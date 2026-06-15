# GitHub Actions Node.js 24 升级

## 问题描述 / 需求背景

GitHub Actions 发出弃用警告：

> Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/checkout@v4, actions/setup-python@v3. Actions will be forced to run with Node.js 24 by default starting June 16th, 2026. Node.js 20 will be removed from the runner on September 16th, 2026.

需要升级工作流中使用的 Action 版本，以支持 Node.js 24，避免未来工作流运行失败。

## 原因分析

- `actions/checkout@v4` 基于 Node.js 20 构建
- `actions/setup-python@v3` 基于 Node.js 20 构建
- GitHub 官方已发布基于 Node.js 24 的新版本：
  - `actions/checkout@v5` — 基于 Node.js 24
  - `actions/setup-python@v6` — 基于 Node.js 24

## 解决方案

修改 `.github/workflows/release.yml`，升级两个 Action 的版本：

```diff
     - name: Checkout source code
-      uses: actions/checkout@v4
+      uses: actions/checkout@v5
       with:
         fetch-depth: 0

     - name: Set up Python
-      uses: actions/setup-python@v3
+      uses: actions/setup-python@v6
       with:
         python-version: '3.10'
```

## 涉及的文件

| 文件 | 说明 |
|------|------|
| `.github/workflows/release.yml` | 升级 `actions/checkout` 和 `actions/setup-python` 的版本 |

## 验证结果

- 修改后 YAML 语法正确
- 新版本 `v5` 和 `v6` 均官方支持 Node.js 24，可消除弃用警告
