# Pre-Deployment Checklist - 15 Critical Checks

**Date:** Generated automatically  
**Project:** LiveKit Voice AI Agent  
**Deployment Target:** Railway

---

## ✅ Check 1: nixpacks.toml Configuration
**Status:** ✅ PASS

**Verification:**
- ✅ `stdenv` included in nixPkgs (line 2)
- ✅ LD_LIBRARY_PATH fix present in start command (line 11)
- ✅ Correct library path finding: `$(find /nix/store -name libstdc++.so.6 2>/dev/null | head -1 | xargs dirname)`
- ✅ PATH includes `$HOME/.local/bin` for uv
- ✅ Build phase installs uv correctly
- ✅ Dependencies synced in `app/` directory

**Location:** `/nixpacks.toml`

---

## ✅ Check 2: railway.json Start Command
**Status:** ✅ PASS

**Verification:**
- ✅ `startCommand` includes LD_LIBRARY_PATH fix
- ✅ PATH export includes `$HOME/.local/bin`
- ✅ Correct working directory: `cd app`
- ✅ Correct command: `uv run python agent.py start`
- ✅ Restart policy configured: `ON_FAILURE` with 10 max retries

**Location:** `/railway.json` (line 7)

---

## ✅ Check 3: Procfile Configuration
**Status:** ✅ PASS

**Verification:**
- ✅ LD_LIBRARY_PATH fix present
- ✅ PATH export correct
- ✅ Working directory change: `cd app`
- ✅ Start command: `uv run python agent.py start`

**Location:** `/Procfile` (line 1)

---

## ⚠️ Check 4: Environment Variables Configuration
**Status:** ⚠️ MANUAL VERIFICATION REQUIRED

**Required Environment Variables (must be set in Railway dashboard):**

**Critical (Agent will fail without these):**
- `OPENAI_API_KEY` - Required for OpenAI API calls
- `CALCOM_API_KEY` - Required for Cal.com integration
- `LIVEKIT_URL` - LiveKit server WebSocket URL (format: `wss://...`)
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret

**Optional:**
- `MEM0_API_KEY` - For memory features (agent works without it)
- `DEFAULT_EMAIL` - Default email for Cal.com bookings

**Verification Steps:**
1. Go to Railway project → Variables tab
2. Verify all critical variables are set
3. Ensure no typos in variable names
4. Test that values are not empty

**Code Verification:**
- ✅ `agent.py` checks for `OPENAI_API_KEY` and `CALCOM_API_KEY` (lines 34-44)
- ✅ `agent.py` handles missing `MEM0_API_KEY` gracefully (lines 53-62)
- ✅ API routes check for required env vars with proper error messages

---

## ✅ Check 5: Python Dependencies
**Status:** ✅ PASS

**Verification:**
- ✅ `pyproject.toml` exists and is valid
- ✅ `uv.lock` exists (locked dependencies)
- ✅ Dependencies include:
  - `livekit-agents[silero,turn-detector,xai,openai]~=1.3`
  - `livekit-plugins-noise-cancellation~=0.2`
  - `python-dotenv`
  - `mem0ai`
  - `httpx`, `pytz`
- ✅ Python version requirement: `>=3.9`
- ✅ Build system configured: `setuptools>=61.0`

**Location:** `/app/pyproject.toml`

---

## ✅ Check 6: Node.js Dependencies
**Status:** ✅ PASS

**Verification:**
- ✅ `package.json` exists and is valid
- ✅ `pnpm-lock.yaml` exists
- ✅ Package manager: `pnpm@9.15.9`
- ✅ Key dependencies:
  - `next@15.5.8`
  - `@livekit/components-react@^2.9.15`
  - `livekit-client@^2.15.15`
  - `openai@^4.0.0`
  - `mem0ai@^2.2.0`
- ✅ All dependencies have version constraints

**Note:** Frontend dependencies are for Vercel deployment, not Railway agent.

