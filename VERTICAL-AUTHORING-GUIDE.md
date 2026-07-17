# Vertical Authoring Guide

> How to ship a new industry vertical in 2 working days.

**Audience:** Future maintainer, future contractor, future paying customer.
**Prerequisite:** Python 3.12, basic comfort with `pip install`, ability to read YAML and Markdown.
**You do NOT need:** Deep LangGraph knowledge. The framework is hidden behind our base classes.

---

## The Map

A "vertical" is an industry-flavoured plug-in. Same engine, different lens.

```
verticals/
├── education/        ← AcmeAcademy (built, reference example)
├── _template/        ← copy this; the skeleton for new industries
└── insurance/        ← (your new vertical goes here)
```

Each vertical is a directory with **6 required files** and 1 optional. That's it.

---

## The 8-Step Workflow (2 days = ~16 hours)

### Step 1 — Bootstrap (15 minutes)

**macOS / Linux (bash):**
```bash
cd langgraph-platform/verticals
cp -r _template <your_industry_name>
cd <your_industry_name>
# Rename template files
for f in *.template; do mv "$f" "${f%.template}"; done
```

**Windows (PowerShell):**
```powershell
cd langgraph-platform\verticals
Copy-Item _template -Recurse -Destination <your_industry_name>
cd <your_industry_name>
# Rename template files
Get-ChildItem -Filter "*.template" | Rename-Item -NewName { $_.Name -replace '\.template$', '' }
```

Industry names use **snake_case singular** (`insurance`, not `Insurance` or `insurances`).

---

### Step 2 — Define your tools (4 hours)

Open `tools.py` and replace the template tools with **your industry's domain functions**.

Each tool is a Python function with:
- A clear docstring (the LLM reads this to decide when to call it)
- Type-hinted args and return values
- Mock implementation (returns realistic fake data — real API integration later)

**Example: insurance vertical**

```python
from core.agents.tools import tool

@tool
def lookup_policy(policy_number: str) -> dict:
    """Look up an insurance policy by its number.
    Returns: policy_id, policy_type, cover_amount, premium, renewal_date.
    Use this whenever a customer references a specific policy."""
    return {
        "policy_id": policy_number,
        "policy_type": "Term Life",
        "cover_amount": 500_000,
        "premium_per_month": 78.50,
        "renewal_date": "2027-03-15",
    }

@tool
def calculate_claim_estimate(policy_id: str, claim_reason: str) -> dict:
    """Estimate the claim amount for a policy + reason combination.
    Returns: estimated_amount, processing_days, requires_documents."""
    ...

@tool
def schedule_callback(customer_id: str, time_window: str) -> bool:
    """Schedule a callback from a human claims officer."""
    ...
```

**Rule of thumb:** 5-10 tools per vertical. More than 10 and the LLM gets confused; fewer than 5 and you can't handle much.

**Common patterns:**
- `lookup_*` — read operations
- `calculate_*` — compute decisions
- `schedule_*`, `send_*`, `create_*` — write operations (always mock until real API exists)
- `escalate_*` — explicit human handoff triggers

---

### Step 3 — Write the three system prompts (2 hours)

Open `prompts.py`. You need three prompts:

#### 3a. `TRIAGE_PROMPT`

Classifies the customer's intent. Lists your allowed intents.

```python
TRIAGE_PROMPT = """You are the Triage agent for [Industry] customer service.

Classify the customer message into ONE intent:
- claim_filing
- policy_question
- billing
- complaint
- general

Output JSON: {"intent": "...", "confidence": 0..1, "urgency": "low|medium|high", "requires_human": bool}

Escalate to human if:
- Complaint with strong negative sentiment
- Threat of legal action
- Confidence < 0.5
- Claim amount mentioned > $10,000
"""
```

#### 3b. `RESOLVER_PROMPT`

The customer-facing personality. Defines the tone and the "rules of engagement."

```python
RESOLVER_PROMPT = """You are a [Brand]'s AI customer service assistant.

You help with [your industry's typical requests].

RULES:
1. Only quote facts that appear in tool results or the FAQ
2. Never invent prices, dates, or coverage details
3. All amounts in AUD including GST
4. If unsure, schedule a callback
5. Keep responses under 3 short paragraphs

You have access to these tools: [tool list]
"""
```

**Critical:** The "RULES" section prevents LLM hallucination. Steal AcmeAcademy's pattern verbatim and adapt.

#### 3c. `SUPERVISOR_PROMPT`

The quality gate. Scores the Resolver's draft.

```python
SUPERVISOR_PROMPT = """You score customer service responses for [Industry].

Score 0.0-1.0 on:
- Accuracy: facts match tool results
- Tone: warm + professional, not pushy
- Completeness: addresses the actual question
- Safety: no policy/price hallucinations

Pass threshold: 0.7
Output JSON: {"quality_score": 0..1, "passes": bool, "feedback": "..."}
"""
```

