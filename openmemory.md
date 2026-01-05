# OpenMemory Guide - Dawn Project

## Overview

This project is a LiveKit-based voice AI agent application with integrated memory management using both Mem0 and OpenMemory systems.

**Project ID:** `Chrisfig97/Dawn`

## Architecture

### Memory Systems
- **Mem0**: Primary memory system for conversation storage and retrieval
- **OpenMemory**: Secondary memory system via MCP server for persistent project memory
- **Integration**: Unified `MemoryManager` class supports both systems

### Components

#### Memory Management
- `lib/memory_manager.py`: Unified memory manager (Mem0 + OpenMemory)
- `lib/openmemory_manager.py`: OpenMemory-specific client for Python
- `lib/mem0-client.ts`: Mem0 client for TypeScript/Node.js
- `lib/openmemory-client.ts`: OpenMemory client for TypeScript/Node.js

#### Agent
- `app/agent.py`: Main LiveKit agent with memory integration
- Uses `MemoryManager` for conversation storage and retrieval

#### API Routes
- `app/api/chatbot/route.ts`: Chatbot endpoint with memory support
- `app/api/sync-memory/route.ts`: Memory synchronization endpoint

## User Defined Namespaces

- `conversations`: Stores conversation history and chat transcripts
- `components`: Component documentation and patterns
- `implementations`: Implementation details and code patterns
- `debug`: Debug information and fixes

## Memory Types

- **component**: Component documentation and architecture
- **implementation**: Implementation details and code patterns
- **user_preference**: User preferences and settings
- **project_info**: General project information
- **debug**: Debug information and bug fixes

## Recent Fixes (Memory App Issues)

### Fixed Issues
1. **Filter Format**: Fixed incorrect OR clause in mem0-client.ts - now uses direct user_id filter
2. **Retry Logic**: Added exponential backoff retry logic (3s, 6s) for memory retrieval
3. **SDK Usage**: Updated chatbot route to use SDK instead of direct API calls
4. **OpenMemory Integration**: Added OpenMemory support alongside Mem0

### Implementation Details
- Memory retrieval now tries OpenMemory first, then falls back to Mem0
- Both systems support retry logic for indexing delays
- Unified interface through MemoryManager class

## Configuration

### Environment Variables
- `MEM0_API_KEY`: Mem0 API key
- `OPENMEMORY_API_TOKEN`: OpenMemory API token (default: om-5rqj2ru86nmfvydd972qlwbgky5ea1zh)
- `OPENMEMORY_API_URL`: OpenMemory API URL (default: https://api.openmemory.dev)
- `OPENMEMORY_PROJECT_ID`: Project ID (default: Chrisfig97/Dawn)

### MCP Configuration
OpenMemory MCP server is configured in `~/.cursor/mcp.json`:
```json
{
  "openmemory": {
    "headers": {
      "Authorization": "Token om-5rqj2ru86nmfvydd972qlwbgky5ea1zh"
    },
    "url": "https://api.openmemory.dev/mcp-stream?client=cursor"
  }
}
```

## Patterns

### Memory Storage
- Conversations are stored to both Mem0 and OpenMemory
- Messages are formatted with role and content
- User ID is used for filtering and organization

### Memory Retrieval
- OpenMemory is tried first, then Mem0 as fallback
- Retry logic handles indexing delays (5-10+ seconds)
- Exponential backoff: 3s, 6s delays

### Error Handling
- Graceful fallback between memory systems
- Comprehensive logging for debugging
- Retry logic prevents transient failures

## Notes

- Memories take 5-10+ seconds to be indexed after storage
- Retry logic automatically handles indexing delays
- Both memory systems can be used simultaneously for redundancy




