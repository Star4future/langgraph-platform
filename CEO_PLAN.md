# LangGraph 多行业客服工作流平台 — 作战计划书

**立项日期：** 2026-05-25
**包工头模式：** A 全新立项
**预估总时长：** 当前会话 + 1-2 次续作
**预估 token 消耗：** 高（多文档 + 多模块代码）

---

## 一、项目目标

> 建一个**核心通用、垂直可插拔**的 LangGraph 多 Agent 客服工作流平台。第一个垂直（教育）服务 AceAchievers 上线，同时架构本身能在 2 天内复制到任何新行业（保险、电商、诊所、健身等），支撑 Nemo 的三条商业路径：自用、SaaS、白标交付。

---

## 二、3 个核心成功变量（200% 标准）

### 变量 1：架构通用性 ⭐ 最高优先级

- **测量方式：** core/ 完全行业无关；verticals/_template/ 可在 2 天内被复制成新行业
- **200% 标准：** VERTICAL-AUTHORING-GUIDE.md 让任何工程师无需问 Claude 就能独立做出第二个 vertical
- **失败信号：** 任何 core/ 文件 import 了 verticals/，或 hardcode 了"education"/"AMC"/"parent"等字眼

### 变量 2：教育垂直完整可跑 ⭐ 核心验证

- **测量方式：** AceAchievers vertical 30 个 eval 场景跑通
- **200% 标准：**
  - resolution_rate ≥ 70%
  - intent_accuracy ≥ 85%
  - human_escalation_precision ≥ 90%
  - MOCK_MODE 零配置即可演示
- **失败信号：** 任何场景跑不通 / Mock 数据假到一眼看穿

### 变量 3：商业文档质量 ⭐ 卖出去的关键

- **测量方式：** 三份文档（BUSINESS-PLAN、ARCHITECTURE、VERTICAL-AUTHORING-GUIDE）
- **200% 标准：** 可同时用于三个场景：
  1. **投资场景**：投资人看完知道商业模式 + 护城河
  2. **销售场景**：客户看完知道 ROI + 接入成本
  3. **招聘场景**：招聘官看完知道技术深度 + 工程判断力
- **失败信号：** 文档泛泛而谈 / 没有具体数字 / 没有 mermaid 图

---

## 三、任务分解（WBS）

| ID | 任务 | Skill | 模型 | 验证重点 | 依赖 |
|----|------|-------|------|----------|------|
| task-001 | 目录骨架 + 商业 & 架构文档 | niuma | sonnet-4-6 | 变量 1+3：文档质量 + 行业无关性 | — |
| task-002 | Core 层：State + Graph Builder + Agent 基类 | niuma | sonnet-4-6 | 变量 1：core 完全行业无关 | task-001 |
| task-003 | Core 层：FastAPI + SSE + Mock LLM | niuma | sonnet-4-6 | 变量 1：API 接口可被任何 vertical 复用 | task-002 |
| task-004 | Education Vertical：工具 + Prompts + 数据 | niuma | sonnet-4-6 | 变量 2：8 个工具 mock 真实可信 | task-003 |
| task-005 | Education Vertical：组装图 + Vercel 部署配置 | niuma | sonnet-4-6 | 变量 2：可跑通端到端 | task-004 |
| task-006 | Vertical Template：脚手架 + 接入文档 | niuma | sonnet-4-6 | 变量 1：照着指南能 2 天接新行业 | task-005 |
| task-007 | Eval Harness：30 场景 + 跑分报告 | niuma | sonnet-4-6 | 变量 2：跑通 30 场景 ≥70% | task-005 |
| task-008 | 测试 + EXPERIENCE-LOG + 收尾 | niuma | sonnet-4-6 | 变量 1+2+3 全部 | task-007 |

---

## 四、Skill 匹配说明

| 任务 | 调用 Skill | 理由 |
|------|-----------|------|
| task-001 ~ 008 | `niuma` | 通用代码执行器，每个任务都是"写代码/写文档+按 spec 验收" |
| 每任务验收 | `jianchaguan` | 监察官按 3 变量 200% + 流程 60% 检验 |

**未调用 `task-decomposer` 的理由：** 包工头本人在阶段 4 已完成拆解（8 个任务 + 依赖链清晰），且每个任务粒度合理（不到 3 小时），无需二次拆解。

**大神参考（来自 nuwa/MASTER-INDEX.md）：**
- 商业模式部分参考 **Geoffrey Moore（Crossing the Chasm）** 的"垂直应用"理论 — 先攻克教育这个 beachhead，再用同架构横向扩张
- 架构部分参考 **Martin Fowler** 的 Strangler Fig Pattern — core/verticals 分层即此模式的体现

---

## 五、监察官检查清单

**通用检查（每个任务必查）：**
- 文件路径绝对路径 / 无误
- Python 文件有 docstring + type hints
- 无敏感信息泄露（API key、个人邮箱等）

**task-001（文档层）：**
- BUSINESS-PLAN.md 三条路径每条都有：客户画像 / 定价 / 销售周期 / 单客户经济
- ARCHITECTURE.md 必须有 mermaid 图
- README.md 有 Quick Start ≤ 5 行命令

**task-002（Core 层）：**
- 全文 grep "education\|AMC\|parent\|aceachievers" 应返回 0 结果
- Agent 基类用 abc.ABC + abstractmethod

**task-003（API 层）：**
- SSE 响应必须有 4 种事件类型：thread / token / citations / done
- Mock LLM 必须可独立运行（无网络）

**task-004 + 005（Education Vertical）：**
- 8 个工具全部实现 + 每个有 docstring 说明业务规则
- prompts 复用 aceachievers/api/main.py 的语气（澳洲、含 GST、不承诺）
- Vercel 配置：Python runtime auto-detect（不指定 "python3.11"，吸取上一项目教训）

