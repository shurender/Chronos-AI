# Deploy Chronos on Vercel + Render

## Backend: Render

1. In Render, click **New +** -> **Blueprint**.
2. Connect the GitHub repo.
3. Select `render.yaml`.
4. Create the service.
5. Add secret environment values in Render:

```env
FIREWORKS_API_KEY=your_fireworks_key
TAVILY_API_KEY=your_tavily_key
GITHUB_TOKEN=optional_github_token
```

Render will use:

- Dockerfile: `Dockerfile.backend`
- Health check: `/health`
- Port: backend listens on `8000`

After deploy, verify:

```bash
curl https://YOUR_RENDER_SERVICE.onrender.com/health
curl https://YOUR_RENDER_SERVICE.onrender.com/debug/config
```

## Frontend: Vercel

The frontend is already configured by `Frontend/vercel.json`.

Set this Vercel environment variable:

```env
VITE_API_BASE_URL=https://YOUR_RENDER_SERVICE.onrender.com
```

Redeploy Vercel after changing it.

Update Render `CORS_ORIGINS` if your final Vercel domain differs:

```env
CORS_ORIGINS=https://chronos-ai-frontend.vercel.app
```
