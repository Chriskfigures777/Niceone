# Deployment Guide

This project consists of two main components:
1. **Next.js Frontend** - Deployed on Vercel
2. **LiveKit Agent (Python)** - Needs to run on a separate service

## Frontend Deployment (Vercel)

The Next.js frontend is configured for automatic deployment on Vercel.

### Setup Steps:
1. Go to [vercel.com](https://vercel.com) and sign in
2. Click "Add New Project"
3. Import repository: `Chriskfigures777/Niceone`
4. Vercel will automatically detect the Next.js app in the `app/` directory
5. Add environment variables (see `.env.example` for required variables)
6. Deploy

### Environment Variables for Vercel:
- `NEXT_PUBLIC_LIVEKIT_URL` - Your LiveKit server URL
- `NEXT_PUBLIC_LIVEKIT_API_KEY` - LiveKit API key
- `NEXT_PUBLIC_LIVEKIT_API_SECRET` - LiveKit API secret
- Any other public environment variables your app needs

## Agent Deployment

The Python agent needs to run as a long-running service. Vercel cannot host long-running processes, so you'll need to deploy it separately.

### Recommended Platforms:
- **Railway** (recommended) - Easy Python deployment
- **Render** - Free tier available
- **Fly.io** - Good for Python services
- **DigitalOcean App Platform** - Simple deployment
- **AWS/GCP/Azure** - For production scale

### Agent Deployment Steps:

#### Using Railway:
1. Go to [railway.app](https://railway.app)
2. Create new project from GitHub repo
3. Add Python service
4. Set root directory to `app/`
5. Set start command: `uv run python agent.py start`
6. Add environment variables:
   - `OPENAI_API_KEY`
   - `CALCOM_API_KEY`
   - `MEM0_API_KEY`
   - `LIVEKIT_URL`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
   - `DEFAULT_EMAIL` (optional)

#### Using Render:
1. Go to [render.com](https://render.com)
2. Create new Web Service
3. Connect GitHub repository
4. Set:
   - **Build Command**: `cd app && uv sync`
   - **Start Command**: `cd app && uv run python agent.py start`
   - **Environment**: Python 3
5. Add all required environment variables

### Local Development:

To run both services locally:

```bash
cd app
pnpm dev:all
```

Or use the start script:

```bash
cd app
./start.sh
```

### Production Start:

For production, start both services:

```bash
cd app
pnpm start:all
```

Or individually:

```bash
# Terminal 1 - Agent
cd app
pnpm start:agent

# Terminal 2 - Next.js Server
cd app
pnpm start
```

## Environment Variables

Create `.env.local` in the `app/` directory with:

```env
# OpenAI
OPENAI_API_KEY=your_openai_key

# Cal.com
CALCOM_API_KEY=your_calcom_key
DEFAULT_EMAIL=your_email@example.com

# Mem0 (optional)
MEM0_API_KEY=your_mem0_key

# LiveKit
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
```

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   Vercel        │         │  Agent Service   │
│   (Next.js)     │◄────────►│  (Python)        │
│   Frontend      │         │  LiveKit Agent   │
└─────────────────┘         └──────────────────┘
         │                           │
         │                           │
         └───────────┬───────────────┘
                     │
         ┌───────────▼───────────┐
         │   LiveKit Server      │
         │   (Cloud/On-Premise)  │
         └───────────────────────┘
```

The frontend connects to LiveKit, and the agent also connects to LiveKit. They communicate through the LiveKit server.

