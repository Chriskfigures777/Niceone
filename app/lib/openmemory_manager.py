"""OpenMemory memory management for conversation storage and retrieval"""
import asyncio
import logging
import os
from typing import Optional
import httpx

logger = logging.getLogger("agent-Alex-2f2")

# Get API token from environment or use default from mcp.json
OPENMEMORY_API_TOKEN = os.getenv("OPENMEMORY_API_TOKEN", "om-5rqj2ru86nmfvydd972qlwbgky5ea1zh")
OPENMEMORY_API_URL = os.getenv("OPENMEMORY_API_URL", "https://api.openmemory.dev")
PROJECT_ID = os.getenv("OPENMEMORY_PROJECT_ID", "Chrisfig97/Dawn")


class OpenMemoryManager:
    """Manages OpenMemory storage and retrieval"""
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or OPENMEMORY_API_TOKEN
        self.api_url = OPENMEMORY_API_URL
        self.project_id = PROJECT_ID
    
    async def add_memory(
        self,
        title: str,
        content: str,
        user_id: Optional[str] = None,
        memory_types: Optional[list] = None,
        namespace: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Add a memory to OpenMemory"""
        if not self.api_token:
            logger.warning("OpenMemory API token not set - skipping memory storage")
            return False
        
        try:
            memory_metadata = {
                "project_id": self.project_id,
                **(metadata or {})
            }
            
            if user_id:
                memory_metadata["user_id"] = user_id
            if memory_types:
                memory_metadata["memory_types"] = memory_types
            if namespace:
                memory_metadata["namespace"] = namespace
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/memories",
                    headers={
                        "Authorization": f"Token {self.api_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "title": title,
                        "content": content,
                        "metadata": memory_metadata,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200 or response.status_code == 201:
                    logger.info(f"✓ Stored memory to OpenMemory: {title}")
                    return True
                else:
                    logger.error(f"OpenMemory API error ({response.status_code}): {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error storing memory to OpenMemory: {e}", exc_info=True)
            return False
    
    async def search_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        memory_types: Optional[list] = None,
        namespaces: Optional[list] = None,
        limit: int = 20,
        max_retries: int = 2
    ) -> list:
        """Search for memories in OpenMemory with retry logic"""
        if not self.api_token:
            return []
        
        params = {
            "query": query,
            "limit": limit,
            "project_id": self.project_id,
        }
        
        if user_id:
            params["user_id"] = user_id
        if memory_types:
            params["memory_types"] = ",".join(memory_types)
        if namespaces:
            params["namespaces"] = ",".join(namespaces)
        
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.api_url}/memories/search",
                        headers={
                            "Authorization": f"Token {self.api_token}",
                            "Content-Type": "application/json",
                        },
                        params=params,
                        timeout=30.0,
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        memories = data if isinstance(data, list) else data.get("results", [])
                        
                        if memories:
                            logger.info(f"Retrieved {len(memories)} memories from OpenMemory (attempt {attempt + 1})")
                            return memories
                    
                    # If no results and we have retries left, wait and retry
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) * 3  # 3s, 6s exponential backoff
                        logger.debug(f"No memories found, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    return []
            except Exception as e:
                logger.error(f"Error searching memories in OpenMemory (attempt {attempt + 1}): {e}", exc_info=True)
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 2  # 2s, 4s for errors
                    await asyncio.sleep(wait_time)
                    continue
                return []
        
        return []
    
    async def store_messages(self, messages: list, user_id: str) -> None:
        """Store conversation messages to OpenMemory"""
        if not self.api_token or not messages:
            return
        
        try:
            # Convert messages to conversation text
            conversation_text = "\n".join([
                f"{msg.get('role', 'unknown')}: {msg.get('content', str(msg))}"
                for msg in messages
            ])
            
            title = f"Conversation - {user_id}"
            content = conversation_text
            
            await self.add_memory(
                title=title,
                content=content,
                user_id=user_id,
                memory_types=["implementation"],
                namespace="conversations"
            )
            
            logger.info(f"✓ Stored {len(messages)} messages to OpenMemory for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing messages to OpenMemory: {e}", exc_info=True)
    
    async def retrieve_memories(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 20,
        max_retries: int = 2
    ) -> list:
        """Retrieve relevant memories for a user"""
        search_query = query or "user information and conversation history"
        return await self.search_memories(
            query=search_query,
            user_id=user_id,
            memory_types=["implementation", "component", "user_preference"],
            namespaces=["conversations"],
            limit=limit,
            max_retries=max_retries
        )




