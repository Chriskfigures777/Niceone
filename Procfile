web: export PATH="$HOME/.local/bin:$PATH" && export LD_LIBRARY_PATH="$(find /nix/store -name libstdc++.so.6 2>/dev/null | head -1 | xargs dirname):$LD_LIBRARY_PATH" && cd app && uv run python agent.py start


