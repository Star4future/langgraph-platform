# `_template/` — New Vertical Scaffold

This is the starting point for a new industry vertical. Copy this directory and fill in the files. See `../../VERTICAL-AUTHORING-GUIDE.md` for the full step-by-step.

## 5-step copy

```bash
cd langgraph-platform/verticals
cp -r _template <your_industry>      # e.g. insurance, ecommerce, healthcare
cd <your_industry>

# Rename .template files (drop the suffix)
for f in *.template; do mv "$f" "${f%.template}"; done
mv data/faq.md.template data/faq.md

# Then edit each file (see VERTICAL-AUTHORING-GUIDE.md):
#   tools.py            ← 5-10 domain functions with @tool decorator
#   prompts.py          ← Triage / Resolver / Supervisor prompts
#   state.py            ← Add your industry fields to BaseSupportState
#   config.yaml         ← Business rules + thresholds
#   data/faq.md         ← 30-50 Q&A
#   data/mock_db.json   ← Realistic mock records
#   data/mock_responses.json  ← Canned scenarios for MOCK_MODE
```

## Register your vertical

Edit `verticals/__init__.py`:

```python
from .insurance import VERTICAL as insurance_vertical  # ← add

VERTICALS = {
    "education": education_vertical,
    "insurance": insurance_vertical,                    # ← add
}
```

## Validate

```bash
# Run the eval harness
python -m eval.run_eval --vertical insurance

# Run the local server
VERTICAL=insurance uvicorn core.api.main:app --reload --port 8000
```

If `resolution_rate >= 0.70`, you ship.

---

## Files in this template

| File | Purpose | When to edit |
|------|---------|--------------|
| `__init__.py` | Vertical entry point (exports `VERTICAL` dict) | Edit ONCE — replace vertical name |
| `tools.py.template` | Domain functions for the LLM to call | Heavy — 5-10 functions |
| `prompts.py.template` | Triage/Resolver/Supervisor system prompts | Heavy — 3 prompts |
| `state.py.template` | Industry state fields | Light — add 3-5 fields |
| `config.yaml.template` | Business rules + branding | Light — fill in values |
| `graph.py.template` | Assembles graph from tools+prompts+config | Tiny edit — change vertical name |
| `data/faq.md.template` | Knowledge base | Heavy — 30-50 Q&A |

---

*Estimated authoring time: 2 working days (~16 hours).*
