# AI Code Review Assistant --- 项目交接文档（V1.0 最新版）

-   文档版本：2026-11-05
-   项目名称：AI Code Review Assistant
-   项目路径：`D:\self\work\aiproject\ai-code-reviewer`
-   当前已知开发分支：`test001`
-   用途：交接给后续 ChatGPT、Codex、ZCode
    或其他开发助手，要求在现有项目基础上继续，不得重新搭建或擅自改变已确认的设计。

------------------------------------------------------------------------

## 1. 项目目标

构建一个面向 GitHub Pull Request 的 AI 代码审查助手：

1.  获取 PR 代码变更（Git Diff）。
2.  解析 Diff 并提供文件、代码行等上下文。
3.  调用配置的大语言模型分析代码问题。
4.  将结果解析为结构化 `ReviewResult`。
5.  定位问题代码并生成 JSON/Markdown 审查报告。
6.  根据 Policy 和严重程度阈值决定审查是否通过。
7.  通过 GitHub Actions 自动执行审查，并将结果发布到 PR 评论。

V1.0 重点是可靠完成代码审查、质量门禁和 PR
反馈，不是数据库化的审查历史管理平台。

## 2. 必须遵守的项目协作约定

-   用户偏好中文、详细但聚焦、按步骤推进。
-   一次只安排一个明确步骤；用户反馈结果后再给下一步。
-   不要主动复述冗长进度，不要擅自扩展任务。
-   修改代码前先检查当前真实文件和 Git 状态，不要依据旧版本代码猜测。
-   用户未要求时，不要直接批量修改多个文件。
-   不要重复已经验证通过的步骤。
-   用户明确要求暂停时，停止推进。
-   对项目进度、代码结构或阶段名称有疑问时，先核对，不要编造阶段或功能。

## 3. 当前架构与核心流程

### 3.1 本地审查流程

``` text
Git Diff
   ↓
Diff Parser
   ↓
DiffContext / DiffLine
   ↓
LLM Analyzer
   ↓
ReviewResult
   ↓
Issue Locator
   ↓
Policy Check
   ↓
Console / JSON Report
```

### 3.2 GitHub 双 Workflow 架构

``` text
Pull Request: opened / synchronize / reopened
                  |
                  v
       AI Code Review (ai-review.yml)
                  |
          运行 python main.py review
                  |
          生成 review-report.json
                  |
          上传 Artifact: ai-review-result
                  |
             workflow_run
                  |
                  v
 AI Code Review Comment (ai-review-comment.yml)
                  |
       Checkout 默认分支可信代码
                  |
          下载上游 Artifact
                  |
          读取 review-report.json
                  |
          GitHub API 创建/更新 PR 评论
```

安全原则： - 上游 PR 工作流负责执行审查和生成报告。 - 下游
`workflow_run` 评论工作流使用高权限 Token。 - 下游只 Checkout
默认分支可信代码，不 Checkout 或执行 PR 提交中的不可信代码。 -
下游从上游 Workflow Run 下载 Artifact。 - 评论工作流有
`contents: read`、`issues: write`、`pull-requests: write` 权限配置。 -
评论工作流独立于上游审查结果执行；上游审查失败时，下游仍可读取报告并发布评论。

## 4. 已完成内容

以下状态依据此前用户确认、代码检查记录及 2026-11-05 GitHub Actions
实际运行结果整理。完成"功能实现"不代表所有边界场景均已验收。

### Phase 1--3：核心审查引擎 --- 已完成

-   Git Diff 获取与解析。
-   DiffLine / DiffContext 等变更上下文处理。
-   LLM 接口集成。
-   结构化 JSON 输出。
-   Pydantic 数据模型。
-   Issue 文件和代码行定位。
-   多行代码片段匹配。
-   审查报告模型与处理流程。

已知 `Issue` 数据模型字段（以用户纠正后的版本为准）：

``` python
class Issue(BaseModel):
    file: str = "unknown"
    line: str | None = None
    code_snippet: str | None = None
    severity: str
    category: str
    message: str
    suggestion: str
```

