#!/usr/bin/env python3
"""Test script for Mem0 Python implementation"""
import os
import sys
import asyncio
from dotenv import load_dotenv
from mem0 import MemoryClient

# Load environment variables
load_dotenv(".env.local")
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")

if not MEM0_API_KEY:
    print("❌ MEM0_API_KEY not found in environment")
    sys.exit(1)

print(f"✓ Found MEM0_API_KEY: {MEM0_API_KEY[:10]}...")

# Test messages (small sample to conserve API calls)
test_messages = [
    {"role": "user", "content": "Hello, my name is Test User"},
    {"role": "assistant", "content": "Hi Test User! How can I help you today?"},
    {"role": "user", "content": "I want to book an appointment"},
    {"role": "assistant", "content": "Of course! What date and time would work for you?"},
]

async def test_python_mem0():
    """Test Python Mem0 SDK"""
    print("\n=== Testing Python Mem0 SDK ===\n")
    
    try:
        # Initialize client
        print("1. Initializing Mem0 client...")
        client = MemoryClient(api_key=MEM0_API_KEY)
        print("   ✓ Client initialized")
        
        # Test storing messages
        print(f"\n2. Storing {len(test_messages)} test messages...")
        result = client.add(test_messages, user_id="test_user_python")
        print(f"   ✓ Messages stored")
        print(f"   Response: {result}")
        
        # Test retrieving memories
        print("\n3. Retrieving memories...")
        memories = client.search("user information and conversation history", version="v2", filters={"OR": [{"user_id": "test_user_python"}]}, limit=10)
        print(f"   ✓ Retrieved memories")
        
        # Handle different response formats
        if isinstance(memories, dict) and "results" in memories:
            memories = memories["results"]
        
        if memories and isinstance(memories, list):
            print(f"   Found {len(memories)} memories:")
            for i, mem in enumerate(memories[:3], 1):  # Show first 3
                mem_text = mem.get("memory", str(mem))
                print(f"   {i}. {mem_text[:100]}...")
        else:
            print("   ⚠️  No memories found (might need to wait a moment for indexing)")
        
        print("\n✅ Python Mem0 test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Python Mem0 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_python_mem0())
    sys.exit(0 if success else 1)





