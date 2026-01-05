"""Unified memory management for conversation storage and retrieval
Supports both Mem0 and OpenMemory"""
import asyncio
import logging
from typing import Optional
from mem0 import MemoryClient
from livekit.agents.llm import ImageContent

logger = logging.getLogger("agent-Alex-2f2")

# Try to import OpenMemory manager
try:
    from lib.openmemory_manager import OpenMemoryManager
    OPENMEMORY_AVAILABLE = True
except ImportError:
    OPENMEMORY_AVAILABLE = False
    logger.warning("OpenMemory manager not available - only Mem0 will be used")


class MemoryManager:
    """Manages memory storage and retrieval using Mem0 and/or OpenMemory"""
    
    def __init__(self, mem0_client: Optional[MemoryClient], use_openmemory: bool = True):
        self.mem0_client = mem0_client
        self.openmemory_manager = None
        
        if use_openmemory and OPENMEMORY_AVAILABLE:
            try:
                self.openmemory_manager = OpenMemoryManager()
                logger.info("✓ OpenMemory manager initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenMemory manager: {e}")
                self.openmemory_manager = None
    
    async def retrieve_memories(self, user_id: str, query: Optional[str] = None, limit: int = 20, max_retries: int = 2) -> list:
        """Retrieve relevant memories for a user with retry logic for indexing delays.
        Tries OpenMemory first, then falls back to Mem0.
        
        Args:
            user_id: User identifier
            query: Optional search query
            limit: Maximum number of memories to retrieve
            max_retries: Number of retry attempts (with exponential backoff)
        """
        # Try OpenMemory first
        if self.openmemory_manager:
            try:
                openmemory_results = await self.openmemory_manager.retrieve_memories(
                    user_id=user_id,
                    query=query,
                    limit=limit,
                    max_retries=max_retries
                )
                if openmemory_results:
                    logger.info(f"Retrieved {len(openmemory_results)} memories from OpenMemory for user {user_id}")
                    # Convert OpenMemory format to expected format
                    formatted_results = []
                    for mem in openmemory_results:
                        formatted_results.append({
                            'memory': mem.get('content', str(mem)),
                            'user_id': user_id,
                            'metadata': mem.get('metadata', {})
                        })
                    return formatted_results
            except Exception as e:
                logger.warning(f"OpenMemory retrieval failed, falling back to Mem0: {e}")
        
        # Fall back to Mem0
        if not self.mem0_client:
            return []
        
        for attempt in range(max_retries + 1):
            try:
                # Use strict user_id filter - ensure we only get memories for this specific user
                filters = {
                    "user_id": user_id  # Direct filter, not OR clause
                }
                if query:
                    # Search with a specific query - get more results for better context
                    results = self.mem0_client.search(query, version="v2", filters=filters, limit=limit)
                else:
                    # Can't use empty query - use a general query to get user context
                    results = self.mem0_client.search("user information and conversation history", version="v2", filters=filters, limit=limit)
                
                # Handle different response formats
                if isinstance(results, dict) and "results" in results:
                    results = results["results"]
                
                if results and isinstance(results, list) and len(results) > 0:
                    # Double-check that all memories belong to this user
                    filtered_results = []
                    for mem in results:
                        mem_user_id = mem.get('user_id') or mem.get('metadata', {}).get('user_id')
                        if mem_user_id == user_id or not mem_user_id:  # Include if matches or no user_id (legacy)
                            filtered_results.append(mem)
                        else:
                            logger.warning(f"Filtered out memory with mismatched user_id: {mem_user_id} (expected: {user_id})")
                    
                    if filtered_results:
                        logger.info(f"Retrieved {len(filtered_results)} memories for user {user_id} (filtered from {len(results)} total)")
                        return filtered_results
                    else:
                        logger.warning(f"All {len(results)} memories were filtered out due to user_id mismatch")
                        return []
                
                # If no results and we have retries left, wait and retry
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 3  # 3s, 6s exponential backoff
                    logger.debug(f"No memories found for user {user_id}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                
                # No results after all retries
                if attempt == 0:
                    logger.info(f"No memories found for user {user_id} (this is normal for new users)")
                return []
                
            except Exception as e:
                logger.error(f"Error retrieving memories (attempt {attempt + 1}): {e}", exc_info=True)
                # On error, retry if we have attempts left
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 2  # 2s, 4s for errors
                    await asyncio.sleep(wait_time)
                    continue
                return []
    
    async def store_messages(self, messages: list, user_id: str) -> None:
        """Store conversation messages to both OpenMemory and Mem0 (if available)"""
        # Store to OpenMemory
        if self.openmemory_manager:
            try:
                await self.openmemory_manager.store_messages(messages, user_id)
            except Exception as e:
                logger.warning(f"Failed to store messages to OpenMemory: {e}")
        
        # Store to Mem0
        if not self.mem0_client:
            if not self.openmemory_manager:
                logger.warning("Neither Mem0 nor OpenMemory available - skipping message storage")
            return
        
        try:
            # Format messages for Mem0
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    formatted_messages.append(msg)
                elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                    content = msg.content
                    if isinstance(content, list):
                        # Extract text from list of content items
                        text_parts = [str(item) for item in content if not isinstance(item, ImageContent)]
                        content = " ".join(text_parts) if text_parts else str(content)
                    formatted_messages.append({
                        "role": msg.role,
                        "content": str(content)
                    })
            
            if formatted_messages:
                logger.info(f"📝 Storing {len(formatted_messages)} messages to Mem0 for user {user_id}")
                logger.debug(f"Messages to store: {formatted_messages}")
                result = self.mem0_client.add(formatted_messages, user_id=user_id)
                logger.info(f"✓ Successfully stored messages to Mem0 for user {user_id}")
                logger.debug(f"Mem0 response: {result}")
            else:
                logger.warning("No formatted messages to store")
        except Exception as e:
            logger.error(f"✗ Error storing messages to Mem0: {e}", exc_info=True)

