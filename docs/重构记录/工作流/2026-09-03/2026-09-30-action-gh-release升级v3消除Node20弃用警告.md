# 升级 action-gh-release v1 → v3，消除 Node.js 20 弃用警告

- 日期：2026-09-30
- 类型：CI 依赖升级 / 环境调整
- 涉及提交：`861aedc`（更新 GitHub Release 动作版本到 v3）

## 问题描述 / 需求背景

工作流运行成功，但日志中出现弃用警告：

```text
Node.js 20 is deprecated. The following actions target Node.js 20 but are being
forced to run on Node.js 24: softprops/action-gh-release@v1.
For more information see:
https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
```

当前不影响执行结果（GitHub 临时强制以 Node 24 兼容运行），但未来 Node 20 运行时被彻底移除后，该 action 将无法运行。

## 原因分析

- `softprops/action-gh-release@v1` 的 action 元数据声明的运行时为 `node20`。
- GitHub 自 2025-09-19 起在托管 runner 上弃用 Node.js 20，因此对该类 action 打印警告并强制切换运行时。
- 上游已发布基于 Node 24 的大版本：最新 v3.0.3，其 `action.yml` 中 `runs.using: "node24"`。

## 解决方案

[release.yml 第 197 行](../../.github/workflows/release.yml#L197) 升级主版本：

```diff
-      uses: softprops/action-gh-release@v1
+      uses: softprops/action-gh-release@v3
```

升级前核对了 v3 的兼容性：

- 本工作流使用的输入参数 `tag_name`、`body`、`files` 在 v3 中均保留，语义一致，无需改动 `with` 配置。
- 全仓库排查（`.github/` 下仅此一个工作流），其余两个 action 已是新版本：
  - `actions/checkout@v5`、`actions/setup-python@v6` 均基于 Node 24，不在警告列表中。
- 未采用设置 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` 环境变量的绕过方式——那只是官方过渡手段，升级 action 版本才是根治。

## 验证结果

- `git diff` 确认仅版本号一行变更，无参数调整。
- 升级后工作流运行不再出现 Node.js 20 弃用警告；Release 创建、附件上传、`tag_name` 关联行为正常。

## 经验教训

1. GitHub Actions 的弃用警告应在下一次维护窗口及时处理，避免运行时移除后集中爆发。
2. 跨大版本升级第三方 action 时，以其仓库对应 tag 的 `action.yml` 为准核对 `runs.using` 与所用输入参数是否兼容，不要仅凭版本号猜测。
3. 优先升级 action 本身，而非依赖 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` 这类临时兼容开关。

## 相关文件

| 文件 | 说明 |
|------|------|
| [`.github/workflows/release.yml`](../../.github/workflows/release.yml#L195-L204) | `softprops/action-gh-release` 由 v1 升级至 v3 |

## 关联问题

- [Release 工作流支持手动干跑预览与发布开关](../features/2026-09-30-Release工作流支持手动干跑预览与发布开关.md)
- [GitHub Models 退役并重构为本地发布说明方案](../fixed_bugs/2026-09-30-GitHubModels退役导致Release工作流失败并重构为本地发布说明方案.md)
- [for 循环误用 fi 闭合导致 bash 语法错误](../fixed_bugs/2026-09-30-release工作流for循环误用fi闭合导致bash语法错误.md)
