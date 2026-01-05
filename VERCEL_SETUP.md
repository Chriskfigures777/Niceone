# Vercel Setup Instructions

## Important: Root Directory Configuration

The `rootDirectory` cannot be set in `vercel.json` - it must be configured in the Vercel dashboard.

## Steps to Configure:

1. **Go to your Vercel project dashboard**
2. **Click on "Settings"** tab
3. **Go to "General"** section
4. **Find "Root Directory"** setting
5. **Set it to:** `app`
6. **Save the changes**

## Alternative: Project Settings

If you're creating a new project:

1. When importing from GitHub, click **"Configure Project"**
2. In the **"Root Directory"** field, enter: `app`
3. Vercel will automatically detect Next.js
4. The build commands in `vercel.json` will work correctly

## Current vercel.json Configuration

The `vercel.json` now has:
- ✅ Build command: `cd app && pnpm install && pnpm build`
- ✅ Output directory: `app/.next`
- ✅ Install command: `cd app && pnpm install`
- ✅ Framework: `nextjs`

**Note:** The `cd app` commands are needed because Vercel runs from the repository root, not the `app/` directory.

## After Setting Root Directory

Once you set the root directory to `app` in the dashboard, you can optionally simplify `vercel.json` to:

```json
{
  "buildCommand": "pnpm install && pnpm build",
  "outputDirectory": ".next",
  "installCommand": "pnpm install",
  "framework": "nextjs"
}
```

But the current configuration will work either way!

