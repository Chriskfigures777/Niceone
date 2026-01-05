#!/bin/bash
# Build script for agent deployment

set -e

echo "🔧 Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

echo "📦 Syncing Python dependencies..."
uv sync --locked

echo "✅ Build complete!"

