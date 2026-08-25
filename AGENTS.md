# AGENTS.md

AI 编码代理的项目约定（Trae / Cursor / Codex / Claude Code 等）。本文件是 AI 指令的唯一事实来源；README.md 面向人类，两者不重复维护。

> Rule #0：如需违反本文件中任何规则，必须先向用户说明并获得明确许可。

## 技术栈

- Python 3.13，无框架，纯标准库 + 少量依赖
- 关键依赖：`openai`（LLM 调用）、`pydantic` + `pydantic-settings`（模型与配置）、`pyyaml`（策略）、`python-dotenv`
- 配置从 `.env` 加载（OpenAI 兼容 API，含第三方中转站）

## 常用命令

```bash
pip install -r requirements.txt        # 安装依赖
python main.py demo                    # 用 examples/bad_code.diff 跑审查
python main.py review                  # 审查当前工作区未提交改动（git diff）
```

验证改动（改动任何 .py 后必须执行）：

```bash
python -m py_compile <改动的 .py 文件>
python test_parser.py                  # 快速冒烟：验证 diff 解析器
```

注意：本项目没有 pytest 测试套件；不要臆造不存在的测试命令。

## 架构与改动指南

完整目录结构见 README.md，此处不重复。改代码前你需要知道的：

数据流：`main.py` → `get_git_diff()` → `parse_diff()` → `review_code()`（LLM 返回 issues JSON）→ `locate_line()` 补行号 → `print_report()/save_report()` → `check_policy()` 门禁。

- **换/接新的 LLM 服务**：client 在 reviewer/analyzer.py 顶部创建；如需多 Provider，实现到预留的 reviewer/llm/ 目录
- **调整问题类型或输出字段**：同步改 reviewer/prompt.py 的 JSON Schema 和 reviewer/models.py 的 Issue，reporter/policy 会自动跟随
- **行号定位不准**：逻辑在 reviewer/locator.py，靠 code_snippet 与 diff 行内容做包含匹配，改动时用 examples/bad_code.diff 回归验证
- **改门禁规则**：reviewer/policy.py 读 review.yaml 的 severity_threshold，语义是"达到或超过阈值即失败、退出码 1"

## 代码风格

- 中文注释和文档字符串
- 保持现有风格：简单直白的函数式写法、逻辑块之间空行分隔；不引入类继承等过度抽象
- 类型注解仅在公共函数签名上使用，与现状保持一致
- 所有 LLM 返回值必须经 Pydantic 模型校验后使用，禁止直接信任原始 dict 字段
- 新增依赖前必须先询问用户

## Git 工作流

- 提交信息用中文或英文均可，一行概括"为什么"而非"改了什么"
- 不要自动 commit / push，除非用户明确要求
- commit 前确认暂存区不含 `.env`、`reports/`、`__pycache__/`

## 边界

- ✅ **必须做**：修改 .py 后运行 `py_compile` 验证；遵循上述数据流扩展功能
- ⚠️ **先问再做**：新增依赖；修改 System Prompt（prompt.py）；修改 review.yaml 阈值语义；重构 reviewer/ 下模块结构
- 🚫 **严禁做**：
  - 读取、提交或外泄 `.env` 内容（含真实 API Key，已被 .gitignore 忽略）
  - 把密钥硬编码进任何代码或文档
  - 提交 `reports/review-report.json`、`__pycache__/` 等运行产物
  - 修改 `examples/bad_code.diff`（它是 parser/locator 的回归基准）
