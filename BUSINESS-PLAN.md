# Business Plan — Multi-Vertical AI Customer Workflow Platform

**Working name:** LangGraph Platform
**Date:** May 2026
**Stage:** v1 — Education vertical (AceAchievers as first customer)

---

## 1. Executive Summary

We build a **multi-agent AI customer workflow platform** with a vertically pluggable architecture. The core engine (Triage → Resolver → Supervisor → Human-in-the-loop) is industry-agnostic; verticals (education, insurance, e-commerce, etc.) are isolated modules containing only domain-specific tools, prompts, and knowledge bases.

**Why this matters commercially:**
- A new vertical can be authored in **2 days** by following our `VERTICAL-AUTHORING-GUIDE.md`
- The same engineering investment yields 3 monetisation paths simultaneously: self-use, SaaS, white-label
- Australian SMB market is starved for production AI workflow tools that don't require an engineering team

**First customer:** AceAchievers (AU online education, founder-owned).
**Validation goal:** Prove the architecture by deploying education vertical to production, then prove transferability by authoring a second vertical (insurance demo) within 2 days.

---

## 2. The Problem

### 2.1 What customer service automation looks like today for AU SMBs

```
SMB option            Cost        Capability                  Result
─────────────────────────────────────────────────────────────────────────
Hire CSR             $65k/yr     Full human support          Doesn't scale
Outsource overseas   $35k/yr     Limited domain knowledge    Quality drops
Chatbot SaaS         $200/mo     Q&A only, no actions        Limited value
Build with engineer  $50k+ once  Custom but fragile          One-shot
Do nothing           $0          —                           Slow growth
```

### 2.2 What's missing

A **mid-tier solution** that:
- Handles complex multi-step workflows (not just Q&A)
- Takes actions (subscription changes, refund calculation, etc.) — not just chat
- Routes to a human at the right moments (high-value, low-confidence, policy edge cases)
- Costs less than a CSR salary
- Doesn't require the SMB to hire an engineer

LangGraph technology makes this possible for the first time. Our platform productises it.

---

## 3. The Solution

### 3.1 Product architecture

```
                Platform Core (we build & own)
                ┌──────────────────────────────┐
                │  Triage Agent                │
                │  Resolver Agent (tool calls) │
                │  Supervisor Agent (quality)  │
                │  Human-in-the-loop pause     │
                │  State machine + routing     │
                │  SSE streaming API           │
                │  Eval harness                │
                └──────────────┬───────────────┘
                               │
            ┌──────────────────┼─────────────────────┐
            │                  │                     │
       ┌────▼────┐        ┌────▼─────┐         ┌─────▼────┐
       │Education│        │ Insurance │         │ E-commerce│
       │ vertical│        │ vertical  │         │ vertical  │
       └─────────┘        └───────────┘         └───────────┘
       AceAchievers       NobleOak             Temple&Webster
       (first customer)   (target)             (target)
```

Each vertical contains only:
- `tools.py` — domain function calls (mocked or real backend)
- `prompts.py` — Triage/Resolver/Supervisor system prompts
- `state.py` — vertical-specific state fields
- `config.yaml` — business rules (refund thresholds, escalation triggers)
- `data/faq.md` — knowledge base

### 3.2 Time-to-market for new verticals

| Step | Time |
|------|------|
| Copy `_template/` to new vertical folder | 5 min |
| Write 5-10 domain-specific tool functions | 4 hours |
| Write 3 system prompts (Triage/Resolver/Supervisor) | 2 hours |
| Author 30-50 Q&A FAQ | 4 hours |
| Configure business rules | 1 hour |
| Eval harness with 30 scenarios | 3 hours |
| Deploy config (Vercel) | 1 hour |
| **Total** | **2 days** |

---

## 4. Three Monetisation Paths

### Path 1 — Self-use (Highest internal ROI)

**The author's project portfolio:**
- AceAchievers (education)
- Held (emotional support app)
- Sealify (consulting)
- LeapDigital (digital agency)
- LumarisGroup (business consulting)
- HuashuDesign (design services)

**Math:** 6 projects × $200/mo equivalent CSR cost = **$1,200/mo saved per month forever**, with one-time 2-day setup per project after the platform is built.

**Risk:** None. We control deployment.

### Path 2 — SaaS Product

**Product:** the platform — AI workflow agent for AU SMBs

**Pricing tiers (AUD, incl. GST):**

| Tier | Price | Includes |
|------|-------|----------|
| Starter | $99/mo | 1 workflow, 1,000 interactions/mo, basic FAQ, email support |
| Pro | $299/mo | 3 workflows, 10,000 interactions/mo, custom tools, Slack support, eval dashboard |
| Business | $799/mo | Unlimited workflows, 50,000 interactions/mo, white-label, priority support, Human-in-the-loop dashboard |
| Enterprise | Custom | On-prem deploy option, SLA, custom verticals built by us |

**Target customers:**

| Segment | Pain | LTV/yr |
|---------|------|--------|
| Online education / tutoring | Parent enquiry overflow | $3,600 |
| Allied health (physio, dental) | Booking + insurance enquiries | $3,600 |
| Boutique fitness / yoga | Membership + class booking | $1,200 |
| Real estate buyer agents | Property enquiry triage | $9,600 |
| Small law firms | Initial consultation triage | $9,600 |
| Childcare centres | Enrolment + fee enquiries | $3,600 |