注意：`line` 是 `str | None`，不是整数；问题描述字段是
`message`，不是旧版本中的 `description`；不要重新引入 `confidence`
等已移除字段。

已解决过的工程问题： - Windows GBK 解码问题。 - 非 master 分支获取 Diff
为空的问题。 - Git Diff 代码行号定位问题。 - LLM 返回的多行代码片段与
Diff 分行内容不一致的问题。 - Pydantic 字段定义与调用代码不匹配的问题。

### Phase 4：CLI、报告和 Policy --- 已完成

支持命令：

``` powershell
python main.py demo
python main.py review
```

已实现： - CLI 入口。 - Demo Diff 审查。 - 当前 Git 变更审查。 - Console
报告。 - JSON 报告保存。 - Policy 配置加载。 - `severity_threshold`
严重程度阈值判断。 - 达到阻断条件时返回失败状态。

当前用户已明确：**继续沿用原有质量门禁逻辑**。AI Review
达到配置阈值的问题时应失败，GitHub Check
保持失败并按现有分支保护/检查规则影响 PR
合并。不要擅自改成纯报告模式，也不要改变阈值语义。

### Phase 5.1：GitHub Actions CI --- 已完成

-   PR `opened`、`synchronize`、`reopened` 触发。
-   Checkout、Python 环境和依赖安装。
-   执行 `python main.py review`。
-   上传 `reports/review-report.json` Artifact。
-   Workflow 文件：`.github/workflows/ai-review.yml`。

### Phase 5.2：PR 自动评论 --- 已完成

-   读取结构化审查结果。
-   格式化 GitHub Markdown 评论。
-   GitHub API 创建 PR 评论。
-   后续安全架构将评论发布移至独立下游 Workflow。

### Phase 5.3：安全评论工作流、评论去重/更新 --- 已完成并通过关键真实场景验证

主要文件： - `.github/workflows/ai-review.yml` -
`.github/workflows/ai-review-comment.yml` - `reviewer/commenter.py` -
`reviewer/github.py` - `reviewer/formatter.py`

已实现/验证： - 上游审查工作流上传 `ai-review-result` Artifact。 -
下游使用 `workflow_run` 的 `completed` 事件触发。 -
下游只检出默认分支可信代码。 - 下游通过 `actions/download-artifact@v4`
和上游 `run-id` 下载 Artifact。 - 获取 PR Number、Commit SHA。 - 使用
`GITHUB_TOKEN` 调用 GitHub API。 - 评论使用 AI Review marker
识别，并支持已有评论更新/去重相关逻辑。 - 已有每个 Commit
独立评论的开发与验证记录；本轮还需要补齐边界回归验证，见待办。

## 5. 2026-11-05 最新真实验证记录

用户在 PR #9（`test001` → `master`）上进行了新的端到端测试。

### 5.1 测试改动

在 `examples/test.java` 中添加了一行无业务影响的注释：

``` java
// Test GitHub Actions permission workflow
```

随后执行 Commit + Push，触发 GitHub Actions。

### 5.2 Workflow 结果

-   上游 `AI Code Review`：Run #24，结果 `Failed`。
-   下游 `AI Code Review Comment`：Run #16，结果 `Success`，耗时约 22
    秒。
-   下游所有步骤均显示成功，包括：
    -   Show workflow result
    -   Check Pull Request
    -   Checkout trusted repository code
    -   Setup Python
    -   Install dependencies
    -   Download Review Result
    -   Show Review Result
    -   Create PR Comment

### 5.3 GitHub API 评论创建结果

下游日志明确输出：

``` text
PR comment created: https://github.com/Zhangjinkai123/ai-code-reviewer/pull/9#issuecomment-6652055650
```

用户随后打开 PR 页面截图，确认 AI Review Bot 评论已成功显示。

因此以下链路已得到真实验证：

``` text
Push
 → AI Code Review 触发
 → 生成并上传 Artifact
 → workflow_run 触发下游
 → 获取 PR 信息
 → 下载并读取 Artifact
 → 使用 GitHub Token
 → GitHub API 创建评论
 → PR 页面展示评论
```

