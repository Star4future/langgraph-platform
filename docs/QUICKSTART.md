# Quickstart — 5 minutes from clone to chat

## Prerequisites

- Python 3.12+
- (Optional) OpenAI API key — without it, the platform runs in MOCK_MODE which is fully functional for demos

## Step 1 — Install

```bash
git clone <repo>
cd langgraph-platform
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2 — Run

**Option A: Mock mode (no API key, instant deterministic responses)**

```bash
export VERTICAL=education
uvicorn core.api.main:app --reload --port 8000
```

**Option B: Real LLM mode**

```bash
cp .env.example .env
# Edit .env, set OPENAI_API_KEY=sk-...
export $(cat .env | xargs)
uvicorn core.api.main:app --reload --port 8000
```

## Step 3 — Test

```bash
# Health check
curl http://localhost:8000/api/health | jq

# Pricing question
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"How much is the AMC plan?","session_id":"demo","customer_id":"test"}'

# Complex multi-tool: refund + plan switch + family discount
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Switch from M3 to M4 and apply family discount for my 2nd child","session_id":"demo2","customer_id":"sarah.chen@example.com.au"}'

# Human escalation trigger
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"I want to refund my entire annual John Locke submission","session_id":"demo3","customer_id":"test"}'

# Check pending human-review queue
curl http://localhost:8000/api/pending-human | jq
```

## Step 4 — Run the eval harness

```bash
python -m eval.run_eval --vertical education
# Outputs: eval/EVAL-RESULTS.md
```

## Step 5 — Run tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## Next steps

- **Add a new vertical:** see `VERTICAL-AUTHORING-GUIDE.md`
- **Deploy to Vercel:** see `docs/DEPLOYMENT-GUIDE.md`
- **Understand the architecture:** see `ARCHITECTURE.md`
- **LangGraph design decisions:** see `docs/LANGGRAPH-DESIGN.md`