**Go-to-market:**
- LinkedIn outreach (the author's network in AU SMB space)
- AceAchievers public demo as proof
- LeapDigital as distribution channel
- Content marketing: "How we built X with LangGraph" technical posts

**Year 1 target:** 30 paid customers across Starter/Pro tiers = ~$5K MRR

### Path 3 — White-label / Custom Build (Fastest cash, highest margin per deal)

**Product:** "AI Customer Workflow — Custom Build" delivered by LeapDigital

**Pricing structure:**

| Deliverable | Price |
|-------------|-------|
| Discovery + workflow design (1 week) | $5,000 |
| Custom vertical build (5-10 workflows) | $15,000 — $30,000 |
| Ongoing maintenance (per month) | $500 — $1,500 |
| Major feature additions | $3,000 per workflow |

**Target customers:**
- Mid-market companies ($5M-50M revenue) with complex customer ops
- Companies whose current customer service team is at capacity
- Companies who can't justify a full engineering hire

**Sales cycle:** 2-6 weeks
**Margin:** ~80% (after the author's time)

**Distribution:** LeapDigital owns customer relationships; LangGraph Platform is the underlying product (the author's IP).

---

## 5. Competitive Landscape

| Competitor | Their offer | Why we win |
|------------|-------------|------------|
| Voiceflow | Visual chatbot builder | They're stateless chat; we're stateful workflows with tool calls |
| Intercom Fin | AI customer support | $0.99/resolution — locks you into Intercom ecosystem; we're standalone & cheaper |
| Dust.tt | Multi-agent platform | French/EU focus, generic horizontal play; we're vertical & AU-localised |
| CrewAI | Open-source multi-agent framework | Code-only, no productised verticals; we package + deliver |
| Custom dev shops | Build from scratch | $50k+ per project; we deliver same in 2-3 weeks for $15-30k via reusable core |

**Our defensible moats:**
1. **Vertical library** — every vertical we build deepens our domain catalogue, raising switching cost for the next customer in the same industry
2. **AU localisation** — GST, Privacy Act, Fair Work compliance baked in; foreign competitors miss this
3. **Founder distribution** — the author has direct channels to AU SMB owners that overseas competitors can't access
4. **Eval-driven quality** — we ship eval harnesses with every vertical; competitors ship "it works on my demo"

---

## 6. Financial Model (Conservative)

### Year 1 — Foundation + first customers

| Source | Customers | Avg revenue/yr | Total |
|--------|-----------|----------------|-------|
| Self-use (author's projects) | 6 | Implicit savings $2,400 | $14,400 implicit value |
| SaaS Starter | 15 | $1,188 | $17,820 |
| SaaS Pro | 8 | $3,588 | $28,704 |
| White-label (via LeapDigital) | 3 | $25,000 | $75,000 |
| Maintenance recurring | 3 | $12,000 | $36,000 |
| **Year 1 cash revenue** | | | **$157,524** |

### Year 2 — Scale verticals + sales

| Source | Customers | Avg revenue/yr | Total |
|--------|-----------|----------------|-------|
| SaaS Starter | 60 | $1,188 | $71,280 |
| SaaS Pro | 30 | $3,588 | $107,640 |
| SaaS Business | 10 | $9,588 | $95,880 |
| White-label | 8 | $25,000 | $200,000 |
| Maintenance recurring | 11 | $12,000 | $132,000 |
| **Year 2 cash revenue** | | | **$606,800** |

### Cost structure (Year 1)

| Item | Annual |
|------|--------|
| OpenAI API costs (avg $0.05/interaction × 200K) | $10,000 |
| Vercel/hosting | $1,200 |
| Domain + ops tooling | $500 |
| Marketing / outreach | $3,000 |
| **Total OPEX** | **$14,700** |
| **Net Year 1** | **~$143,000** (excluding the author's time) |

---

## 7. Why Now

1. **LangGraph reached production maturity** (v0.2 in 2025, used by Klarna, Replit, Uber)
2. **GPT-4o mini pricing collapsed** — $0.15/1M input tokens makes per-interaction cost negligible
3. **AU SMB AI adoption gap** — Big consultancies serve enterprise; nobody serves SMB workflow needs
4. **The author has multiple owned projects** — internal testbed before external sales = de-risked learning
5. **Job market validation** — Latitude IT, NobleOak, Temple & Webster all hiring for "agent workflow" roles, confirming demand

---

## 8. 12-Month Roadmap

| Month | Milestone |
|-------|-----------|
| M1 (now) | Platform v1 + Education vertical deployed to AceAchievers |
| M2 | Insurance vertical authored (validates 2-day claim) + demo deployed |
| M3 | First paying customer via Path 3 (LeapDigital lead) |
| M4 | SaaS landing page + waitlist + Starter tier public |
| M5 | E-commerce vertical (target: Temple & Webster style use cases) |
| M6 | 5 SaaS paying customers + 2 white-label projects |
| M7-9 | Allied health + real estate verticals; 15 SaaS customers |
| M10-12 | Self-service vertical authoring (customer can build own vertical with our UI) |

---

## 9. What Could Kill This

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| OpenAI raises pricing 5× | Low | Platform supports multiple LLM providers via adapter pattern |
| LangGraph deprecates / breaks API | Med | Core abstracts LangGraph behind our own interface |
| Customer wants on-prem (no cloud OpenAI) | Med | Path 3 customers can pay extra; offer Anthropic/Mistral via adapter |
| Sales cycle longer than expected | High | Path 1 self-use generates value regardless; Path 3 funded by LeapDigital existing pipeline |
| Free alternative emerges (open-source SaaS) | Med | Verticals + AU localisation + service layer = moat; pure code is commodified anyway |

---

## 10. Founder Positioning

This platform turns the author into:
1. **A founder** of a real B2B SaaS company
2. **A consultant** with a productised offering (5-10× margin vs hourly consulting)
3. **An employable AI engineer** with production deployment evidence at AceAchievers + multiple vertical case studies

The same engineering hours fund all three trajectories. The optimal play is to keep building until one of them takes off, then go all-in.

---

*Document version: 1.0 · Author: @Star4future · Status: Live*