**重要结论：** - 评论工作流独立执行，上游 AI Review
失败没有阻止下游评论。 - GitHub Token 权限、Artifact
下载、报告读取和评论创建在本次运行中均成功。 - 这不代表上游 AI Review
通过；上游本次仍为 Failed。 - 也不代表所有多
Commit、并发或重试边界均已验收。

### 5.4 2026-11-06 修复后的验收状态

-   提交 `773180e` 修正本地审查使用共同祖先计算 Diff 的范围，并增加真实临时 Git 仓库分叉测试。
-   本地标准库测试脚本全部通过：Parser、Locator、Diff、Reporter、Policy、Commenter、Formatter、GitHub API、PR Comment。
-   GitHub Actions 上游 Run `42205849784` 对应 `773180e`，状态成功并生成 `ai-review-result` Artifact；下游 Run `42205902620` 状态成功。
-   上游 Artifact 与下游下载通过 `workflow_run.id` 关联；评论文件链接使用对应上游 Run 的 `head_sha`。评论采用每次 Run 创建独立评论的设计，因此旧 Run 不会更新或覆盖新 Run 的评论。
-   需要注意：`workflow_run` 工作流按 GitHub 安全模型使用默认分支可信代码。本次下游 Run 页面显示执行提交为默认分支 `16fb42e`，因此 `test001` 中尚未合并的评论实现不会被该次下游 Run 执行；这不表示 PR 分支代码可直接被高权限工作流执行。
-   公开 PR 页面可以确认 AI Review 评论存在，但页面没有展示其对应的 Workflow Run ID 或完整 Commit SHA；同时无法读取 Artifact 内的报告内容。因此报告内容与该次评论的精确绑定，以及多次 Push 并发/乱序的真实线上表现仍未完成端到端核实。
-   同一 Commit 重跑会创建重复评论；这是当前设计的已知限制，不应误记为已实现去重/更新。
-   为避免短时间内重复触发 GitHub Actions 和加重限流，本次未额外 Push 测试提交。

## 6. 当前已知问题：GitHub Actions YAML 误报

这是用户明确要求在 V1.0 初始版本主体完成后专项排查解决的问题。

文件： `.github/workflows/ai-review-comment.yml`

本次 AI Review 对 `COMMIT_SHA` 提出"缩进与其他 env
变量不一致、无法确认其属于 env"的 High 级别问题。

用户提供的完整 YAML 文件及 PR Diff 后，人工核对确认：

``` yaml
      - name: Create PR Comment
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.workflow_run.pull_requests[0].number }}
          COMMIT_SHA: ${{ github.event.workflow_run.head_sha }}
        run: |
```

四个变量缩进一致，均属于该步骤的 `env` 节点。下游 Python 也成功读取了
`COMMIT_SHA`，并成功创建 PR 评论。因此该条 AI 诊断属于误报。

用户的明确安排： - **先完成 V1.0 初始版本主体工作。** -
**初始版本完成后，再专项排查和解决配置文件误报。** -
不要现在为了该问题擅自改变整体架构或质量门禁。 - 专项排查应覆盖 YAML
节点层级、`env` / `with` / `jobs` 等上下文、完整文件上下文与局部 Diff
的关系、Prompt 和审查规则。 - 修复后必须用合法 YAML 与非法 YAML
对照样例验证：合法配置不误报，非法配置能识别。

### 6.1 2026-11-06 YAML 误报专项处理结果

- 新增 `reviewer/yaml_context.py`，对完整 YAML Diff 使用 PyYAML 解析并生成
  key path；局部 Diff 会标记为不完整，不把缺失上下文当成确定性错误。
- LLM 输入新增每行 `indent` 和 `yaml_context`，Prompt 明确区分 YAML 语法错误
  与 GitHub Actions schema 错误，要求核对 `env`、`with`、`jobs`、`steps` 的
  父级路径和同级关系。
- `yaml_regression_valid.diff` 与 `yaml_regression_invalid.diff` 均可通过 YAML
  语法解析；回归脚本确认合法样例的 `COMMIT_SHA` 位于
  `jobs.comment.steps[0].env`，非法样例位于 step 层级。
