#!/bin/bash

# Start script for both agent and Next.js server
# This script starts both services concurrently

echo "🚀 Starting Agent and Next.js Server..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo "❌ Error: pnpm is not installed. Please install it first:"
    echo "   npm install -g pnpm"
    exit 1
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "⚠️  Warning: .env.local file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env.local
        echo "✅ Created .env.local. Please update it with your API keys."
    else
        echo "❌ Error: .env.example not found. Please create .env.local manually."
        exit 1
    fi
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    pnpm install
fi

# Sync Python dependencies if needed
echo "📦 Syncing Python dependencies..."
uv sync

# Start both services
echo "🎯 Starting services..."
pnpm start:all