---

### Step 4 — Extend state and config (1 hour)

#### 4a. `state.py`

```python
from core.state import BaseSupportState

class InsuranceState(BaseSupportState):
    policy_id: str | None
    claim_id: str | None
    customer_tier: str | None  # "standard" | "premium" | "vip"
```

Add ONLY fields specific to your industry. Don't redefine fields that are in `BaseSupportState`.

#### 4b. `config.yaml`

```yaml
vertical:
  name: insurance
  display_name: "Insurance / Financial Services"

business_rules:
  human_escalation:
    - claim_amount_above: 10000
    - confidence_below: 0.5
    - keywords: ["lawyer", "ombudsman", "complaint"]
  retry_limit: 2

branding:
  brand_name: "YourBrand Insurance"
  support_email: "support@yourbrand.com.au"
  business_hours: "Mon-Fri 9am-5pm AEST"

llm:
  triage_model: "gpt-4o-mini"
  resolver_model: "gpt-4o-mini"
  supervisor_model: "gpt-4o-mini"
```

---

### Step 5 — Write the FAQ (3-4 hours)

`data/faq.md` — write 30-50 Q&A from the customer's perspective.

```markdown
## Claims

### How do I file a claim?

You can file a claim by:
- Calling 1300-XXX-XXX during business hours
- Submitting online at yourbrand.com.au/claims
- Talking to me — I can start the process and book a callback

You'll need: policy number, date of incident, brief description.

### How long does a claim take to process?

- Simple claims: 3-5 business days
- Claims requiring assessment: 10-14 business days
- Complex/disputed claims: 21+ business days
```

**Rules:**
- Question = how a real customer asks it (use their words, not yours)
- Answer = 2-3 short paragraphs max
- Include any policy details (timeframes, eligibility, exclusions)
- Always end ambiguous questions with "contact support@..."

---

### Step 6 — Mock data + responses (2 hours)

`data/mock_db.json` — fake records your tools return.

```json
{
  "policies": {
    "POL-12345": {"type": "Term Life", "cover": 500000, "premium": 78.50},
    "POL-67890": {"type": "Income Protection", "cover": 80000, "premium": 145.20}
  },
  "customers": {
    "CUS-001": {"name": "Sarah Chen", "tier": "premium", "policies": ["POL-12345"]}
  }
}
```

`mock_responses.json` — for `MOCK_MODE`, maps trigger keywords to canned LLM responses (no real API call needed). Lets your demo work without an API key.

**Full schema (all fields, most are optional):**

```json
[
  {
    "keywords":         ["claim", "file", "submit"],
    "stage":            "triage",
    "intent":           "claim_filing",
    "confidence":       0.92,
    "urgency":          "medium",
    "requires_human":   false,
    "tool_calls": [
      { "name": "lookup_policy", "arguments": {"policy_number": "POL-12345"} }
    ],
    "response":         "I can help start your claim. I see you have a Term Life policy...",
    "quality_score":    0.85,
    "feedback":         "Good — accurate and complete."
  }
]
```

**Field reference:**

| Field | Required | Used by | Notes |
|-------|----------|---------|-------|
| `keywords` | ✓ | All | Match triggers (OR logic, case-insensitive). First match wins within a stage; the final entry is the catch-all fallback. |
| `stage` | recommended | All | `"triage"`, `"resolver"`, `"supervisor"`, or `"any"` (default). One scenario can serve multiple stages by using `"any"`. |
| `intent` | triage only | Triage | Output intent string. |
| `confidence` | triage only | Triage | 0..1, default 0.7. |
| `urgency` | triage only | Triage | `"low"`, `"medium"`, `"high"`. |
| `requires_human` | triage only | Triage | Set `true` for high-risk keywords. |
| `tool_calls` | resolver only | Resolver | List of `{name, arguments}` dicts. Present = mock makes a tool-call round; absent = return `response` directly. |
| `response` | resolver only | Resolver | The draft the Resolver returns after tools finish. |
| `quality_score` | supervisor only | Supervisor | 0..1. Below 0.7 triggers retry. |
| `feedback` | supervisor only | Supervisor | Shown to Resolver on retry. |

**Matching algorithm (from `core/llm/mock.py`):**
1. Filter by `stage` (skip if stage mismatch and not `"any"`).
2. Return the first scenario whose `keywords` list has any word present in the user message.
3. If no match: fall back to the **last entry** in the list — put a generic catch-all scenario last.

---

### Step 7 — Register your vertical (5 minutes)

Edit `verticals/__init__.py`:

```python
from .education import VERTICAL as education_vertical
from .insurance import VERTICAL as insurance_vertical  # ← add this

VERTICALS = {
    "education": education_vertical,
    "insurance": insurance_vertical,  # ← add this
}
```