- 本地已通过 `test_yaml_regression.py` 及全部现有标准库测试。由于当前 GitHub
  限流风险，尚未额外 Push 触发真实 LLM/Workflow；线上误报修复仍需后续受控验证。

### 6.2 2026-11-09 收尾与真实模型验收

- 修复 `reviewer/analyzer.py` 缺少 `json` 导入导致实际审查失败的问题。
- Parser 正确移除上下文行的 Diff 标记，保留代码原始缩进；忽略无换行标记和
  文件元数据。仅将 `/dev/null` 新文件、单个完整 hunk、行号连续且行数匹配的
  Diff 标记为完整，避免把已有文件开头的局部新增误认为完整文件。
- YAML 使用现有 PyYAML 的 SafeLoader 构建节点，并保护递归别名遍历；
  截断、局部及不连续 Diff 不提供确定性的完整结构路径。
- 提示词限定：缺少 YAML 层级上下文只跳过该配置问题，不抑制其他明确缺陷。
- 新增 `test_analyzer.py`，不调用服务的默认模式覆盖实际解析路径、Pydantic
  校验、行号定位、报告往返、质量门禁与独立评论生成（HTTP 发布使用模拟）。
- 使用项目现有配置完成真实模型验证：合法 YAML 返回空 issues；非法 YAML
  识别 step 层级错误的 `COMMIT_SHA`，定位第 19 行；Java SQL 注入识别为 high，
  定位第 23–25 行。结果存放于被忽略的 `reports/live-*.json`。
- 以上是固定样例验收，不代表所有模型输出或配置误报均得到保证。
- 通过全部 11 个本地测试脚本、修改文件编译检查；原始 `bad_code.diff` 未修改。
- GitHub 只读 API 复核：上游 Run `42205849784`，SHA
  `773180e38e4e843823de839d442f302e14be141e`，PR #9，结论 success，
  有未过期的 `ai-review-result` Artifact（170 字节）；评论 Run `42205902620`
  成功，其可信代码 SHA 为 `16fb42e6cd8a04635ea64ccb98b5288e44b5545b`。
  本轮没有下载 Artifact 内容，也没有取得对应新评论的完整绑定证据。
- 本轮没有 commit、push、合并或新增线上触发。已有 Run 不能证明当前工作区修改
  已在线生效；最终发布仍需合并可信代码并安排一次受控验收。

### 6.3 2026-11-09 发布验收准备

- 用户要求完整完成第一版，仅查看结果；继续推进集中发布和线上验收。
- 已确认 GitHub SSH 与 API 认证可用，PR #9 仍打开且基准为 `master`。
- 评论头部新增完整提交 SHA 与来源 Actions Run 链接；空报告也保留来源信息。
- 评论工作流显式声明 `actions: read`，上游事件元数据通过环境变量传入日志脚本。
- 修改后的编译检查、11 个本地测试脚本已通过，下一步集中提交推送，
  PR #9 验证后合并，再以独立验收 PR 检查高危门禁、Artifact 和评论来源绑定。
- 这里记录的是发布准备，不构成线上验收通过的声明；结果以随后验收记录为准。

### 6.4 2026-11-09 首轮发布审查与资源上限修复

- 已集中推送 `ca641f09728010e5d6bdddc91a7568711254dc96`。
- PR #9 上游 Run `42580195994` 成功，已实际下载并校验 Artifact 报告。
  报告指出 YAML 非循环别名可导致指数展开，严重程度 medium，未触发 high 门禁。
- 已确认该问题有效：为节点与键路径遍历增加共享的 4096 次访问预算，
  超限返回 `unavailable`、`complete: false`、`reason: structure_limit`，
  不输出部分结构路径，不影响后续其他文件的审查。
- 新增 24 层非循环双分支别名的回归样例，确认处理有界；
  编译、Parser、YAML、Analyzer 链路测试通过。
- 下游 Run `42580280025` 成功，但仍来自默认分支旧代码；新版评论链路仍需合并后验证。

### 6.5 2026-11-09 多文档 YAML 边界修复

