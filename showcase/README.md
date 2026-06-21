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

1. Import the repository in Vercel.
2. Set **Root Directory** to `showcase/app` (Project Settings → General).
3. Leave **Framework Preset** on Next.js (defaults are fine once root directory is set).
4. `showcase/app/vercel.json` installs workspace deps from `showcase/` then builds this app.

No environment variables are needed for the current replay-only showcase.

For a CLI deployment:

```bash
npx vercel
npx vercel --prod
```

When the live Modal endpoint is connected later, add its public URL as a Vercel environment variable
and keep `HUD_API_KEY` and `ANTHROPIC_API_KEY` only in Modal secrets.
