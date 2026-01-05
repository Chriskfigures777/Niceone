# Railway libstdc++.so.6 Fix

## Problem
Railway agent crashes on startup with:
```
OSError: libstdc++.so.6: cannot open shared object file: No such file or directory
```

## Root Cause
LiveKit's Python SDK requires the C++ standard library (`libstdc++.so.6`), but the library path is not correctly configured in the Nix environment.

## Solution
The fix uses `stdenv` (which includes gcc and all standard libraries) and dynamically finds the library path at runtime.

### Configuration Files

**nixpacks.toml:**
- Added `stdenv` to nixPkgs (includes gcc and standard libraries)
- Start command uses `find` to locate `libstdc++.so.6` dynamically

**railway.json & Procfile:**
- Start commands use `find` to locate the library at runtime

## AI Prompt for Future Fixes

If this error occurs again, use this prompt:

```
The Railway agent is crashing with "libstdc++.so.6: cannot open shared object file". 
This is a LiveKit Python SDK dependency issue. Fix by:
1. Ensure nixpacks.toml includes "stdenv" in nixPkgs
2. Use dynamic library path finding in start commands: 
   export LD_LIBRARY_PATH="$(find /nix/store -name libstdc++.so.6 2>/dev/null | head -1 | xargs dirname):$LD_LIBRARY_PATH"
3. Apply to nixpacks.toml [start] cmd, railway.json startCommand, and Procfile
4. Verify the library exists in the Nix store during build phase
```

## Alternative Solutions (if above doesn't work)

1. **Use Nix shell environment:**
   - Wrap start command in `nix-shell` to get proper environment

2. **Install system packages:**
   - Use apt-get to install libstdc++6 (if using Ubuntu base)

3. **Use Dockerfile:**
   - Switch from Nixpacks to custom Dockerfile with explicit library installation

