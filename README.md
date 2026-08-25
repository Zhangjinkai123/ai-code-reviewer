# AI Code Reviewer

基于大语言模型的自动化代码审查工具 (AI-powered Code Reviewer)。

解析 Git Diff，调用 LLM 发现代码问题（安全漏洞、缺陷、坏味道等），自动定位行号并输出审查报告；支持通过 `review.yaml` 配置严重程度阈值作为 CI 门禁。

## 目录结构

```text
ai-code-reviewer/
├── app/                    # 预留
├── examples/
│   └── bad_code.diff       # 演示用 diff 样例
├── git_utils/
│   └── diff.py             # 获取 Git Diff
├── reports/                # 审查报告输出目录（已忽略，不提交）
├── reviewer/
│   ├── analyzer.py         # AI 分析核心：解析 -> LLM -> 定位
│   ├── locator.py          # 根据 code_snippet 自动定位行号
│   ├── models.py           # Pydantic 数据结构
│   ├── parser.py           # Git Diff 解析器
│   ├── policy.py           # 审查策略（严重程度阈值门禁）
│   ├── prompt.py           # System Prompt 管理
│   ├── reporter.py         # 报告输出（控制台 + JSON）
│   └── llm/                # LLM Provider 扩展点（预留）
├── main.py                 # 入口
├── config.py               # 配置加载（pydantic-settings）
├── review.yaml             # 审查策略配置
└── requirements.txt
```

## 快速开始

1. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**

   复制 `.env.example` 为 `.env` 并填入真实配置：

   ```env
   OPENAI_API_KEY=your_api_key_here
   OPENAI_BASE_URL=https://api.openai.com/v1
   LLM_MODEL=gpt-4o-mini
   ```

   > 注意：`.env` 已被 `.gitignore` 忽略，不会被提交到仓库。

3. **运行代码审查**

   ```bash
   # 使用内置样例 diff
   python main.py demo

   # 审查当前工作区的未提交改动
   python main.py review
   ```

## 审查策略

在 `review.yaml` 中配置失败阈值：

```yaml
review:
  severity_threshold: high   # low / medium / high / critical
```

当发现达到或超过阈值的问题时，程序以非零退出码结束，可用于 CI 流水线阻断。

## 输出报告

- 控制台输出问题列表
- JSON 报告保存至 `reports/review-report.json`
