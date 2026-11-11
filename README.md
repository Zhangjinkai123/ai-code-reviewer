# AI Code Reviewer

基于大语言模型的 GitHub Pull Request 审查组件。它解析 Git Diff，调用
OpenAI 兼容接口生成问题，输出报告和 PR 评论，并按严重程度执行门禁。

## 接入 GitHub 仓库

在调用仓库的 Actions Secrets 中配置 `CR_API_KEY`，然后新增工作流：

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

示例固定到 `v1.2.0` 的完整提交 SHA。根据实际服务修改 `base-url` 和
`model`。审查 Job 使用只读权限；发布 Job 单独持有评论权限，不执行 PR 代码。
策略从 PR 的 base 提交读取，PR 无法通过修改策略放宽本次门禁。

在目标仓库默认分支配置保护规则，要求 PR 和实际出现的审查检查通过，禁止
直接推送和强推。建议先观察检查是否稳定，再将其设为必需；多维护者场景应
要求可信人员审批，并重点审查工作流变更。同仓库 PR 可能使用仓库 Secret，
因此只应允许可信协作者运行工作流；fork PR 默认无法获取调用方 Secret。

需要自定义编排时也可使用 `action.yml`：调用方需检出目标仓库、设置
`fetch-depth: 0` 并传入 API 参数。Composite Action 不隔离 Job 权限，
生产环境发布评论建议使用可复用工作流。

## 本地使用

需要 Python 3.13：

```powershell
pip install -r requirements.txt
```

在项目根目录的 `.env` 中设置，勿提交真实密钥：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

```powershell
python main.py demo
python main.py review
```

`demo` 审查固定样例；`review` 比较当前工作树与默认远程分支共同祖先，
包括已跟踪文件的暂存和未暂存改动，不包括未跟踪文件。报告输出到控制台和
`reports/review-report.json`；空 Diff 不生成报告。`reports/` 是运行产物。

## 策略与排障

在被审查仓库的 `review.yaml` 中设置阈值，文件缺失时默认 `high`：

```yaml
review:
  severity_threshold: high
```

严重程度依次为 `low`、`medium`、`high`、`critical`；达到或超过阈值时
退出码为 1。门禁失败时工作流仍上传报告并尝试发布评论。模型服务或配置
异常可能没有报告，评论会跳过：检查 Secret、服务地址、模型名和网络后重跑。
评论发布失败时检查调用方权限。每次审查生成独立评论，重跑可能产生重复评论。

升级时核对版本及完整 SHA，先在测试仓库验证，再更新调用方引用。更新内部
审查器时，先合入可信审查器提交，再同时更新工作流中的审查和发布引用。

## 开发与验证

主要代码位于 `main.py`、`git_utils/` 和 `reviewer/`；`examples/` 包含
Diff 回归样例。项目自身的双工作流用于审查和发布评论，需配置
`CR_API_KEY`、`CR_BASE_URL`、`CR_MODEL` 三个 Secrets。

项目使用独立测试脚本，不依赖 pytest：

```powershell
python -m compileall -q main.py config.py git_utils reviewer
Get-ChildItem test_*.py | ForEach-Object { python $_.FullName; if ($LASTEXITCODE -ne 0) { throw "测试失败: $($_.Name)" } }
```

默认测试模拟模型和 GitHub API。真实模型测试可显式运行
`python test_analyzer.py --live valid`、`--live invalid` 或 `--live sql`，
会调用配置的模型服务并产生费用。历史验收记录见
[V1 发布验收记录](V1-发布验收记录-2026-11-09.md)。

当前不提供自动修复、数据库或管理界面。已有 YAML 文件的局部 Diff 不视为
完整配置，缺少上下文时会跳过无法确认的配置问题。
