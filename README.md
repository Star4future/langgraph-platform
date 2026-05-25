# LangGraph Multi-Vertical Customer Workflow Platform

> Production-ready multi-agent AI customer workflows with industry-pluggable verticals.
> Built on **LangGraph** + **FastAPI** + **OpenAI** · Deployed on **Vercel**
>
> 🌐 **Live demo:** [langgraph-platform-demo.vercel.app](https://langgraph-platform-demo.vercel.app)

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)]()
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-1C3C3C)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)]()
[![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?logo=vercel&logoColor=white)]()
[![MIT](https://img.shields.io/badge/License-MIT-yellow)]()

---

## What This Is

A **multi-agent AI workflow engine** with a strict separation between an industry-agnostic core and pluggable vertical modules.

- **Core engine:** Triage → Resolver → Supervisor → Human-in-the-loop, with state machine, conditional routing, retry loops, and SSE streaming
- **Vertical = directory of artifacts:** tools.py, prompts.py, state.py, config.yaml, faq.md
- **Time to author a new vertical:** ~2 days (see `VERTICAL-AUTHORING-GUIDE.md`)
- **First vertical:** `education/` — deployed to https://aceachievers.com.au

---

## Why This Exists

Three audiences, same engine:

| Audience | Use case |
|----------|----------|
| **Author's own product portfolio** | Self-use across 6 owned websites (education, emotional support, design, consulting) |
| **AU SMB SaaS market** | $99-799/mo subscription tiers for tutoring centres, allied health, fitness, real estate, law |
| **Mid-market white-label** | $15k-30k custom builds delivered via partner agency |

See `BUSINESS-PLAN.md` for the full model.

---

## Quick Start (60 seconds)

```bash
# 1. Clone & install
git clone https://github.com/Star4future/langgraph-platform
cd langgraph-platform
pip install -r requirements.txt

# 2. Set vertical + run (MOCK_MODE — no API key needed)
export VERTICAL=education
uvicorn core.api.main:app --reload --port 8000

# 3. Test the chat
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"I want to switch from M3 to M4 and refund the difference","session_id":"demo","customer_id":"parent_001"}'
```

You'll see SSE events stream back: `triage` → `tool_call` → `tool_result` → `token` → `done`.

---

## Architecture (10-second version)

```
┌─────────────────────────────────────────────────┐
│  core/   — industry-agnostic engine             │
│  ├── agents/  (triage, resolver, supervisor)    │
│  ├── graph_builder.py                            │
│  ├── llm/     (mock + openai adapters)           │
│  └── api/     (FastAPI + SSE)                    │
├─────────────────────────────────────────────────┤
│  verticals/  — plug-in industry modules         │
│  ├── education/   ← AceAchievers                 │
│  ├── _template/   ← copy this for new industry   │
│  └── (insurance/, ecommerce/, etc.)              │
├─────────────────────────────────────────────────┤
│  deploy/   — per-customer deployment configs    │
│  └── aceachievers/  ← Vercel + custom widget     │
└─────────────────────────────────────────────────┘
```

See `ARCHITECTURE.md` for full diagrams and design decisions.

---

## What's in v1

✅ Core engine (Triage / Resolver / Supervisor / Human-in-the-loop)
✅ Education vertical (8 mock tools, AU-localised prompts, 40-Q FAQ)
✅ Vercel deployment config for AceAchievers
✅ Eval harness (30 scenarios, 6 metrics)
✅ Mock LLM for zero-cost demos
✅ SSE streaming widget
✅ Vertical authoring guide
✅ Full unit + integration tests

🔜 v1.1 — Insurance vertical (validation that 2-day vertical authoring claim is real)
🔜 v1.2 — Multi-LLM routing (cheap Triage, premium Resolver)
🔜 v1.3 — Long-term memory (Redis)

---

## Performance & Eval

Latest education vertical eval run (`eval/EVAL-RESULTS.md`):

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Resolution rate | 73% | ≥ 70% | ✓ |
| Intent accuracy | 90% | ≥ 85% | ✓ |
| Human-escalation precision | 95% | ≥ 90% | ✓ |
| Avg quality score | 0.78 | ≥ 0.70 | ✓ |
| Avg retry count | 0.27 | ≤ 0.5 | ✓ |
| P50 latency | 2.3s | ≤ 3s | ✓ |

---

## Repository Layout

```
langgraph-platform/
├── BUSINESS-PLAN.md          ← commercial model, 3 monetisation paths
├── ARCHITECTURE.md           ← technical architecture + design decisions
├── VERTICAL-AUTHORING-GUIDE.md  ← author new industry in 2 days
├── README.md                 ← this file
├── EXPERIENCE-LOG.md         ← lessons from 0→1 (replicable knowledge)
│
├── core/                     ← industry-agnostic engine
├── verticals/                ← industry modules (education, _template)
├── deploy/                   ← customer deployments
├── eval/                     ← scenarios + harness + reports
├── tests/                    ← unit + integration
└── docs/                     ← QUICKSTART, LANGGRAPH-DESIGN, DEPLOYMENT-GUIDE
```

---

## Deployment

```bash
# Deploy to Vercel (production)
cd deploy/aceachievers
vercel --prod

# Health check
curl https://aceachievers.com.au/api/health
```

See `docs/DEPLOYMENT-GUIDE.md`.

---

## Authoring a New Vertical

```bash
# 1. Copy template
cp -r verticals/_template verticals/insurance

# 2. Fill in
#    - tools.py     (5-10 domain functions)
#    - prompts.py   (Triage / Resolver / Supervisor system prompts)
#    - state.py     (extend BaseSupportState with vertical fields)
#    - config.yaml  (business rules: escalation thresholds, etc.)
#    - data/faq.md  (30-50 Q&A)

# 3. Add to verticals/__init__.py registry

# 4. Run eval
python -m eval.run_eval --vertical insurance

# Total time: 2 days
```

Full step-by-step in `VERTICAL-AUTHORING-GUIDE.md`.

---

## License

MIT — see `LICENSE`.

---

## Background

This platform was extracted from production work on **aceachievers.com.au** — an Australian education brand — where a simpler Q&A bot (OpenAI Assistants API + File Search) hit a complexity ceiling for multi-step parent service requests. LangGraph + multi-agent architecture became necessary; productising it as a platform unlocks reuse across an owned-projects portfolio and the AU SMB market.

Related work:
- AceAchievers Parent Concierge v1: `aceachievers/api/main.py` (Assistants API)
- ADR-001: Why managed vector store, not custom RAG (`aceachievers/portfolio/articles/`)
- Original LangGraph project brief: `job-system/learning/langgraph_project_brief.md`

---

*Built by [@Star4future](https://github.com/Star4future) · May 2026 · MIT licensed*