**task-006（Template）：**
- 完整 `.template` 后缀文件（不被 Python 误执行）
- README 写出 "5 步骤接入新行业"

**task-007（Eval）：**
- 30 场景覆盖：billing(8) + plan_change(7) + refund(6) + family(4) + escalation(3) + general(2)
- 必须包含至少 5 个 high_risk 场景（验证 human-in-the-loop）

**task-008（收尾）：**
- 测试覆盖 core/ ≥ 60% 行覆盖
- EXPERIENCE-LOG.md 含：技术决策 / 踩坑 / 复用建议

---

## 六、风险与卡点预判

1. ⚠️ **MOCK_MODE 设计不够干净** — Mock LLM 容易写成 hardcoded if-else，破坏 vertical 抽象性。**对策：** Mock LLM 由 vertical 通过 `mock_responses.json` 注入，core 不知道任何业务关键词。
2. ⚠️ **Vertical 边界泄露到 Core** — 写 core 时容易顺手写"if intent == billing"等业务逻辑。**对策：** 监察官在 task-002/003 强制 grep 检查。
3. ⚠️ **LangGraph 依赖不可用** — Python 包 `langgraph` 需要 pip install，离线环境装不上。**对策：** core 抽象掉 langgraph 直接依赖，用适配器；离线时降级到内置 mini state machine。
4. ⚠️ **30 个 eval 场景质量浮夸** — 容易写成全是简单 case。**对策：** 强制场景分类（easy: medium: hard = 10:15:5），监察官查分布。

---

## 七、Nemo 决策点

执行过程中可能需要拍板：

- [ ] **是否真的不要 langgraph 包依赖？** （我倾向：用，业内标准就是它，但要包装一层适配器便于测试）→ **包工头自行决定使用 langgraph 包，monkey-patch 友好的写法，无需 Nemo 拍板**
- [ ] **Frontend widget 是否独立做新版还是复用 AceAchievers 的？** → **包工头决定：复用 aa-assistant.js 设计模式但写成 platform 级 widget，可被任何 vertical 实例化**
- [ ] **是否真的把 vertical 命名为 "education" 而非 "ace-achievers"？** → **决定：vertical 命名为 industry（education），deploy 命名为 customer（aceachievers）**

---

## 八、产出文件清单（执行完毕后应有）

```
langgraph-platform/
├── STATE.json
├── CEO_PLAN.md                         ← 本文件
├── PROGRESS.md                         ← 实时任务状态
├── CHANGELOG.md
├── REPORT.md                           ← 每阶段汇报
├── BUSINESS-PLAN.md                    ★ 商业核心
├── ARCHITECTURE.md                     ★ 技术核心
├── VERTICAL-AUTHORING-GUIDE.md         ★ 复制核心
├── README.md
├── EXPERIENCE-LOG.md                   ★ 经验沉淀
├── LICENSE
├── .gitignore
├── .env.example
├── requirements.txt
├── vercel.json                         (deploy 层)
│
├── core/                               ★ 行业无关
│   ├── __init__.py
│   ├── state.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── triage_base.py
│   │   ├── resolver_base.py
│   │   ├── supervisor_base.py
│   │   └── human_escalation.py
│   ├── graph_builder.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── mock.py
│   │   └── openai_client.py
│   └── api/
│       ├── __init__.py
│       ├── main.py
│       ├── sse.py
│       └── models.py
│
├── verticals/
│   ├── education/                      ★ AceAchievers 用
│   │   ├── __init__.py
│   │   ├── tools.py
│   │   ├── prompts.py
│   │   ├── state.py
│   │   ├── config.yaml
│   │   ├── graph.py
│   │   ├── mock_responses.json
│   │   └── data/
│   │       ├── faq.md
│   │       └── mock_db.json
│   │
│   └── _template/                      ★ 新行业脚手架
│       ├── README.md
│       ├── tools.py.template
│       ├── prompts.py.template
│       ├── state.py.template
│       ├── config.yaml.template
│       └── data/
│           └── faq.md.template
│
├── deploy/
│   └── aceachievers/
│       ├── README.md
│       ├── .env.example
│       ├── vercel.json
│       ├── api/main.py                 ← Vercel entry
│       └── widget.js                   ← Frontend widget
│
├── eval/
│   ├── run_eval.py
│   ├── metrics.py
│   ├── datasets/
│   │   └── education_30.jsonl
│   └── EVAL-RESULTS.md
│
├── tests/
│   ├── test_core_state.py
│   ├── test_education_tools.py
│   └── test_graph_e2e.py
│
├── docs/
│   ├── QUICKSTART.md
│   ├── LANGGRAPH-DESIGN.md
│   └── DEPLOYMENT-GUIDE.md
│
└── artifacts/                          ← 牛马/监察官产物
    ├── task-001/
    ├── task-002/
    └── ...
```

---

## 九、执行节奏

| 阶段 | 任务 | 估时 | 检查点 |
|------|------|------|--------|
| 第 1 段 | task-001 | 45 分钟 | 文档层完成 → Nemo 可读 BUSINESS-PLAN |
| 第 2 段 | task-002 + 003 | 90 分钟 | Core 层完成 → 可单独运行最小 graph |
| 第 3 段 | task-004 + 005 | 90 分钟 | Education 跑通 → Vercel 可部署 |
| 第 4 段 | task-006 + 007 | 60 分钟 | Template + Eval 完成 |
| 第 5 段 | task-008 | 30 分钟 | 测试 + 收尾 |

**总计：** 约 5-6 小时密集工作，预计需要 1-2 次续作。

---

*作战计划完成 — 立即进入执行阶段。包工头不停。*
