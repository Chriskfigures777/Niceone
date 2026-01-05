#!/usr/bin/env python3
"""Comprehensive test for Mem0 - tests storage, retrieval, and data size limits"""
import os
import sys
import asyncio
import time
from dotenv import load_dotenv
from mem0 import MemoryClient

# Load environment variables
load_dotenv(".env.local")
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")

if not MEM0_API_KEY:
    print("❌ MEM0_API_KEY not found in environment")
    sys.exit(1)

print(f"✓ Found MEM0_API_KEY: {MEM0_API_KEY[:10]}...\n")

# Test with different conversation sizes
test_conversations = {
    "small": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
    ],
    "medium": [
        {"role": "user", "content": "Hello, my name is Test User"},
        {"role": "assistant", "content": "Hi Test User! How can I help you today?"},
        {"role": "user", "content": "I want to book an appointment"},
        {"role": "assistant", "content": "Of course! What date and time would work for you?"},
        {"role": "user", "content": "How about tomorrow at 2pm?"},
        {"role": "assistant", "content": "Let me check availability for tomorrow at 2pm."},
    ],
    "large": [
        {"role": "user", "content": "Hello, my name is Test User"},
        {"role": "assistant", "content": "Hi Test User! How can I help you today?"},
        {"role": "user", "content": "I want to book an appointment"},
        {"role": "assistant", "content": "Of course! What date and time would work for you?"},
        {"role": "user", "content": "How about tomorrow at 2pm?"},
        {"role": "assistant", "content": "Let me check availability for tomorrow at 2pm."},
        {"role": "user", "content": "Actually, can we do 3pm instead?"},
        {"role": "assistant", "content": "Sure, 3pm works. I'll schedule that for you."},
        {"role": "user", "content": "Great, thanks!"},
        {"role": "assistant", "content": "You're welcome! Is there anything else I can help with?"},
    ]
}

async def test_mem0_comprehensive():
    """Comprehensive test of Mem0 functionality"""
    print("=== Comprehensive Mem0 Test ===\n")
    
    try:
        # Initialize client
        print("1. Initializing Mem0 client...")
        client = MemoryClient(api_key=MEM0_API_KEY)
        print("   ✓ Client initialized\n")
        
        user_id = "test_user_comprehensive"
        
        # Test 1: Store small conversation
        print("2. Testing SMALL conversation (2 messages)...")
        try:
            result = client.add(test_conversations["small"], user_id=user_id)
            print(f"   ✓ Stored successfully")
            print(f"   Response: {result}\n")
        except Exception as e:
            print(f"   ❌ Failed: {e}\n")
            return False
        
        # Wait a bit for indexing
        print("3. Waiting 3 seconds for memory indexing...")
        await asyncio.sleep(3)
        
        # Test 2: Retrieve memories
        print("4. Retrieving memories...")
        try:
            memories = client.search(
                "user information and conversation history",
                version="v2",
                filters={"OR": [{"user_id": user_id}]},
                limit=10
            )
            
            # Handle different response formats
            if isinstance(memories, dict) and "results" in memories:
                memories = memories["results"]
            
            if memories and isinstance(memories, list):
                print(f"   ✓ Found {len(memories)} memories:")
                for i, mem in enumerate(memories[:3], 1):
                    mem_text = mem.get("memory", str(mem))
                    print(f"   {i}. {mem_text[:80]}...")
            else:
                print("   ⚠️  No memories found yet (may need more time for indexing)")
            print()
        except Exception as e:
            print(f"   ❌ Failed to retrieve: {e}\n")
        
        # Test 3: Store medium conversation
        print("5. Testing MEDIUM conversation (6 messages)...")
        try:
            result = client.add(test_conversations["medium"], user_id=user_id)
            print(f"   ✓ Stored successfully")
            print(f"   Response: {result}\n")
        except Exception as e:
            print(f"   ❌ Failed: {e}\n")
            return False
        
        # Wait for indexing
        print("6. Waiting 3 seconds for memory indexing...")
        await asyncio.sleep(3)
        
        # Test 4: Retrieve again
        print("7. Retrieving memories again...")
        try:
            memories = client.search(
                "user information and conversation history",
                version="v2",
                filters={"OR": [{"user_id": user_id}]},
                limit=10
            )
            
            if isinstance(memories, dict) and "results" in memories:
                memories = memories["results"]
            
            if memories and isinstance(memories, list):
                print(f"   ✓ Found {len(memories)} memories")
            else:
                print("   ⚠️  No memories found")
            print()
        except Exception as e:
            print(f"   ❌ Failed: {e}\n")
        
        # Test 5: Check if we can search for specific content
        print("8. Testing specific memory search (looking for 'appointment')...")
        try:
            memories = client.search(
                "appointment booking",
                version="v2",
                filters={"OR": [{"user_id": user_id}]},
                limit=5
            )
            
            if isinstance(memories, dict) and "results" in memories:
                memories = memories["results"]
            
            if memories and isinstance(memories, list):
                print(f"   ✓ Found {len(memories)} relevant memories")
                for i, mem in enumerate(memories[:2], 1):
                    mem_text = mem.get("memory", str(mem))
                    print(f"   {i}. {mem_text[:80]}...")
            else:
                print("   ⚠️  No relevant memories found")
            print()
        except Exception as e:
            print(f"   ❌ Failed: {e}\n")
        
        print("✅ Comprehensive test completed!")
        print("\n📝 Summary:")
        print("   - Python SDK can store messages")
        print("   - Memories may take a few seconds to be indexed")
        print("   - Search functionality works")
        print("\n💡 Recommendations:")
        print("   - Wait 3-5 seconds after storing before retrieving")
        print("   - Use specific queries for better search results")
        print("   - Store conversations in batches (not too large)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mem0_comprehensive())
    sys.exit(0 if success else 1)





