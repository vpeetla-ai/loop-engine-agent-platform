# Production deployment

## Architecture

| Service | Host | Role |
|---------|------|------|
| **Demo UI** | Vercel | Static `demo/` — repo URL + task form |
| **API** | Render | FastAPI — LangGraph agent loop + repo fix |
| **Target repos** | GitHub | Cloned, fixed, PR opened (never direct push to `main`) |

## 1. GitHub token (required for PR workflow)

Create a [fine-grained personal access token](https://github.com/settings/tokens?type=beta):

- **Repository access:** Only select repositories you want LoopForge to fix
- **Permissions:**
  - Contents: Read and write
  - Pull requests: Read and write
  - Metadata: Read

Store as `GITHUB_TOKEN` on Render.

## 2. LLM API key (recommended)

Set `GROQ_API_KEY` on Render for real code generation on non-trivial repos.  
Without it, `MockLLM` runs (demo/fixture only).

## 3. Deploy API to Render

```bash
# Push repo to GitHub first, then:
# Render Dashboard → New → Blueprint → connect loop-engine-agent-platform
# Or use render.yaml (auto-detected)
```

Env vars on Render:

```env
GROQ_API_KEY=gsk_...
GITHUB_TOKEN=github_pat_...
PYTHONPATH=/app/src:/app/backend
```

Health check: `GET /health` → `github_configured: true`

## 4. Deploy demo to Vercel

```bash
cd loop-engine-agent-platform
npx vercel --prod
```

Set environment variable in Vercel (or inject in `demo/index.html`):

```html
<script>window.LOOPFORGE_API = "https://loopforge-api.onrender.com";</script>
```

## 5. Run from UI

1. Open demo URL
2. Paste `https://github.com/you/your-repo.git`
3. Task: `Find and fix all failing tests`
4. Mode: **Bugfix**
5. Check **Create Pull Request**
6. Click **Fix Repo & Open PR**

## PR workflow (what happens)

```text
clone main
  → pytest (baseline failures)
  → orchestrate → code → review → quality
  → git checkout -b loopforge/fix-{run_id}
  → git commit
  → git push origin loopforge/fix-{run_id}
  → GitHub API: POST /repos/{owner}/{repo}/pulls
  → returns pr_url
```

**Main is never pushed to.** All changes land on a fix branch + PR for human review.

## API reference

```bash
curl -X POST https://YOUR-API/api/repo-fix \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/org/repo.git",
    "branch": "main",
    "task": "Find and fix all failing tests",
    "mode": "bugfix",
    "create_pr": true
  }'
```

Response includes `pr_url`, `pr_branch`, `git_commit_sha`, `trace`.

### Observability (optional — Langfuse)

| Variable | Purpose |
|----------|---------|
| `LANGFUSE_PUBLIC_KEY` | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key |
| `LANGFUSE_HOST` | Default `https://cloud.langfuse.com` |
| `LANGFUSE_ENABLED` | `true` to export harness traces |

After a run, open Langfuse → **Traces** and filter by project. See [TRACE_LINKED_OBSERVABILITY](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/docs/TRACE_LINKED_OBSERVABILITY.md).

## Local dev

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export GITHUB_TOKEN=... GROQ_API_KEY=...
uvicorn backend.app.main:app --reload --port 8000
```

Test on fixture (no GitHub):

```bash
pytest tests/test_repo_fix.py -q
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `no_github_token` | Set `GITHUB_TOKEN` on Render |
| `git clone failed` | Repo must be public or token needs access |
| `push failed` | Token needs Contents write on target repo |
| PR create 422 | Branch may already exist; re-run with new run_id |
| Tests fail on Node/Rust repo | v1 supports pytest; extend `WorkspaceManager.run_pytest` |
