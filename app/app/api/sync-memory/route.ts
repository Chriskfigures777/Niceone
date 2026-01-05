import { NextRequest, NextResponse } from 'next/server';
import { storeMessages } from '@/lib/mem0-client';

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface SyncMemoryRequest {
  conversationHistory: ChatMessage[];
  userId?: string;
  email?: string;
}

/**
 * API endpoint to sync conversation history to Mem0 before starting a call
 * This ensures the agent has access to all text mode conversation history
 * Uses the Mem0 SDK instead of direct API calls (SDK handles authentication correctly)
 */
export async function POST(request: NextRequest) {
  try {
    const body: SyncMemoryRequest = await request.json();
    const { conversationHistory = [], userId = 'default_user', email } = body;

    if (!conversationHistory || conversationHistory.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No conversation history to sync',
      });
    }

    // Check if MEM0_API_KEY is configured
    if (!process.env.MEM0_API_KEY) {
      console.warn('Mem0 API key not set - skipping sync');
      return NextResponse.json(
        {
          success: false,
          error: 'Mem0 API key not configured',
          details: 'Please set MEM0_API_KEY in your environment variables',
        },
        { status: 400 }
      );
    }

    // Store conversation to Mem0 using SDK (works correctly, unlike direct API calls)
    // Filter out system messages as Mem0 only accepts 'user' | 'assistant'
    try {
      const filteredMessages = conversationHistory.filter(
        (msg): msg is { role: 'user' | 'assistant'; content: string } =>
          msg.role === 'user' || msg.role === 'assistant'
      );
      await storeMessages(filteredMessages, userId);

      console.log('✓ Conversation history synced to Mem0:', {
        userId,
        messageCount: conversationHistory.length,
      });

      // Note: Memories take 5-10+ seconds to be indexed
      // The memory retrieval functions have retry logic to handle this delay
      // We don't wait here to avoid blocking the response, but retrieval will retry automatically

      return NextResponse.json({
        success: true,
        message: 'Conversation history synced to Mem0',
        syncedMessages: conversationHistory.length,
        note: 'Memories may take 5-10 seconds to be indexed and available for retrieval',
      });
    } catch (error) {
      console.error('Error syncing to Mem0:', error);
      return NextResponse.json(
        {
          success: false,
          error: 'Failed to sync to Mem0',
          details: error instanceof Error ? error.message : 'Unknown error',
        },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Sync memory API error:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Failed to process sync request',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
