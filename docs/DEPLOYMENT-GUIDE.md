# Deployment Guide

## Architecture overview

```
GitHub repo
    │
    │ git push
    ▼
Vercel build pipeline
    │ - pip install -r requirements.txt
    │ - auto-detect Python from .py extension
    │ - bundle core/ + verticals/ + selected deploy/<customer>/
    ▼
Vercel Serverless Function (Python 3.12)
    │ entry: deploy/<customer>/api/main.py
    ▼
Public domain (e.g. acmeacademy.com.au)
```

## Per-deployment files

Each customer deployment lives under `deploy/<customer-name>/`:

```
deploy/education-demo/
├── README.md         # customer-specific notes
├── .env.example      # env vars required
├── vercel.json       # routing + function config
├── api/main.py       # Vercel entry — picks vertical
└── widget.js         # frontend chat widget (customer-branded)
```

## Deploying a customer for the first time

```bash
cd deploy/education-demo
vercel link              # interactive: select project / create new
vercel --prod            # production deploy
```

**Key:** Vercel auto-detects Python from the `.py` extension in `api/`. **Do NOT specify `"runtime": "python3.11"` in vercel.json** — that's invalid format and breaks the build (lesson learned the hard way in an earlier deploy).

## Environment variables

Set these in **Vercel Project Settings → Environment Variables**:

| Variable | Required? | Value |
|----------|-----------|-------|
| `VERTICAL` | Yes | The vertical name (e.g. `education`) |
| `OPENAI_API_KEY` | **NO** for public demo deploys | Set only on private/staging deploys where you want real LLM |
| `LLM_MODEL` | No | Default `gpt-4o-mini` |
| `QUALITY_THRESHOLD` | No | Default `0.7` |
| `MAX_RETRY_COUNT` | No | Default `2` |

**Why no API key on public deploys?**
- Public demo = anyone can hit your endpoint = your bill
- MOCK_MODE is fully functional for demonstrations
- Real LLM mode only when you're behind auth (staging/internal)

## Adding a new customer of an existing vertical

You have AcmeAcademy running. Now MathPro Tutoring (different brand, same education vertical) wants to deploy:

```bash
cp -r deploy/education-demo deploy/mathpro
cd deploy/mathpro
# Edit widget.js — change brand + colors
# Edit README.md — point at mathpro.com.au domain
vercel link
vercel --prod
```

Total time: **30 minutes** (mostly waiting for build).

## Adding a new industry vertical and customer

Combination of two flows:

1. Author the vertical (2 days) — `VERTICAL-AUTHORING-GUIDE.md`
2. Create a deploy directory (30 minutes) — pattern above

Total: **~2.5 days** for a completely new industry + customer.

## Vercel ignore file (avoiding 100MB limit)

`.vercelignore` at project root should exclude:
- `eval/results/` (test artefacts can be large)
- `tests/`
- `.venv/`
- `*.pyc`
- Any large data files not needed at runtime

**Hard-won lesson:** Vercel has a per-file 100 MB upload limit. Move large files **out of the project directory** rather than relying on `.vercelignore` (it doesn't always parse complex patterns). See `EXPERIENCE-LOG.md` for the war story.

## Custom domain

```bash
vercel domains add acmeacademy.com.au
# Follow DNS instructions
```

## Health monitoring

```bash
curl https://acmeacademy.com.au/api/health
```

Should return:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "mode": "mock",
  "loaded_verticals": ["education"],
  "default_vertical": "education"
}
```

If `status != "ok"`, check `vercel logs <deployment-url>`.

## Rollback

```bash
vercel rollback                          # pick from list
vercel rollback <previous-deployment>    # specific deploy
```

## Multi-deployment workflows

For multi-deploy scenarios:

| Scenario | Approach |
|----------|----------|
| Single deploy, dedicated domain | `deploy/<name>/` + its own Vercel project |
| Multiple deploys, shared platform | One Vercel project, multiple `deploy/` directories, route by domain header |
| Multi-tenant | (v2 roadmap) — single deploy, vertical+brand selected by subdomain |
