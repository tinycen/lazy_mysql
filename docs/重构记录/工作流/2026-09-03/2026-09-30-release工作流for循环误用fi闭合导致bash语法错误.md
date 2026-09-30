# Release 工作流 for 循环误用 fi 闭合导致 bash 语法错误

- 日期：2026-09-30
- 类型：CI 脚本语法 Bug
- 涉及提交：`46a9506`（修复条件判断逻辑）

## 问题描述 / 需求背景

手动运行 Release 工作流（已填版本号、勾选 publish），`1. Prepare release notes` 步骤失败。日志显示前面的赋值与提示都正常输出，随后报语法错误：

```text
Current tag is: v0.7.4
Warning: 本次手动运行将正式发布（上传 PyPI 并创建 GitHub Release）。
/home/runner/work/_temp/xxxx.sh: line 39: syntax error near unexpected token `fi'
Error: Process completed with exit code 2.
```

## 原因分析

### 直接根因

查找发布说明文件的 `for` 循环被错误地用 `fi` 而不是 `done` 闭合：

```bash
# 错误写法（runner 实际执行的内容）
for candidate in "$NOTES_DIR/$CURRENT_TAG.md" "$NOTES_DIR/$VERSION.md"; do
  if [ -f "$candidate" ]; then
    NOTES_FILE="$candidate"
    break
  fi
fi        # ← 错误：for 复合命令必须以 done 闭合
```

bash 解析到 `for ...; do` 后期望 `done`，读到 `fi` 即报 `syntax error near unexpected token 'fi'`。这也解释了为什么报错前的 `echo`、变量赋值、warning 都已打印——bash 是边读取解析边执行复合命令体的。

### 排查过程中的三个关键干扰（重要）

本次根因虽简单，但定位耗时，主要因为「看到的内容」与「runner 执行的内容」一度不一致：

1. **IDE/编辑器缓冲区 ≠ 磁盘文件**
   通过编辑器与 Read 工具看到的第 110 行一直是正确的 `done`，但那是**未保存的编辑器缓冲**。用 PowerShell 直接读磁盘（`Get-Content(...)[109]`）和 `git show HEAD:<file>` 看到的都是 `fi`。

2. **raw.githubusercontent 网页抓取结果不可作为字节级依据**
   WebFetch 抓取远程 raw 文件时该处显示为 `done`（且另一行 `<br/>` 还被错误折行），与实际仓库内容不符，属于内容转换/缓存假象。最终以 **git 协议数据**为准：`git fetch origin` 后 `git show origin/main:.github/workflows/release.yml` 证实远程第 110 行确为 `fi`。

3. **先排除了 CRLF 假设**
   本机文件为 CRLF（`core.autocrlf=true`），曾怀疑 runner 上 `fi\r` 导致 token 异常。但 `git show` 导出的仓库版本为 LF，且对问题行做十六进制检查未见 NBSP 等特殊字符，从而排除换行符/不可见字符方向，回到结构性语法错误本身。

## 解决方案

将循环闭合词由 `fi` 改为 `done`：

```bash
        for candidate in "$NOTES_DIR/$CURRENT_TAG.md" "$NOTES_DIR/$VERSION.md"; do
          if [ -f "$candidate" ]; then
            NOTES_FILE="$candidate"
            break
          fi
        done
```

改动只有一行，`git diff` 确认无其他变更：

```diff
             NOTES_FILE="$candidate"
             break
           fi
-        fi
+        done
```

## 验证结果

采用「提取脚本块 + 本地 `bash -n` 静态校验」的方式，无需推送即可验证：

1. 从 YAML 中提取整个 `run: |` 脚本块写入临时 `.sh`；
2. 用 Git 自带的 `C:\Program Files\Git\bin\bash.exe`（注意系统 `bash.exe` 指向的是未装发行版的 WSL，不可用）执行 `bash -n`；
3. 分别对 **CRLF 版本与 LF 版本**校验，退出码均为 `0`。

修复提交推送后，该步骤不再报语法错误。

## 经验教训

1. **shell 复合命令闭合词必须配对**：`if...fi`、`for/while...done`、`case...esac`、函数花括号 `{ ... }` 各成体系，嵌套时建议按缩进逐级核对。
2. **排查「肉眼正确却报错」时，以磁盘字节和 git 数据为准，不要信未保存的编辑器内容**；可用 `git show HEAD:path`、`git show origin/main:path`、十六进制导出交叉确认。
3. **CI shell 脚本改动后，推送前用 `bash -n` 做一次本地静态语法检查**，成本极低，能拦住绝大多数闭合/引号类错误。
4. Windows 环境下做 bash 校验，优先使用 Git for Windows 自带 bash，避免误用 WSL 占位 `bash.exe`。

## 相关文件

| 文件 | 说明 |
|------|------|
| [`.github/workflows/release.yml`](../../.github/workflows/release.yml#L105-L110) | 第 110 行 `fi` → `done`，修复 for 循环闭合 |

## 关联问题

- [Release 工作流支持手动干跑预览与发布开关](../features/2026-09-30-Release工作流支持手动干跑预览与发布开关.md)
- [GitHub Models 退役并重构为本地发布说明方案](2026-09-30-GitHubModels退役导致Release工作流失败并重构为本地发布说明方案.md)
- [action-gh-release 升级 v3 消除 Node 20 弃用警告](../config/2026-09-30-action-gh-release升级v3消除Node20弃用警告.md)
