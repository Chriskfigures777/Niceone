/**
 * Chatbot client for text-only conversations after LiveKit call ends
 * Uses Mem0 for memory persistence
 * Optimized for better context understanding and faster responses
 */

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface ChatbotResponse {
  response: string;
  memories?: string[];
}

export class ChatbotClient {
  private conversationHistory: ChatMessage[] = [];
  private userId: string;
  private email?: string;
  private apiUrl: string;
  private maxHistoryLength: number = 50; // Limit to last 50 messages for performance

  constructor(userId: string = 'default_user', email?: string) {
    this.userId = userId;
    this.email = email;
    this.apiUrl = '/api/chatbot';
  }

  /**
   * Send a message to the chatbot and get a response
   * Optimized with history trimming for better performance
   */
  async sendMessage(message: string): Promise<ChatbotResponse> {
    try {
      // Trim conversation history to prevent payload from getting too large
      // Keep only the most recent messages for context
      const trimmedHistory = this.conversationHistory.slice(-this.maxHistoryLength);

      const response = await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          conversationHistory: trimmedHistory,
          userId: this.userId,
          email: this.email,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chatbot API error: ${response.statusText}`);
      }

      const data = await response.json();

      // Update conversation history
      this.conversationHistory.push(
        { role: 'user', content: message },
        { role: 'assistant', content: data.response }
      );

      // Trim history if it gets too long (keep last maxHistoryLength items)
      if (this.conversationHistory.length > this.maxHistoryLength) {
        this.conversationHistory = this.conversationHistory.slice(-this.maxHistoryLength);
      }

      return data;
    } catch (error) {
      console.error('Chatbot client error:', error);
      throw error;
    }
  }

  /**
   * Get the current conversation history
   */
  getConversationHistory(): ChatMessage[] {
    return [...this.conversationHistory];
  }

  /**
   * Set conversation history (useful when loading from Mem0)
   */
  setConversationHistory(history: ChatMessage[]): void {
    this.conversationHistory = [...history];
  }

  /**
   * Clear conversation history
   */
  clearHistory(): void {
    this.conversationHistory = [];
  }

  /**
   * Add a message to history (for loading previous conversations)
   */
  addToHistory(message: ChatMessage): void {
    this.conversationHistory.push(message);
  }

  /**
   * Sync conversation history to Mem0 before starting a call
   * This ensures the agent has access to all text mode conversation history
   */
  async syncToMem0(): Promise<{ success: boolean; message?: string; error?: string }> {
    if (this.conversationHistory.length === 0) {
      return { success: true, message: 'No conversation history to sync' };
    }

    try {
      const response = await fetch('/api/sync-memory', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversationHistory: this.conversationHistory,
          userId: this.userId,
          email: this.email,
        }),
      });

      // Check if response is ok before trying to parse JSON
      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        let errorDetails = '';
        let errorData: any = null;

        try {
          // Try to get response as text first
          const responseText = await response.text();

          if (responseText && responseText.trim()) {
            try {
              // Try to parse as JSON
              errorData = JSON.parse(responseText);
              const extractedError = errorData.error || errorData.message || '';
              const extractedDetails =
                errorData.details || errorData.mem0Error?.message || errorData.mem0Error || '';

              if (extractedError) {
                errorMessage = extractedError;
              }

              if (extractedDetails) {
                errorDetails =
                  typeof extractedDetails === 'string'
                    ? extractedDetails
                    : JSON.stringify(extractedDetails);
                // Combine error message and details for better debugging
                if (errorDetails !== errorMessage) {
                  errorMessage = `${errorMessage}. Details: ${errorDetails}`;
                }
              }
            } catch {
              // If not JSON, use as plain text
              errorMessage = `${errorMessage}. Response: ${responseText.substring(0, 200)}`;
              errorDetails = responseText.substring(0, 200);
            }
          } else {
            // Empty response body
            errorMessage = `${errorMessage}. Empty response body`;
          }
        } catch (e) {
          // If reading response fails, use status info
          const readError = e instanceof Error ? e.message : String(e) || 'Unknown error';
          errorMessage = `${errorMessage}. Failed to read response: ${readError}`;
        }

        // Ensure we always have a meaningful error message
        if (!errorMessage || errorMessage.trim() === '') {
          errorMessage = `HTTP ${response.status}: ${response.statusText || 'Unknown error'}`;
        }

        const errorInfo = {
          status: response.status,
          statusText: response.statusText || 'Unknown',
          error: errorMessage,
          ...(errorData && Object.keys(errorData).length > 0 && { errorData }),
          ...(errorDetails && errorDetails.trim() && { details: errorDetails }),
        };

        console.error('Failed to sync to Mem0:', JSON.stringify(errorInfo, null, 2));
        return { success: false, error: errorMessage };
      }

      // Parse JSON response
      let data: any = {};
      try {
        const text = await response.text();
        if (text && text.trim()) {
          try {
            data = JSON.parse(text);
          } catch (parseError) {
            console.error(
              'Failed to parse sync response as JSON:',
              parseError,
              'Response text:',
              text
            );
            return {
              success: false,
              error: `Invalid JSON response from server: ${text.substring(0, 100)}`,
            };
          }
        } else {
          console.warn('Empty response from sync-memory API');
          return { success: false, error: 'Empty response from server' };
        }
      } catch (parseError) {
        console.error('Failed to read sync response:', parseError);
        return { success: false, error: 'Failed to read response from server' };
      }

      // Check if response indicates success
      if (data.success === true) {
        console.log('✓ Conversation history synced to Mem0:', data);
        return {
          success: true,
          message: data.message || 'Conversation history synced successfully',
        };
      } else {
        // Response was ok but success is false or undefined
        const errorMsg = data.error || data.details || data.message || 'Failed to sync to Mem0';
        console.error('Failed to sync to Mem0 (response ok but success=false):', {
          data,
          error: errorMsg,
        });
        return { success: false, error: errorMsg };
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : typeof error === 'string'
            ? error
            : JSON.stringify(error) || 'Unknown error occurred';

      console.error('Error syncing to Mem0:', {
        error: errorMessage,
        errorType: error instanceof Error ? error.constructor.name : typeof error,
        ...(error instanceof Error && error.stack && { stack: error.stack }),
      });

      return {
        success: false,
        error: errorMessage,
      };
    }
  }
}
