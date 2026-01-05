import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';
import { searchMemories, storeMessages } from '@/lib/mem0-client';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface ChatRequest {
  message: string;
  conversationHistory?: ChatMessage[];
  userId?: string;
  email?: string;
}

// Simple in-memory cache for recent memories (per user)
// This reduces redundant Mem0 API calls for consecutive messages
const memoryCache = new Map<string, { memories: any[]; timestamp: number }>();
const CACHE_TTL = 60000; // 1 minute cache

/**
 * Chatbot API endpoint that uses Mem0 for memory
 * This is used when the LiveKit call ends - pure text conversation
 */
export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    const { message, conversationHistory = [], userId = 'default_user' } = body;

    if (!message || !message.trim()) {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    // OPTIMIZATION 1: Check cache first for recent memories
    const cacheKey = userId;
    const cached = memoryCache.get(cacheKey);
    const now = Date.now();
    let memories: any[] = [];

    if (cached && now - cached.timestamp < CACHE_TTL) {
      // Use cached memories (less than 1 minute old)
      memories = cached.memories;
      console.log(`Using cached memories for user ${userId} (${memories.length} items)`);
    } else if (process.env.MEM0_API_KEY) {
      // OPTIMIZATION 2: Fetch memories from Mem0 (no retry needed for most cases)
      try {
        // Use SDK search - reduced retries to 1 for faster response
        memories = await searchMemories(message, userId, 20, 1);

        // Update cache with fresh memories
        memoryCache.set(cacheKey, { memories, timestamp: now });

        // Clean up old cache entries (prevent memory leaks)
        if (memoryCache.size > 100) {
          const oldestKey = memoryCache.keys().next().value;
          if (oldestKey) memoryCache.delete(oldestKey);
        }
      } catch (error) {
        console.error('Error fetching Mem0 memories:', error);
      }
    }

    // OPTIMIZATION 3: Better memory filtering - only use relevant conversation content
    const validMemories = memories
      .map((m: any) => m.memory || m)
      .filter((mem: string) => {
        if (!mem || typeof mem !== 'string' || mem.trim().length < 10) return false;
        // Only include memories that look like actual conversation content
        const lowerMem = mem.toLowerCase();
        return [
          'user',
          'said',
          'asked',
          'mentioned',
          'discussed',
          'talked',
          'conversation',
          'told',
        ].some((keyword) => lowerMem.includes(keyword));
      })
      .slice(0, 10); // Limit to 10 most relevant memories to reduce token usage

    // Build conversation context with memories
    const systemPrompt = `You are a friendly, reliable AI assistant for Figures Solutions.

${validMemories.length > 0 ? `\nRelevant context from previous conversations:\n${validMemories.map((m: string) => `- ${m}`).join('\n')}\n` : ''}

You are currently in text-only chatbot mode. Continue the conversation naturally based on the context above and the conversation history.
Keep responses concise and helpful.`;

    // OPTIMIZATION 4: Include full conversation history for better context understanding
    // OpenAI maintains context across the entire conversation
    const messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[] = [
      { role: 'system', content: systemPrompt },
      ...(conversationHistory.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })) as OpenAI.Chat.Completions.ChatCompletionMessageParam[]),
      { role: 'user', content: message },
    ];

    // Call OpenAI API
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: messages,
      temperature: 0.7,
      max_tokens: 1500, // Reduced slightly for faster responses while still allowing detailed answers
    });

    const assistantMessage =
      completion.choices[0]?.message?.content || 'I apologize, I could not generate a response.';

    // OPTIMIZATION 5: Store to Mem0 asynchronously (don't wait for it)
    // This allows the response to be returned immediately while storage happens in background
    if (process.env.MEM0_API_KEY) {
      // Fire and forget - store the new exchange without blocking the response
      storeMessages(
        [
          { role: 'user', content: message },
          { role: 'assistant', content: assistantMessage },
        ],
        userId
      ).catch((error) => {
        console.error('Error storing exchange to Mem0 (async):', error);
      });

      // Invalidate cache so next request gets fresh memories
      memoryCache.delete(cacheKey);
    }

    return NextResponse.json({
      response: assistantMessage,
      memories: memories.length > 0 ? memories.map((m: any) => m.memory) : [],
    });
  } catch (error) {
    console.error('Chatbot API error:', error);
    return NextResponse.json(
      {
        error: 'Failed to process message',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
