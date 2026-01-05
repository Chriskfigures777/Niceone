# Quick Guide: Deploy Agent to Railway

## Step-by-Step Instructions

### 1. Sign up for Railway
- Go to [railway.app](https://railway.app)
- Sign up with your GitHub account (free tier available)

### 2. Create New Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repository: `Chriskfigures777/Niceone`
4. Railway will detect it's a Python project

### 3. Configure the Service
1. Railway will create a service automatically
2. Click on the service to open settings
3. Go to **Settings** tab
4. Set the following:

   **Root Directory:**
   ```
   app
   ```

   **Start Command:**
   ```
   uv run python agent.py start
   ```

   **Build Command (optional, Railway auto-detects):**
   ```
   uv sync
   ```

### 4. Add Environment Variables
Go to the **Variables** tab and add:

**Required:**
```
OPENAI_API_KEY=your_openai_api_key_here
CALCOM_API_KEY=your_calcom_api_key_here
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
```

**Optional:**
```
MEM0_API_KEY=your_mem0_key_if_using
DEFAULT_EMAIL=your_email@example.com
```

### 5. Deploy
1. Railway will automatically start deploying
2. Watch the logs to see the build progress
3. Once deployed, your agent will be running!

### 6. Check Logs
- Click on **Deployments** tab
- Click on the latest deployment
- View logs to ensure the agent started successfully
- You should see: "Starting agent server..." and "Agent name: Alex-2f2"

---

## Alternative: Deploy to Render

### 1. Sign up
- Go to [render.com](https://render.com)
- Sign up with GitHub

### 2. Create Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository: `Chriskfigures777/Niceone`

### 3. Configure
- **Name:** `niceone-agent` (or any name)
- **Root Directory:** `app`
- **Environment:** `Python 3`
- **Build Command:** `uv sync`
- **Start Command:** `uv run python agent.py start`

### 4. Add Environment Variables
Same as Railway - add all the required variables in the **Environment** section

### 5. Deploy
Click **"Create Web Service"** and Render will deploy your agent.

---

## Verify Deployment

Once deployed, check the logs. You should see:
- ✅ Agent server starting
- ✅ Agent name: Alex-2f2
- ✅ Connected to LiveKit
- ✅ Waiting for jobs

If you see errors, check:
1. All environment variables are set correctly
2. LiveKit server is accessible
3. API keys are valid

---

## Cost Estimate

**Railway:**
- Free tier: $5 credit/month
- Hobby plan: $5/month (if you exceed free tier)

**Render:**
- Free tier: Available (with limitations)
- Starter: $7/month

Both are very affordable for starting out!