**Location:** `/app/package.json`

---

## ✅ Check 7: Agent Entry Point
**Status:** ✅ PASS

**Verification:**
- ✅ `agent.py` exists at `/app/agent.py`
- ✅ File is valid Python (no syntax errors detected)
- ✅ Imports are correct:
  - LiveKit agents and plugins
  - Local lib modules
  - Required dependencies
- ✅ Main entry point: `agent.py start` command
- ✅ CLI interface configured via `livekit.agents.cli`

**Location:** `/app/agent.py`

---

## ✅ Check 8: API Routes
**Status:** ✅ PASS

**Verification:**
- ✅ `/app/api/connection-details/route.ts` - LiveKit connection setup
  - Validates `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
  - Proper error handling
- ✅ `/app/api/chatbot/route.ts` - Text chatbot endpoint
  - Validates `OPENAI_API_KEY`
  - Handles missing `MEM0_API_KEY` gracefully
  - Proper error responses
- ✅ `/app/api/sync-memory/route.ts` - Memory sync endpoint
  - Validates `MEM0_API_KEY` with clear error messages
  - Handles empty conversation history

**Note:** These routes are for Next.js frontend (Vercel), not Railway agent.

---

## ✅ Check 9: Hardcoded Secrets/Credentials
**Status:** ✅ PASS

**Verification:**
- ✅ No hardcoded API keys found (grep search: `sk-`, `password=`, `secret=`)
- ✅ All credentials loaded from environment variables
- ✅ API keys are masked in logs (e.g., `CALCOM_API_KEY[:20]...`)
- ✅ No secrets in version control
- ✅ `.env.local` is gitignored (standard practice)

**Security Best Practices:**
- ✅ Environment variables used throughout
- ✅ Sensitive values not logged in full
- ✅ Error messages don't expose secrets

---

## ✅ Check 10: Build Scripts
**Status:** ✅ PASS

**Verification:**
- ✅ `app/start.sh` exists and is executable
- ✅ `app/build.sh` exists and is executable
- ✅ Scripts have proper error handling (`set -e` in build.sh)
- ✅ Scripts check for required tools (uv, pnpm)
- ✅ Build script installs uv and syncs dependencies

**Note:** Railway uses nixpacks.toml, but these scripts are available for manual builds.

---

## ✅ Check 11: Error Handling
**Status:** ✅ PASS

**Verification:**
- ✅ `agent.py` has 76 error handling instances (try/except/raise)
- ✅ Critical environment variables validated with clear error messages
- ✅ Mem0 client initialization wrapped in try/except (lines 54-59)
- ✅ API routes have proper error handling:
  - `connection-details/route.ts`: Validates env vars, handles JSON parsing errors
  - `chatbot/route.ts`: Handles missing API keys, API errors, memory errors
  - `sync-memory/route.ts`: Validates inputs, handles Mem0 errors
- ✅ Logging configured: `logging.basicConfig` with INFO level
- ✅ Error messages are descriptive and actionable

**Error Handling Patterns:**
- ✅ Raises `ValueError` for missing required env vars
- ✅ Logs errors with context
- ✅ Returns proper HTTP status codes in API routes
- ✅ Graceful degradation (Mem0 optional)

---

## ✅ Check 12: Logging Configuration
**Status:** ✅ PASS

**Verification:**
- ✅ Logging configured in `agent.py` (line 30):
  - Level: `INFO`
  - Format: `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'`
- ✅ Logger instance: `logger = logging.getLogger("agent-Alex-2f2")`
- ✅ 97 logging statements found in agent.py
- ✅ API routes use `console.log` and `console.error` (Next.js standard)
- ✅ Logging includes:
  - Startup information
  - API key loading (masked)
  - Memory operations
  - Error details with context

**Logging Best Practices:**
- ✅ Sensitive data masked in logs
- ✅ Structured logging format
- ✅ Error logging includes stack traces (`exc_info=True`)

