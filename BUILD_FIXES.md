# Build Fixes Applied

## Vercel Frontend Build Fix

**Problem:** Build commands were trying to `cd app` when `rootDirectory` was already set to `app/`

**Fix Applied:**
- Removed `cd app` from build and install commands in `vercel.json`
- Vercel automatically runs commands from the `rootDirectory`, so no need to cd

**Updated vercel.json:**
```json
{
  "buildCommand": "pnpm install && pnpm build",
  "outputDirectory": ".next",
  "installCommand": "pnpm install",
  "framework": "nextjs",
  "rootDirectory": "app"
}
```

## Railway Agent Build Fix

**Problem:** Railway needs proper configuration to install `uv` and build Python dependencies

**Fixes Applied:**
1. **railway.json** - Railway-specific configuration
2. **nixpacks.toml** - Build configuration for Railway's Nixpacks builder
3. **runtime.txt** - Python version specification
4. **build.sh** - Build script for manual builds
5. **Procfile** - Already existed, defines the start command

## Common Build Issues & Solutions

### Vercel Build Fails

**Issue:** "Cannot find module" or "Command failed"
- ✅ **Fixed:** Removed redundant `cd app` commands
- Check that `package.json` is in the `app/` directory
- Ensure `pnpm-lock.yaml` is committed
- Verify Node.js version (Vercel auto-detects from `package.json`)

**Issue:** "Missing environment variables"
- Add all required env vars in Vercel dashboard
- Use `NEXT_PUBLIC_` prefix for client-side variables

### Railway Build Fails

**Issue:** "uv: command not found"
- ✅ **Fixed:** Added `nixpacks.toml` with uv installation
- Railway will now auto-install uv during build

**Issue:** "Python version not found"
- ✅ **Fixed:** Added `runtime.txt` specifying Python 3.11
- Railway will use the specified version

**Issue:** "Dependencies not installing"
- ✅ **Fixed:** Added proper build commands in `nixpacks.toml`
- Ensure `uv.lock` is committed to the repository

**Issue:** "Agent not starting"
- Check that `Procfile` exists with: `web: uv run python agent.py start`
- Verify all environment variables are set in Railway dashboard
- Check logs for specific error messages

## Verification Steps

### Test Vercel Build Locally:
```bash
cd app
pnpm install
pnpm build
```

### Test Railway Build Locally:
```bash
cd app
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
uv sync
uv run python agent.py start
```

## Next Steps

1. **Vercel:** Redeploy - the build should now work
2. **Railway:** 
   - Connect your GitHub repo
   - Railway will auto-detect the configuration
   - Add environment variables
   - Deploy

Both builds should now succeed! 🎉

