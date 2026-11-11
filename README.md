# AI Code Reviewer

基于大语言模型的 GitHub Pull Request 代码审查工具。项目解析 Git Diff，调用 OpenAI 兼容接口生成结构化问题，定位代码行，输出 JSON/Markdown 报告，并按严重程度阈值执行质量门禁。

## 核心流程

```text
Git Diff
  -> Diff Parser
  -> LLM Analyzer
  -> Pydantic ReviewResult
  -> Issue Locator
  -> JSON / Markdown Report
  -> Policy Gate
```

本地运行 `review` 时，程序先获取 `HEAD` 与 `origin/HEAD`（回退到 `origin/master` 或 `origin/main`）的共同祖先，再与当前工作树比较，包含当前分支提交及已跟踪文件的暂存、未暂存改动，不包含未跟踪文件。GitHub Actions 中使用 `GITHUB_BASE_SHA`，比较 PR 基准提交与当前提交。

## 快速开始

### 1. 安装依赖

```powershell
pip install -r requirements.txt
```

### 2. 配置 `.env`

在项目根目录创建 `.env`，填入 OpenAI 兼容服务配置：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

`.env` 已被 Git 忽略，禁止提交真实密钥。

### 3. 运行审查

```powershell
# 使用固定 Diff 样例
python main.py demo

# 审查当前分支相对默认远程分支的改动
python main.py review
```

报告会打印到控制台，并保存到 `reports/review-report.json`。`reports/` 是运行产物目录，不应提交。

## 质量门禁

在 `review.yaml` 中配置失败阈值：

```yaml
review:
  severity_threshold: high
```

严重程度为 `low`、`medium`、`high`、`critical`。达到或超过阈值时程序以退出码 `1` 结束，适合用于 CI 分支保护。未知严重程度会被拒绝，不会默认为低风险。

## GitHub Actions

### Reusable Workflow（推荐用于其他仓库）

工具仓库提供可复用工作流：审查 Job 只读并运行固定版本的审查器，发布 Job
单独持有 PR 评论权限，只消费 Artifact，不检出或执行 PR 代码。策略文件
`review.yaml` 从 PR base commit 读取，因此 PR 本身不能通过修改阈值放宽本次门禁。

调用方在自己的 Workflow 中引用同一版本的 Reusable Workflow：

```yaml
name: AI Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  issues: write
  pull-requests: write

jobs:
  review:
    uses: Zhangjinkai123/ai-code-reviewer/.github/workflows/reusable-review.yml@6cc7512f36507e5d76ad478ea75fdd22dc58593f
    with:
      base-url: https://api.openai.com/v1
      model: gpt-4o-mini
    secrets:
      api-key: ${{ secrets.CR_API_KEY }}
```

示例固定到 `v1.2.0` 对应的完整 commit SHA，避免 Tag 被移动。模型密钥只传给
审查 Workflow。fork PR 默认拿不到调用方 Secret；同仓库 PR 则可能使用仓库
Secret，因此只应允许可信协作者创建可运行该 Workflow 的分支和 PR。
审查 Job 使用 `fetch-depth: 0`，以便三点 Diff 能找到共同祖先。

### 生产仓库设置

在实际调用仓库的 Settings 中配置 `CR_API_KEY`，并将写权限限制给可信维护者。
在 Branches / Rulesets 中保护默认分支：要求 Pull Request、要求
`AI Code Review / review / review (pull_request)` 检查通过、禁止直接推送和强制推送。
如果有多位维护者，要求至少一位可信维护者批准，并重点审查 `.github/workflows/**`
的改动；单人维护时可暂不要求审批，但应在合并前人工检查 Workflow 变更。
首次启用时先观察检查结果，确认稳定后再把它设为必需检查。

工作流依赖和内部审查器均固定到完整 commit SHA。升级时先核对新版本及其
完整 SHA，在测试仓库验证后更新调用方引用。更新内部审查器时，先合入可信
审查器提交，再同时更新工作流中的审查和发布引用，验证后发布新版本。
更新依赖时应核对官方仓库的发布记录和 SHA，并运行 `python test_workflow.py`。

检查失败时先查看 Actions 中 `review` Job：达到门禁阈值会上传报告并尝试
发布评论；模型服务或配置异常可能没有报告，评论也会跳过。确认 Secret、
服务地址、模型名和网络连接后重跑；评论发布失败则检查调用方授予的权限。
空 Diff 不生成报告或评论。

### Composite Action（单 Job / 自定义编排）

`action.yml` 仍可用于需要自行控制 Job、权限和报告处理的场景。调用方负责
checkout 目标仓库、配置 `fetch-depth: 0`，并传入 API 参数；Composite Action
本身不能隔离 Job 权限，因此生产 PR 评论建议使用上面的 Reusable Workflow。