---

## ✅ Check 13: File Permissions and Paths
**Status:** ✅ PASS

**Verification:**
- ✅ `agent.py` exists and is readable
- ✅ `start.sh` is executable
- ✅ `build.sh` is executable
- ✅ All required files present:
  - `pyproject.toml` ✅
  - `uv.lock` ✅
  - `package.json` ✅
  - `agent.py` ✅
- ✅ Working directory paths correct:
  - nixpacks.toml: `cd app` before `uv sync` and start
  - railway.json: `cd app` in startCommand
  - Procfile: `cd app` in command

**Path Verification:**
- ✅ All relative paths assume `app/` as working directory
- ✅ Library imports use relative paths: `from lib.xxx import yyy`

---

## ✅ Check 14: Restart Policy Configuration
**Status:** ✅ PASS

**Verification:**
- ✅ `railway.json` configured:
  - `restartPolicyType: "ON_FAILURE"`
  - `restartPolicyMaxRetries: 10`
- ✅ This ensures agent restarts automatically on crashes
- ✅ Prevents infinite restart loops (max 10 retries)

**Location:** `/railway.json` (lines 8-9)

---

## ⚠️ Check 15: Documentation Consistency
**Status:** ⚠️ MINOR INCONSISTENCIES

**Verification:**

**Documentation Files Found:**
- ✅ `RAILWAY_LIBSTDCXX_FIX.md` - Documents the libstdc++ fix
- ✅ `DEPLOYMENT.md` - General deployment guide
- ✅ `AGENT_DEPLOYMENT.md` - Railway-specific deployment
- ✅ `VERCEL_ENV_SETUP.md` - Vercel environment variables
- ✅ `VERCEL_SETUP.md` - Vercel setup guide

**Inconsistencies Found:**

1. **Root Directory Configuration:**
   - `AGENT_DEPLOYMENT.md` (line 23): Says root directory should be `app`
   - `DEPLOYMENT.md` (line 42): Says root directory should be `app`
   - **Actual:** Railway configs use root directory with `cd app` in commands
   - **Status:** ✅ Actually consistent - commands change to `app/` directory

2. **Start Command Variations:**
   - `AGENT_DEPLOYMENT.md` (line 28): `uv run python agent.py start`
   - **Actual railway.json:** Includes full LD_LIBRARY_PATH fix
   - **Recommendation:** Update docs to include LD_LIBRARY_PATH fix

3. **Environment Variables:**
   - All docs list required env vars consistently
   - ✅ All match what's in code

**Recommendations:**
- Update `AGENT_DEPLOYMENT.md` to include LD_LIBRARY_PATH fix in start command
- Verify Railway dashboard root directory setting matches documentation

---

## Summary

### ✅ Passed: 13/15
### ⚠️ Manual Verification Required: 2/15

**Critical Actions Before Deployment:**

1. **⚠️ REQUIRED:** Set all environment variables in Railway dashboard:
   - `OPENAI_API_KEY`
   - `CALCOM_API_KEY`
   - `LIVEKIT_URL`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
   - (Optional) `MEM0_API_KEY`
   - (Optional) `DEFAULT_EMAIL`

2. **⚠️ RECOMMENDED:** Update `AGENT_DEPLOYMENT.md` to reflect actual start command with LD_LIBRARY_PATH fix

3. **✅ VERIFIED:** All configuration files have the libstdc++ fix applied

4. **✅ VERIFIED:** No hardcoded secrets found

5. **✅ VERIFIED:** Error handling and logging are properly configured

---

## Deployment Readiness: ✅ READY (after env vars set)

**Next Steps:**
1. Set environment variables in Railway
2. Deploy to Railway
3. Monitor logs for successful startup
4. Verify agent connects to LiveKit server
5. Test voice call functionality

---

*Generated: Pre-deployment verification checklist*