- 资源上限修复提交 `7ff0d4b` 的审查 Run `42580525567` 成功；已下载实际报告。
- 报告指出单文档 `yaml.compose` 会误判合法多文档 YAML，确认属于有效问题。
- 改用 `yaml.compose_all` 并在异常处理范围内消费生成器；多文档路径带
  `document` 编号，沿用原始文件行号，所有文档共享同一遍历预算。
- 增加合法双文档与第二文档语法错误的回归，避免将合法 Kubernetes 清单误报。

## 7. V1.0 范围与明确不做事项

### V1.0 继续保留

-   现有 Git Diff → LLM → ReviewResult 流程。
-   现有 CLI 和 JSON Artifact。
-   现有 Policy / `severity_threshold` 质量门禁。
-   现有安全双 Workflow。
-   现有 PR 评论创建/更新机制。
-   使用 GitHub Actions Artifact 保存报告。

### 明确不纳入当前 V1.0

-   不增加数据库。
-   不做独立历史记录持久化。
-   不把审查历史保存到 Git 分支作为数据库替代。
-   不增加独立第三个 Quality Gate Workflow。
-   不把质量门禁改成纯报告模式。
-   多模型架构及协同审查属于后续阶段，不在当前 V1.0 主线中。
-   自动修复、Web 管理台、完整产品化部署等不提前纳入。

**特别纠正：不要新增"Phase 5.4 历史记录持久化"任务。用户已明确表示 V1.0
不做历史记录持久化。** GitHub Actions Artifact 保留报告即可。

## 8. V1.0 待完成事项

以下为当前盘点后的待办，不代表已开始实施。推进前应先对照仓库实际代码、测试和用户原始路线确认。

### 高优先级

1.  **Commit SHA 与审查报告关联边界**：代码配置已确认 Artifact 按上游 Run ID 下载，评论链接使用该 Run 的 `head_sha`；修复提交对应的上游 Run 已成功并生成 Artifact。仍需能查看 Artifact 内容或该次评论，才能确认报告与评论内容中的 SHA。
2.  **PR 多 Commit / 并发边界**：代码结构确认每个 Run 使用自己的 Artifact 并新建独立评论，不存在覆盖另一条评论的更新操作。真实并发、乱序完成和重跑尚未线上演练；同一 Commit 重跑会产生重复评论，属于已知限制。
3.  **本地完整回归（已完成）**：2026-11-09 全部 11 个测试脚本通过；真实 LLM 的合法 YAML、非法 YAML、Java SQL 注入样例均通过。详见 6.2；无需为重复验收频繁调用模型。
4.  **V1.0 最终验收**：主功能和本地回归完成；线上 Workflow 成功与评论存在已得到公开页面证据，但 Artifact 内容和评论与具体 Run 的精确绑定仍缺少可核查证据。受 GitHub 限流风险约束，本轮不额外 Push 触发测试。补齐这两项证据后即可完成最终签收。

### 中优先级

5.  README 和安装、配置、运行说明：已完成，包含离线和真实模型验证命令。
6.  GitHub Actions 工作流说明、安全边界说明：已完成。
7.  报告结构示例和已知限制说明：已完成；真实验收报告保留在本地忽略目录。

### YAML 误报专项（本地和真实模型样例验收已完成，待线上发布验收）

已完成：

- 找到误报对应的原始 Diff，并确认原输入只有 Diff 行片段。
- 增加 YAML 结构路径和缩进元数据，区分完整文件与局部 Diff。
- 优化 Prompt，明确区分 YAML 语法与 GitHub Actions schema。
- 添加合法和非法 YAML 回归样例及 `test_yaml_regression.py`。
- 保持现有 Java / SQL 高危审查链路、Policy 门禁和输出格式不变。

待后续受控验证：

- 真实 LLM 对照验证已于 2026-11-09 完成，不需要为此单独 Push。
- 在不频繁 Push 的前提下，选择一次 GitHub Workflow 运行核对线上输入和评论。

## 9. 当前项目目录结构（已知信息，需以本地仓库为准）