项目使用两个 Workflow：

1. `AI Code Review` 在 PR `opened`、`synchronize`、`reopened` 时运行审查，上传 `ai-review-result` Artifact。
2. `AI Code Review Comment` 监听上游 `workflow_run.completed`，使用上游 Run ID 下载对应 Artifact，再用高权限 `GITHUB_TOKEN` 创建 PR 评论。

评论 Workflow 只检出默认分支上的可信代码，不执行 PR 提交中的代码。报告包含问题时，评论中的文件链接使用本次上游 Run 的 `head_sha`，指向对应提交。
评论头部显示完整提交 SHA 和上游 Actions Run 链接，空问题报告也可核对来源。
评论工作流显式声明 `actions: read`，用于读取上游 Run 的 Artifact。

由于 `workflow_run` 使用默认分支上的工作流和代码，PR 分支中尚未合并的评论逻辑不会在高权限评论 Workflow 中执行；这是安全边界的一部分。

需要在仓库 Secrets 中配置：

```text
CR_API_KEY
CR_BASE_URL
CR_MODEL
```

Workflow 会将它们映射为程序使用的 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`LLM_MODEL`。

每次审查会创建一条独立评论；当前设计不查询、去重或更新历史评论。因此同一 Commit 重跑可能产生重复评论，旧 Run 也可能在乱序完成时留下较晚发布的旧结果。这是当前 V1.0 的已知限制。

## 手工评论入口

`python main.py pr-comment <owner/repository> <pr_number>` 保留用于本地兼容测试，需要设置 `GITHUB_TOKEN`。生产自动评论使用上面的安全双 Workflow。

## 目录结构

```text
ai-code-reviewer/
├── .github/workflows/       # 审查与评论 Workflow
├── examples/                # Diff 回归样例
├── git_utils/diff.py        # Git Diff 获取
├── reviewer/
│   ├── analyzer.py          # LLM 分析与行号定位
│   ├── commenter.py         # 报告读取与 PR 评论
│   ├── formatter.py         # Markdown 评论格式化
│   ├── github.py            # GitHub REST API
│   ├── locator.py           # 代码片段定位
│   ├── models.py            # Pydantic 模型
│   ├── parser.py            # Diff 解析
│   ├── policy.py            # 严重程度门禁
│   ├── reporter.py          # 控制台与 JSON 报告
│   └── yaml_context.py      # YAML 结构路径与完整性元数据
├── main.py
├── review.yaml
└── requirements.txt
```

## 本地验证

项目没有 pytest 套件，使用标准库脚本：

```powershell
python -m compileall -q main.py config.py git_utils reviewer
python test_parser.py
python test_yaml_regression.py
python test_analyzer.py
python test_locator.py
python test_diff.py
python test_reporter.py
python test_policy.py
python test_commenter.py
python test_formatter.py
python test_github.py
python test_pr_comment.py
python test_workflow.py
```

`test_workflow.py` 读取实际双 Workflow，并执行其中的评论脚本，覆盖门禁失败后
报告与评论生成、无问题放行、乱序完成和同一提交重跑。模型服务与 HTTP 发布
均使用模拟响应，该测试不构成 GitHub 线上验收。

`test_analyzer.py` 默认使用模拟模型响应，不读取模型配置或发起请求，覆盖响应校验、
行号定位、报告往返、门禁失败后独立生成评论。需要真实模型验收时，显式运行：

```powershell
python test_analyzer.py --live valid
python test_analyzer.py --live invalid
python test_analyzer.py --live sql
```

这些命令使用项目现有模型配置，分别检查合法 YAML 不误报、错误层级能识别、
SQL 注入能定位；报告保存在被忽略的 `reports/live-*.json`，不会发布 GitHub 评论。

## 当前范围与限制

- V1.0 不包含数据库、审查历史持久化、Web 管理台或自动修复。
- 报告通过 GitHub Actions Artifact 保留。
- 当前 LLM 调用使用 `chat.completions.create`，暂不迁移 Responses API。
- V1 已于 2026-11-09 完成：PR #9 合并到 `master`，12 个本地测试脚本通过，
  真实模型及 GitHub Actions 验收通过。
- 独立 PR #10 已验证高危拦截后仍有报告和评论、参数化修复后放行、
  旧提交晚到时独立评论及 SHA/Run/行号绑定；验收 PR 已关闭且未合并。
  详细 Run、Artifact 和评论索引见 [V1 发布验收记录](V1-发布验收记录-2026-11-09.md)。
- YAML 仅在 Diff 明确包含完整新文件时提供完整路径；已有文件的局部 Diff
  保守标记为不完整。配置上下文不足时只跳过无法确认的配置问题。
