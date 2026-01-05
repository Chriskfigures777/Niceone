#!/bin/bash
# Test the Next.js sync-memory API endpoint

# Load API key
if [ -f .env.local ]; then
    export MEM0_API_KEY=$(grep "^MEM0_API_KEY=" .env.local | cut -d'=' -f2- | tr -d '"' | tr -d "'")
fi

if [ -z "$MEM0_API_KEY" ]; then
    echo "❌ MEM0_API_KEY not found"
    exit 1
fi

echo "=== Testing Next.js sync-memory API endpoint ==="
echo ""

# Test messages (small sample)
TEST_PAYLOAD='{
  "conversationHistory": [
    {"role": "user", "content": "Hello, my name is Test User"},
    {"role": "assistant", "content": "Hi Test User! How can I help you today?"},
    {"role": "user", "content": "I want to book an appointment"},
    {"role": "assistant", "content": "Of course! What date and time would work for you?"}
  ],
  "userId": "test_user_api",
  "email": "test@example.com"
}'

echo "1. Testing /api/sync-memory endpoint..."
echo "   (Note: This requires the Next.js server to be running)"
echo ""

# Check if server is running on default port
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✓ Server detected on port 3000"
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:3000/api/sync-memory" \
      -H "Content-Type: application/json" \
      -d "$TEST_PAYLOAD")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    echo "   HTTP Status: $HTTP_CODE"
    if [ "$HTTP_CODE" -eq 200 ]; then
        echo "   ✓ API endpoint responded successfully"
        echo "   Response: $BODY" | head -c 300
        echo ""
    else
        echo "   ❌ API endpoint returned error"
        echo "   Response: $BODY"
    fi
else
    echo "   ⚠️  Next.js server not running on port 3000"
    echo "   Start it with: npm run dev"
    echo ""
    echo "   To test manually, run:"
    echo "   curl -X POST http://localhost:3000/api/sync-memory \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '$TEST_PAYLOAD'"
fi

echo ""
echo "✅ Test completed!"





