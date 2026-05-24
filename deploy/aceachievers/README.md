# Deploy: AceAchievers

Production Vercel deployment of the LangGraph Platform using the `education` vertical.

## Configuration

| File | Purpose |
|------|---------|
| `vercel.json` | Vercel routing + Python function config |
| `api/main.py` | Vercel entry — instantiates `core.api.create_app(default_vertical="education")` |
| `widget.js` | Frontend floating chat widget (drop-in `<script>` tag) |
| `.env.example` | Required env vars |

## Local dev

```bash
cd deploy/aceachievers
cp .env.example .env
pip install -r ../../requirements.txt
VERTICAL=education uvicorn api.main:app --reload --port 8000
```

Test:
```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"refund please","session_id":"s1","customer_id":"sarah.chen@example.com.au"}'
```

## Deploy to production

```bash
cd deploy/aceachievers
vercel --prod
```

**Important:** Vercel project settings should NOT set `OPENAI_API_KEY` — the production deploy stays in MOCK_MODE so anyone visiting can use the demo without billing the project. Real LLM mode is enabled only for local dev or internal staging.

## Embed widget on aceachievers.com.au

Add to homepage:
```html
<script src="/widget.js" data-api="https://aceachievers.com.au/api/chat"></script>
```

Widget will inject a floating chat bubble in the bottom-right corner.

## Health check

```bash
curl https://aceachievers.com.au/api/health
```

## Architecture note

This deployment uses:
- **Platform core** from `../../core/` (unchanged across all deploys)
- **Education vertical** from `../../verticals/education/` (industry-specific)
- **AceAchievers branding** here in `deploy/aceachievers/` (customer-specific)

To deploy a different customer using the same education vertical, copy this entire directory (`deploy/aceachievers/` → `deploy/other-school/`) and edit only `widget.js` (branding) + `vercel.json` (domain).

To deploy a completely different industry (e.g. insurance), use a different vertical — see `verticals/insurance/` (when authored) and create `deploy/<customer>/` using it.