用户在 2026-11-02 提供的 VS Code 截图中确认过的主要结构：

``` text
ai-code-reviewer/
├── .github/
│   └── workflows/
│       ├── ai-review.yml
│       └── ai-review-comment.yml
├── .trae/
├── .vscode/
├── app/
│   └── __init__.py
├── examples/
│   ├── bad_code.diff
│   └── test.java
├── git_utils/
│   └── diff.py
├── reports/
│   └── review-report.json
├── reviewer/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── formatter.py
│   ├── locator.py
│   ├── models.py
│   ├── parser...
│   ├── commenter.py
│   └── github.py
├── main.py
├── requirements.txt
└── ...
```

注意：这是已知结构摘要，不是完整目录清单；`reviewer/`
下的完整文件名和其他目录必须以当前工作区为准，不得根据该示意图创建或删除文件。

## 10. 配置与实现约定

已知环境变量映射：

-   `CR_API_KEY` → `OPENAI_API_KEY`
-   `CR_BASE_URL` → `OPENAI_BASE_URL`
-   `CR_MODEL` → `LLM_MODEL`

GitHub Actions 中使用 Repository Secrets 注入模型配置。

LLM 调用目前继续使用：

``` python
client.chat.completions.create(...)
```

用户曾讨论是否改为 Responses
API，但明确决定：**当前先不改，作为后期优化点。** 不要在 V1.0
主线中擅自迁移。

Token 消耗统计、Prompt Cache 等优化也留到后期。

## 11. Git 状态与版本信息

已知在 2026-11-05 本轮测试开始前，用户执行 `git status` 得到：

``` text
On branch test001
Your branch is up to date with 'origin/test001'.

nothing to commit, working tree clean
```

当时最近 5 条提交：

``` text
eaa2bec (HEAD -> test001, origin/test001) update ignore
20cc0d1 fix: reduce false positives in YAML review
d066491 feat: create independent review comment for each commit
9b571e6 test: verify AI review comment update
7d765a9 测试ai cr001
```

之后用户在 `examples/test.java` 添加测试注释并执行 Commit + Push，GitHub
Actions 产生 Run #24 / #16。**本轮测试 Push 后的最新 Commit SHA 和最新
Git 状态尚未在交接时重新核对。**
后续已核对到当前本地分支为 `test001`，相比 `origin/test001` 领先提交
`c6169bf`；本轮 YAML 专项修改尚未提交或 Push。开始新的线上验证前仍应在
项目根目录执行：

``` powershell
git status
git log -5 --oneline
```

不要把上面 `eaa2bec` 当成当前最新提交。

此前用户曾遇到 SSH
`Permission denied (publickey)`，之后已报告"目前已成功推送"。因此 SSH
问题目前视为已解决，不要重复排查，除非再次出现。

## 12. 新助手接手后的第一步

先完整阅读本交接文档，然后：

1.  请用户确认当前是否仍在 `test001` 分支。
2.  执行 `git status` 和 `git log -5 --oneline`，确认本轮测试 Push
    后的真实状态。
3.  对照当前代码核实本交接文档中的实现状态。
4.  先确认当前工作区是否包含 YAML 专项的本地未提交修改。
5.  线上验证必须避开短时间内重复 Push，优先复用已有 Run 或由用户明确安排
    一次受控触发。

不要进入历史持久化，不要增加第三个 Workflow，也不要擅自进入 Phase 6。

------------------------------------------------------------------------

## 13. 关键决策速查

  决策项                                 已确认结论
  -------------------------------------- --------------------------------
  V1.0 是否做数据库/历史持久化           不做
  审查报告如何保存                       GitHub Actions Artifact
  是否保留现有质量门禁                   保留
  AI Review 达到阈值是否失败             是
  评论工作流是否因上游失败而停止         否，独立运行
  是否增加第三个 Quality Gate Workflow   不增加
  是否立即修 YAML 误报                   已完成本地及真实模型样例验收，待线上发布验收
  是否迁移 Responses API                 暂不迁移
  Token 统计 / Prompt Cache              后期优化
  开发方式                               中文、分步、每步等待用户反馈
