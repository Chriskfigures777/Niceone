import MemoryClient from 'mem0ai';

// Get API key from environment variable
// This is server-side only for security (API routes, server components)
// The API key should be in .env.local as MEM0_API_KEY
const MEM0_API_KEY = process.env.MEM0_API_KEY || '';

// Initialize Mem0 client
let mem0Client: MemoryClient | null = null;

/**
 * Get or create the Mem0 client instance
 * @returns Mem0 client instance or null if API key is not set
 */
export function getMem0Client(): MemoryClient | null {
  if (!MEM0_API_KEY) {
    console.warn('Mem0 API key is not set. Memory features will be disabled.');
    return null;
  }

  if (!mem0Client) {
    try {
      mem0Client = new MemoryClient({ apiKey: MEM0_API_KEY });
    } catch (error) {
      console.error('Failed to initialize Mem0 client:', error);
      return null;
    }
  }

  return mem0Client;
}

/**
 * Store conversation messages to Mem0
 * @param messages - Array of messages with role and content
 * @param userId - User identifier (e.g., email or user ID)
 */
export async function storeMessages(
  messages: Array<{ role: string; content: string }>,
  userId: string
): Promise<void> {
  const client = getMem0Client();
  if (!client) {
    return;
  }

  try {
    await client.add(messages, { user_id: userId });
    console.log(`Stored ${messages.length} messages to Mem0 for user ${userId}`);
  } catch (error) {
    console.error('Error storing messages to Mem0:', error);
  }
}

/**
 * Search for relevant memories with retry logic for indexing delays
 * @param query - Search query string
 * @param userId - User identifier to filter memories
 * @param limit - Maximum number of memories to retrieve
 * @param maxRetries - Number of retry attempts (with exponential backoff)
 * @returns Array of relevant memories
 */
export async function searchMemories(
  query: string,
  userId: string,
  limit: number = 20,
  maxRetries: number = 2
): Promise<any[]> {
  const client = getMem0Client();
  if (!client) {
    return [];
  }

  // Use direct user_id filter (not OR clause) - matches Python implementation
  const filters = {
    user_id: userId,
  };

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      // Use a general query if empty (can't search with empty query)
      const searchQuery = query.trim() || 'user information and conversation history';
      
      const results = await client.search(searchQuery, {
        api_version: 'v2',
        filters: filters,
        limit: limit,
      });

      // Handle different response formats
      let memories = results;
      if (typeof results === 'object' && 'results' in results) {
        memories = (results as any).results;
      }

      if (Array.isArray(memories) && memories.length > 0) {
        // Double-check that all memories belong to this user
        const filteredMemories = memories.filter((mem: any) => {
          const memUserId = mem?.user_id || mem?.metadata?.user_id;
          return memUserId === userId || !memUserId; // Include if matches or no user_id (legacy)
        });

        if (filteredMemories.length > 0) {
          console.log(`Retrieved ${filteredMemories.length} memories for user ${userId} (attempt ${attempt + 1})`);
          return filteredMemories;
        }
      }

      // If no results and we have retries left, wait and retry
      if (attempt < maxRetries) {
        const waitTime = Math.pow(2, attempt) * 3000; // 3s, 6s exponential backoff
        console.log(`No memories found for user ${userId}, retrying in ${waitTime}ms (attempt ${attempt + 1}/${maxRetries + 1})`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue;
      }

      // No results after all retries
      if (attempt === 0) {
        console.log(`No memories found for user ${userId} (this is normal for new users)`);
      }
      return [];
    } catch (error) {
      console.error(`Error searching memories (attempt ${attempt + 1}):`, error);
      // On error, retry if we have attempts left
      if (attempt < maxRetries) {
        const waitTime = Math.pow(2, attempt) * 2000; // 2s, 4s for errors
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue;
      }
      return [];
    }
  }

  return [];
}

/**
 * Get all memories for a user
 * @param userId - User identifier
 * @param limit - Maximum number of memories to retrieve
 * @returns Array of all memories for the user
 */
export async function getAllMemories(userId: string, limit: number = 20): Promise<any[]> {
  return searchMemories('', userId, limit);
}

