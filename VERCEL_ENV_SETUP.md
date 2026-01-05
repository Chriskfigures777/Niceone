# Vercel Environment Variables Setup

## Required Environment Variables

You need to set these environment variables in your Vercel project settings for the build and runtime to work correctly.

### How to Add Environment Variables in Vercel:

1. Go to your Vercel project dashboard
2. Click on **Settings** → **Environment Variables**
3. Add each variable below
4. Make sure to set them for **Production**, **Preview**, and **Development** environments
5. **Redeploy** after adding variables

### Required Variables:

#### OpenAI (Required for Chatbot API)
```
OPENAI_API_KEY=sk-...
```
- Used by: `/api/chatbot` route
- **Critical**: Without this, the chatbot API will fail

#### LiveKit (Required for Voice Calls)
```
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
```
- Used by: `/api/connection-details` route
- **Critical**: Without these, voice calls won't work

#### Mem0 (Optional - for Memory Features)
```
MEM0_API_KEY=your_mem0_key
```
- Used by: Memory storage and retrieval
- **Optional**: App works without it, but memory features will be disabled

### Public Environment Variables (Client-Side)

If your frontend needs access to any of these, prefix them with `NEXT_PUBLIC_`:

```
NEXT_PUBLIC_LIVEKIT_URL=wss://your-livekit-server.com
```

**Note**: Never expose API keys or secrets with `NEXT_PUBLIC_` prefix!

### After Adding Variables:

1. **Redeploy** your project in Vercel
2. The build should now succeed
3. Test the application to ensure everything works

### Troubleshooting:

- **Build fails with "OPENAI_API_KEY missing"**: Make sure you added it in Vercel dashboard and redeployed
- **API routes return 500 errors**: Check that all required env vars are set
- **Build succeeds but runtime fails**: Check Vercel function logs for specific errors

