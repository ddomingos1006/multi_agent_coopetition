# Context Window Parliament showcase

Replay data comes from the deterministic Python worlds and policies in this repository.

```bash
python showcase/exporter/export_replays.py
python showcase/exporter/export_strategy_summary.py
cd showcase
npm install
npm run dev
```

Run `npm run build` before shipping. The default hearing is `incident-response-medium-004` with the Trained Speaker policy.

## Deploy to Vercel

### Option A — repo root (simplest)

1. Import the repository in Vercel.
2. Leave **Root Directory** empty (repository root).
3. In **Project Settings → Build & Development Settings**, clear any custom **Install Command** and **Build Command** overrides so the repo-root `vercel.json` is used:
   - Install: `npm ci --prefix showcase`
   - Build: `npm run build --prefix showcase`
4. **Framework Preset:** Next.js.

### Option B — app subdirectory

1. Set **Root Directory** to `showcase/app`.
2. Clear install/build overrides so `showcase/app/vercel.json` applies:
   - Install: `cd .. && npm ci`
   - Build: `npm run build`

**Do not** combine Root Directory `showcase/app` with Install Command `npm ci --prefix showcase` — that path is wrong and causes the `EUSAGE` / missing lockfile error.

Sync your fork to latest `main` before redeploying. No environment variables are needed for the replay-only showcase.

For a CLI deployment:

```bash
npx vercel
npx vercel --prod
```

When the live Modal endpoint is connected later, add its public URL as a Vercel environment variable
and keep `HUD_API_KEY` and `ANTHROPIC_API_KEY` only in Modal secrets.

## Live Modal replay mode

The bundled replay JSON remains the default. To use live inference, deploy the Modal app and point
the Next.js app at the `live_replay` web function:

```bash
modal deploy ../modal_benchmark.py
```

Set these in Vercel or your local Next.js environment:

```bash
PARLIAMENT_MODAL_RUN_URL=https://<workspace>--context-window-parliament-benchmark-live-replay.modal.run
NEXT_PUBLIC_PARLIAMENT_LIVE=1
```

You can also enable live mode for one browser session with `?live=1`. If the Modal endpoint is not
configured or a live run fails, the frontend falls back to the bundled replay for the selected world.
Use `PARLIAMENT_MODAL_KEY` and `PARLIAMENT_MODAL_SECRET` when the Modal endpoint is protected with
proxy auth tokens.