---

### Step 8 — Build your eval (3 hours)

Copy `eval/datasets/education_30.jsonl` to `eval/datasets/insurance_30.jsonl`.

Replace the 30 scenarios with industry-specific ones. Structure each as:

```json
{
  "id": "T001",
  "category": "claim_filing",
  "difficulty": "easy",
  "input": "I want to file a claim for my car accident yesterday",
  "expected_intent": "claim_filing",
  "expected_tools": ["lookup_policy", "schedule_callback"],
  "should_require_human": false,
  "quality_threshold": 0.75
}
```

**Distribution rule:** 10 easy + 15 medium + 5 hard. At least 5 high-risk scenarios that should trigger human escalation.

Then:
```bash
python -m eval.run_eval --vertical insurance
```

If `resolution_rate >= 0.70` you ship. Otherwise iterate on prompts/tools.

---

## Validation Checklist

Before declaring "done":

- [ ] All 6 required files exist in `verticals/<name>/`
- [ ] `__init__.py` exports `VERTICAL` dict with all keys
- [ ] Vertical registered in `verticals/__init__.py`
- [ ] FAQ has ≥ 30 Q&A
- [ ] Tools have docstrings (the LLM reads them)
- [ ] Mock data is realistic (no "Lorem ipsum")
- [ ] Eval passes: `resolution_rate >= 0.70`
- [ ] `python scripts/check_layering.py` passes (no core ← vertical leaks)
- [ ] Local server runs: `VERTICAL=insurance uvicorn core.api.main:app`
- [ ] Test one tool-calling conversation end-to-end manually

---

## Time Budget (16-hour vertical)

| Step | Task | Hours |
|------|------|-------|
| 1 | Bootstrap (copy template, rename files) | 0.25 |
| 2 | Define tools (5-10 tools + mock implementations) | 4 |
| 3 | Write 3 system prompts (triage / resolver / supervisor) | 2 |
| 4 | State extension + config.yaml | 1 |
| 5 | FAQ (30-50 Q&A in data/faq.md) | 4 |
| 6 | Mock data + mock_responses.json | 2 |
| 7 | Register vertical in verticals/__init__.py | 0.25 |
| 8 | Eval: 30 scenarios + run_eval | 3 |
| — | **Total** | **~16.5 hours** |

Spread over 2 days with breaks. Sustainable.

---

## What NOT to Do

❌ **Don't modify `core/`.** That's the engine. Touching it breaks every other vertical.

❌ **Don't import another vertical.** Verticals are isolated. If you find yourself wanting another vertical's tool, the right answer is to copy the tool's pattern into your own vertical.

❌ **Don't write too many tools.** > 10 tools = LLM confusion. Split into multiple verticals if the domain is huge.

❌ **Don't skip the eval.** "It works on my demo" is not shipping. Eval catches the 30% of cases you didn't think of.

❌ **Don't put real customer data in `mock_db.json`.** Mock data only.

---

## Common Pitfalls

These are real friction points that will cost you 30-90 minutes each if you don't know about them:

**1. ImportError from graph.py after renaming state class**
`graph.py` and `__init__.py` both import your state class by name. When you rename it from `VerticalState`, change it in **both** files. Grep: `grep -rn "VerticalState" verticals/<your_name>/`.

**2. Mock responses not matching**
The keyword matcher is case-insensitive and uses OR logic within a scenario's `keywords` list, but respects the `stage` filter. If your keywords aren't triggering, check: (a) is the `stage` set correctly? (b) are the keywords present verbatim in the test input? (c) is there a more-specific scenario earlier in the list stealing the match?

**3. Eval pass rate suspiciously low (< 30%)**
This usually means your `mock_responses.json` scenarios don't cover the eval dataset's input phrases. Map each `education_30.jsonl` input keyword to at least one mock scenario. The last entry in `mock_responses.json` is the catch-all fallback — make sure it has a generic but quality-passing response.

**4. `graph.update_state` fails on resume**
This means the graph was compiled without a checkpointer, or the thread_id wasn't passed to the original `astream_events` call. Both must use `config={"configurable": {"thread_id": session_id}}`.

**5. Local run works but Vercel returns 500 on first request**
Common cause: top-level import of a module that's in `.vercelignore`. Always lazy-import inside function bodies for any module that might be excluded from the Vercel build.

---

## Getting Help

- **Reference vertical:** `verticals/education/` — read this in full before authoring
- **Architecture:** `ARCHITECTURE.md` § 5 (Vertical Module Contract)
- **LangGraph patterns:** `docs/LANGGRAPH-DESIGN.md`
- **Stuck?** Open an issue in the repo with your `verticals/<name>/` snapshot

---

*v1.0 · May 2026*
