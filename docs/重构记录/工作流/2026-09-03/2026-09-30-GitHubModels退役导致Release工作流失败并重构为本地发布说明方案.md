# GitHub Models 退役导致 Release 工作流失败，并重构为「本地发布说明 + git 记录兜底」方案

- 日期：2026-09-30
- 类型：CI 故障修复 / 发布流程重构
- 涉及提交：`9aa0d81`（重构发布流程，移除 AI 依赖）

## 问题描述 / 需求背景

推送 `v0.7.4` 标签后，Release 工作流在「调用 AI 生成 Release Notes」步骤失败，关键日志：

```text
Sending prompt to AI model...
--- Raw AI Response Start ---
OK
--- Raw AI Response End ---
jq: parse error: Invalid numeric literal at line 1, column 3
Error: Process completed with exit code 5.
```

原工作流通过 `curl` 直接请求 GitHub Models 推理端点，再用 `jq` 解析响应：

```bash
AI_RESPONSE=$(curl -s "https://models.github.ai/inference/chat/completions" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $GITHUB_TOKEN" \
     -d "$JSON_PAYLOAD")

RELEASE_BODY=$(echo "$AI_RESPONSE" | jq -r '.choices[0].message.content')
```

表面现象是「模型响应异常 + jq 解析失败」，且使用的模型 ID 为 `openai/gpt-4.1-mini`，一度怀疑是模型名变更或接口鉴权问题。

## 原因分析

**根因是 GitHub Models 服务整体退役，与 prompt、token、模型 ID 均无关。**

- 查阅 GitHub 官方文档确认：**GitHub Models 已于 2026-07-30 完全退役**，playground、模型目录、推理 API（`models.github.ai`）、BYOK 全部关闭。
- 服务下线后，该端点不再返回 OpenAI 格式的 JSON，而是返回纯文本的健康检查响应 `OK`。
- `jq` 拿到 `OK` 后按 JSON 解析，在第 1 行第 3 列（字符 `K`）报 `Invalid numeric literal`，退出码 5。

官方给出的迁移方向只有两类：Azure AI Foundry（REST API）或 GitHub Copilot（Copilot CLI）。

## 方案演进过程

重构并非一次到位，经历了两个阶段，第二阶段为最终落地方案：

### 阶段一（已废弃）：迁移到 `actions/ai-inference`（Copilot CLI）

最初按用户提供的参考仓库 `https://github.com/actions/ai-inference` 改造：

- 新增 `actions/setup-node@v6` + `npm install -g @github/copilot`
- 用 `actions/ai-inference@v1` 替换手工 `curl`/`jq`，模型改为裸 ID `gpt-4.1`
- 认证需要 `COPILOT_GITHUB_TOKEN`（fine-grained PAT，勾选 Copilot Requests → Read）

该方案技术可行，但存在明显成本：需要 Copilot 订阅、额外维护 PAT、引入 Node 工具链，与一个简单的发布说明需求不匹配。

### 阶段二（最终方案）：本地手写文件优先 + git 提交记录兜底

用户提出更轻量的思路：在仓库内维护 `docs/release_notes/<版本>.md`，工作流只负责读取；读不到时自动用 git 提交记录生成。该方案零外部依赖、零密钥、可离线审阅，最终取代了阶段一。

## 解决方案

### 1. 新增发布说明目录

- 新建目录 `docs/release_notes/`
- 编写 `docs/release_notes/README.md` 说明命名规则、两种触发方式、兜底机制与模板
- 过渡期曾用空文件 `.gitkeep` 占位（Git 不跟踪空目录），README 建立后已删除

文件命名支持两种形式，按优先级查找：`v0.7.5.md`（推荐，与 tag 一致）、`0.7.5.md`。

### 2. 重写工作流的 Release Notes 准备步骤

用单个 `Prepare release notes` 步骤替代原有的「取 commit log → curl 调模型 → jq 解析」三步，同时删除了 Node/Copilot/jq 全部依赖与失效的 `models: read` 权限。

核心逻辑（[release.yml 第 103-167 行](../../../../.github/workflows/release.yml#L103-L167)）：

```bash
# 1. 查找手写文件
NOTES_FILE=""
for candidate in "$NOTES_DIR/$CURRENT_TAG.md" "$NOTES_DIR/$VERSION.md"; do
  if [ -f "$candidate" ]; then
    NOTES_FILE="$candidate"
    break
  fi
done

# 2. 找不到则用「上一个 tag → 当前版本」的提交记录生成友好 Markdown
PREVIOUS_TAG=$(git tag --sort=-v:refname | head -n 2 | tail -n 1)
# ...
git log "$COMMIT_RANGE" --date=short \
  --pretty=format:"- \`%h\` %s  <br/>_&nbsp;&nbsp;&nbsp;&nbsp;%an · %ad_"
```

兜底输出包含版本标题、提示语、提交总数，以及每条提交的短哈希 / 说明 / 作者 / 日期；首个 tag 取全部历史；两 tag 间无提交时给出明确文案。最终内容通过 `$GITHUB_OUTPUT` 的 heredoc 传递给后续 Release 步骤。

### 3. 清理失效配置

- 删除 `permissions.models: read`（该权限随服务一并失效）
- 删除残留的 `test_changelog.prompt.yml`（旧 AI 方案的 prompt 文件，已无引用）

## 验证结果

- 工作流不再请求任何外部 AI 端点，消除了对已退役服务的依赖。
- 手写文件存在时原样使用；不存在时工作流正常走兜底分支，不阻断发布。
- 后续手动干跑验证（见关联文档）确认两种路径均能产出预期 Markdown。

## 经验教训

1. **「接口返回体变了」类报错先确认服务是否还活着**：本次在模型名、鉴权上排查方向都不对，官方服务退役公告才是根因；社区同类问题本质相同。
2. **能用仓库内文件解决的，不引入外部服务**：发布说明是低频、强审阅需求，本地 Markdown + git 历史比 AI API 更稳定、可追溯，也省去密钥与订阅维护。
3. **兜底设计保证发布不中断**：即使忘记写说明文件，发布流程也应成功，只是内容降级为提交记录。

## 相关文件

| 文件 | 说明 |
|------|------|
| [`.github/workflows/release.yml`](../../../../.github/workflows/release.yml) | 删除 AI 调用，新增本地文件读取与 git log 兜底逻辑 |
| [`docs/release_notes/README.md`](../../../release_notes/README.md) | 发布说明目录的使用说明与模板 |
| `docs/release_notes/v<版本>.md` | 各版本手写发布说明（按版本号新建） |

## 关联问题

- [Release 工作流支持手动干跑预览与发布开关](2026-09-30-Release工作流支持手动干跑预览与发布开关.md)
- [for 循环误用 fi 闭合导致 bash 语法错误](2026-09-30-release工作流for循环误用fi闭合导致bash语法错误.md)
- [action-gh-release 升级 v3 消除 Node 20 弃用警告](2026-09-30-action-gh-release升级v3消除Node20弃用警告.md)
