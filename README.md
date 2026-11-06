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

项目使用两个 Workflow：

1. `AI Code Review` 在 PR `opened`、`synchronize`、`reopened` 时运行审查，上传 `ai-review-result` Artifact。
2. `AI Code Review Comment` 监听上游 `workflow_run.completed`，使用上游 Run ID 下载对应 Artifact，再用高权限 `GITHUB_TOKEN` 创建 PR 评论。

评论 Workflow 只检出默认分支上的可信代码，不执行 PR 提交中的代码。报告包含问题时，评论中的文件链接使用本次上游 Run 的 `head_sha`，指向对应提交。

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
│   └── reporter.py          # 控制台与 JSON 报告
├── main.py
├── review.yaml
└── requirements.txt
```

## 本地验证

项目没有 pytest 套件，使用标准库脚本：

```powershell
python -m py_compile git_utils/diff.py reviewer/policy.py
python test_parser.py
python test_locator.py
python test_diff.py
python test_reporter.py
python test_policy.py
python test_commenter.py
python test_formatter.py
python test_github.py
python test_pr_comment.py
```

## 当前范围与限制

- V1.0 不包含数据库、审查历史持久化、Web 管理台或自动修复。
- 报告通过 GitHub Actions Artifact 保留。
- 当前 LLM 调用使用 `chat.completions.create`，暂不迁移 Responses API。
- YAML 合法/非法配置误报专项将在 V1.0 主体验收后单独处理。
