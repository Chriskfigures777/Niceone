#!/bin/bash
# Test script for Mem0 JavaScript/API implementation using curl

# Check if MEM0_API_KEY is set
if [ -z "$MEM0_API_KEY" ]; then
    echo "❌ MEM0_API_KEY not found in environment"
    echo "Please set it: export MEM0_API_KEY='your-key'"
    exit 1
fi

echo "✓ Found MEM0_API_KEY: ${MEM0_API_KEY:0:10}..."

# Test messages (small sample to conserve API calls)
TEST_MESSAGES='[
  {"role": "user", "content": "Hello, my name is Test User"},
  {"role": "assistant", "content": "Hi Test User! How can I help you today?"},
  {"role": "user", "content": "I want to book an appointment"},
  {"role": "assistant", "content": "Of course! What date and time would work for you?"}
]'

echo ""
echo "=== Testing Mem0 API Direct (JavaScript/curl) ==="
echo ""

# Test 1: Store messages
echo "1. Storing test messages to Mem0 API..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.mem0.ai/v1/memories/" \
  -H "Authorization: Bearer $MEM0_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": $TEST_MESSAGES,
    \"user_id\": \"test_user_curl\"
  }")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "   HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo "   ✓ Messages stored successfully"
    echo "   Response: $BODY" | head -c 200
    echo ""
else
    echo "   ❌ Failed to store messages"
    echo "   Response: $BODY"
    exit 1
fi

# Test 2: Search memories
echo ""
echo "2. Searching for memories..."
SEARCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.mem0.ai/v1/memories/search/" \
  -H "Authorization: Bearer $MEM0_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"user information and conversation history\",
    \"user_id\": \"test_user_curl\",
    \"limit\": 10
  }")

SEARCH_HTTP_CODE=$(echo "$SEARCH_RESPONSE" | tail -n1)
SEARCH_BODY=$(echo "$SEARCH_RESPONSE" | sed '$d')

echo "   HTTP Status: $SEARCH_HTTP_CODE"
if [ "$SEARCH_HTTP_CODE" -eq 200 ]; then
    echo "   ✓ Memories retrieved successfully"
    echo "   Response preview: $SEARCH_BODY" | head -c 300
    echo ""
    
    # Try to extract memory count if possible
    MEMORY_COUNT=$(echo "$SEARCH_BODY" | grep -o '"results":\[' | wc -l || echo "0")
    if [ "$MEMORY_COUNT" -gt 0 ]; then
        echo "   Found memories in response"
    fi
else
    echo "   ⚠️  Search returned status $SEARCH_HTTP_CODE"
    echo "   Response: $SEARCH_BODY"
fi

echo ""
echo "✅ Mem0 API curl test completed!"
echo ""
echo "Note: If memories aren't found immediately, they may need a moment to be indexed."





