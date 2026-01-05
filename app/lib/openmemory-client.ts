/**
 * OpenMemory client for storing and retrieving memories
 * Uses the OpenMemory MCP server API
 */

// Get API token from environment variable or use the configured MCP token
// The token from mcp.json: om-5rqj2ru86nmfvydd972qlwbgky5ea1zh
const OPENMEMORY_API_TOKEN =
  process.env.OPENMEMORY_API_TOKEN || 'om-5rqj2ru86nmfvydd972qlwbgky5ea1zh';
const OPENMEMORY_API_URL = process.env.OPENMEMORY_API_URL || 'https://api.openmemory.dev';

interface Memory {
  title: string;
  content: string;
  metadata?: {
    user_id?: string;
    project_id?: string;
    memory_types?: string[];
    namespace?: string;
    [key: string]: any;
  };
}

interface SearchOptions {
  project_id?: string;
  user_preference?: boolean;
  memory_types?: string[];
  namespaces?: string[];
  limit?: number;
}

/**
 * Add a memory to OpenMemory
 * @param title - Memory title
 * @param content - Memory content
 * @param metadata - Optional metadata including user_id, project_id, etc.
 */
export async function addMemory(
  title: string,
  content: string,
  metadata?: {
    user_id?: string;
    project_id?: string;
    memory_types?: string[];
    namespace?: string;
    [key: string]: any;
  }
): Promise<void> {
  if (!OPENMEMORY_API_TOKEN) {
    console.warn('OpenMemory API token is not set. Memory features will be disabled.');
    return;
  }

  try {
    // Use MCP protocol or direct API call
    // Since we're using the MCP stream endpoint, we might need to use MCP protocol
    // For now, try direct API call to the base URL
    const response = await fetch(`${OPENMEMORY_API_URL}/memories`, {
      method: 'POST',
      headers: {
        Authorization: `Token ${OPENMEMORY_API_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title,
        content,
        metadata: metadata || {},
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`OpenMemory API error (${response.status}):`, errorText);
      return;
    }

    console.log(`✓ Stored memory to OpenMemory: ${title}`);
  } catch (error) {
    console.error('Error storing memory to OpenMemory:', error);
  }
}

/**
 * Search for memories in OpenMemory
 * @param query - Search query
 * @param options - Search options including project_id, user_preference, etc.
 * @returns Array of matching memories
 */
export async function searchMemories(query: string, options: SearchOptions = {}): Promise<any[]> {
  if (!OPENMEMORY_API_TOKEN) {
    console.warn('OpenMemory API token is not set. Memory features will be disabled.');
    return [];
  }

  try {
    const { project_id, user_preference, memory_types, namespaces, limit = 20 } = options;

    // Build search parameters
    const params = new URLSearchParams({
      query,
      limit: limit.toString(),
    });

    if (project_id) {
      params.append('project_id', project_id);
    }
    if (user_preference !== undefined) {
      params.append('user_preference', user_preference.toString());
    }
    if (memory_types && memory_types.length > 0) {
      params.append('memory_types', memory_types.join(','));
    }
    if (namespaces && namespaces.length > 0) {
      params.append('namespaces', namespaces.join(','));
    }

    const response = await fetch(`${OPENMEMORY_API_URL}/memories/search?${params.toString()}`, {
      method: 'GET',
      headers: {
        Authorization: `Token ${OPENMEMORY_API_TOKEN}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`OpenMemory search API error (${response.status}):`, errorText);
      return [];
    }

    const data = await response.json();
    return Array.isArray(data) ? data : data.results || [];
  } catch (error) {
    console.error('Error searching memories in OpenMemory:', error);
    return [];
  }
}

/**
 * Store conversation messages to OpenMemory
 * Converts messages to memory format and stores them
 * @param messages - Array of messages with role and content
 * @param userId - User identifier
 * @param projectId - Project identifier (optional)
 */
export async function storeMessages(
  messages: Array<{ role: string; content: string }>,
  userId: string,
  projectId: string = 'Chrisfig97/Dawn'
): Promise<void> {
  if (!OPENMEMORY_API_TOKEN || messages.length === 0) {
    return;
  }

  try {
    // Convert messages to a conversation memory
    const conversationText = messages.map((msg) => `${msg.role}: ${msg.content}`).join('\n');

    const title = `Conversation - ${new Date().toISOString()}`;
    const content = conversationText;

    await addMemory(title, content, {
      user_id: userId,
      project_id: projectId,
      memory_types: ['implementation'],
      namespace: 'conversations',
    });

    console.log(`✓ Stored ${messages.length} messages to OpenMemory for user ${userId}`);
  } catch (error) {
    console.error('Error storing messages to OpenMemory:', error);
  }
}

/**
 * Get memories for a user from OpenMemory
 * @param userId - User identifier
 * @param projectId - Project identifier
 * @param query - Optional search query
 * @param limit - Maximum number of memories to retrieve
 * @returns Array of memories
 */
export async function getUserMemories(
  userId: string,
  projectId: string = 'Chrisfig97/Dawn',
  query: string = 'user information and conversation history',
  limit: number = 20
): Promise<any[]> {
  return searchMemories(query, {
    project_id: projectId,
    limit,
  });
}
