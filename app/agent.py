"""Main agent entrypoint for LiveKit voice AI agent"""
import logging
import os
import asyncio
import re
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, room_io, get_job_context
from livekit.plugins import noise_cancellation, openai
from livekit.plugins.openai import realtime
from openai.types.beta.realtime.session import TurnDetection
from mem0 import MemoryClient

# Local imports
from lib.ssl_config import configure_ssl
from lib.agent_instructions import get_agent_instructions
from lib.memory_manager import MemoryManager
from lib.audio_manager import AudioSessionManager
from lib.image_handler import handle_image_upload
from lib.calcom_client import CalComClient
from lib.time_utils import get_current_eastern_time, format_eastern_time
from lib.calcom_tools import create_calcom_tools, _email_state

logger = logging.getLogger("agent-Alex-2f2")

# Configure SSL certificates for macOS compatibility
configure_ssl()

# Configure logging level
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def check_livekit_dependencies():
    """Check if LiveKit dependencies (libstdc++.so.6) are available"""
    import ctypes
    import sys
    import platform
    
    logger.info("🔍 Checking LiveKit dependencies...")
    
    # Check if we're on Linux (where libstdc++.so.6 is needed)
    if platform.system() == "Linux":
        try:
            # Try to load libstdc++.so.6
            lib_paths = [
                "/usr/lib/x86_64-linux-gnu/libstdc++.so.6",
                "/usr/lib/libstdc++.so.6",
                "/lib/x86_64-linux-gnu/libstdc++.so.6",
            ]
            
            # Also check Nix store if LD_LIBRARY_PATH is set
            import os
            ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
            if ld_library_path:
                for path_dir in ld_library_path.split(":"):
                    if path_dir:
                        lib_paths.append(f"{path_dir}/libstdc++.so.6")
            
            # Try to find in /nix/store
            import subprocess
            try:
                result = subprocess.run(
                    ["find", "/nix/store", "-name", "libstdc++.so.6"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    nix_path = result.stdout.strip().split("\n")[0]
                    lib_paths.insert(0, nix_path)
                    logger.info(f"✓ Found libstdc++.so.6 in Nix store: {nix_path}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Try to load the library
            loaded = False
            for lib_path in lib_paths:
                try:
                    if os.path.exists(lib_path):
                        ctypes.CDLL(lib_path)
                        logger.info(f"✓ Successfully loaded libstdc++.so.6 from: {lib_path}")
                        loaded = True
                        break
                except OSError:
                    continue
            
            if not loaded:
                logger.warning("⚠️  libstdc++.so.6 not found in standard locations")
                logger.warning("   This may cause issues when importing LiveKit. Check LD_LIBRARY_PATH.")
                logger.warning(f"   Current LD_LIBRARY_PATH: {ld_library_path or 'Not set'}")
            else:
                logger.info("✓ LiveKit dependencies check passed")
        except Exception as e:
            logger.warning(f"⚠️  Could not verify libstdc++.so.6: {e}")
    else:
        logger.info(f"✓ Running on {platform.system()} - libstdc++.so.6 check not needed")


# Run dependency check before importing LiveKit
check_livekit_dependencies()

# Load environment variables
load_dotenv(".env.local")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CALCOM_API_KEY = os.getenv("CALCOM_API_KEY")
if not CALCOM_API_KEY:
    logger.error("CALCOM_API_KEY is not set in environment variables")
    raise ValueError("CALCOM_API_KEY is required. Please set it in .env.local file or environment variables.")
DEFAULT_EMAIL = os.getenv("DEFAULT_EMAIL", "")
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")

if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required. Please set it in .env.local file or environment variables.")

logger.info("OPENAI_API_KEY loaded successfully")
logger.info(f"Cal.com API key loaded: {CALCOM_API_KEY[:20]}...")
logger.info(f"Default email: {DEFAULT_EMAIL if DEFAULT_EMAIL else 'Not set'}")

calcom_client = CalComClient(CALCOM_API_KEY)

# Initialize Mem0 client
if MEM0_API_KEY:
    try:
        mem0_client = MemoryClient(api_key=MEM0_API_KEY)
        logger.info(f"✓ Mem0 client initialized successfully (API key: {MEM0_API_KEY[:10]}...)")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Mem0 client: {e}", exc_info=True)
        mem0_client = None
else:
    mem0_client = None
    logger.warning("Mem0 API key not set - memory features will be disabled")

# Update shared email state
_email_state["email"] = DEFAULT_EMAIL


class DefaultAgent(Agent):
    """Main agent class with Cal.com integration and memory management"""
    
    def __init__(self, default_email: str = DEFAULT_EMAIL) -> None:
        self._tasks = []
        self.default_email = default_email
        self.user_email = default_email  # Track user's email from conversation
        self._conversation_started = False  # Track if we've retrieved initial memories
        self._retrieved_memories = []  # Store retrieved memories for context
        _email_state["email"] = default_email  # Update shared state
        
        current_time_et = get_current_eastern_time()
        time_context = f"Current time: {format_eastern_time(current_time_et)}"
        
        # Create tools before calling super().__init__() so we can pass them
        # Note: We'll update agent_instance after creating the agent
        tools = create_calcom_tools(calcom_client, default_email, agent_instance=None)
        
        # Get agent instructions from module (memories will be added after retrieval)
        instructions = get_agent_instructions(default_email, time_context, current_time_et, memories_context="")
        
        super().__init__(
            instructions=instructions,
            tools=tools,
        )
        self._calcom_tools = tools
        
        # Store agent instance reference for tools to access
        # Tools will access this via the closure
        self._agent_instance_for_tools = self
        
        # Initialize memory manager
        self.memory_manager = MemoryManager(mem0_client)

    async def on_enter(self):
        """Set up image handler and video tracking when agent enters session"""
        room = get_job_context().room
        
        def _image_received_handler(reader, participant_identity):
            task = asyncio.create_task(handle_image_upload(self, reader, participant_identity))
            self._tasks.append(task)
            task.add_done_callback(lambda t: self._tasks.remove(t) if t in self._tasks else None)
        
        room.register_byte_stream_handler("images", _image_received_handler)
        logger.info("Image upload handler registered on 'images' topic")
        
        def setup_video_tracking():
            remote_participants = list(room.remote_participants.values())
            if remote_participants:
                remote_participant = remote_participants[0]
                video_tracks = [pub for pub in list(remote_participant.track_publications.values()) 
                               if pub.track and pub.track.kind == rtc.TrackKind.KIND_VIDEO]
                for publication in video_tracks:
                    logger.info(f"✓ Video track detected: {publication.track.sid}, source: {publication.source}")
        
        setup_video_tracking()
        
        @room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_VIDEO:
                pass
        
        @room.on("track_published")
        def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if publication.track and publication.track.kind == rtc.TrackKind.KIND_VIDEO:
                pass
        
        # Retrieve memories immediately when session starts (not waiting for first user turn)
        # This ensures the agent has full conversation context from text mode
        if self.memory_manager.mem0_client and not self._conversation_started:
            user_id = self.user_email or "default_user"
            try:
                logger.info(f"🔍 Retrieving memories for user {user_id} at session start...")
                memories = await self.memory_manager.retrieve_memories(
                    user_id, 
                    query="user information and conversation history",
                    limit=20  # Get more memories for better context
                )
                if memories:
                    logger.info(f"✓ Retrieved {len(memories)} memories for user {user_id}")
                    # Store memories for use in agent responses
                    # The memories will be available when processing user messages
                    self._retrieved_memories = memories
                    logger.info("✓ Memories stored - agent will use them in responses")
                else:
                    logger.info(f"No existing memories found for user {user_id} (this is normal for new users)")
                    self._retrieved_memories = []
            except Exception as e:
                logger.warning(f"Could not retrieve initial memories: {e}", exc_info=True)
                self._retrieved_memories = []
            self._conversation_started = True
    
    async def on_agent_turn_completed(self, turn_ctx) -> None:
        """Handle agent turn completion - ensure full response text is sent as chat message"""
        try:
            # After agent finishes responding, capture the full response text from chat_ctx
            # RealtimeModel streams audio but may not send complete text in chat messages
            # We need to extract the full text and send it as a proper chat message
            if hasattr(self, 'chat_ctx') and self.chat_ctx:
                messages = list(self.chat_ctx.messages)
                if messages:
                    # Get the last assistant message (the agent's response)
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'role') and last_msg.role == 'assistant':
                        # Use the text_content property which properly extracts all text content
                        # This joins multiple text content items with newlines automatically
                        full_text = last_msg.text_content if hasattr(last_msg, 'text_content') else ""

                        # Send the full response text as a chat message to ensure it's displayed
                        # This is critical because RealtimeModel may only stream partial text
                        if full_text and len(full_text.strip()) > 0:
                            room = get_job_context().room
                            try:
                                # Use room's chat API to send the complete message
                                # RealtimeModel streams audio but text messages might be incomplete
                                # So we send the full text from chat_ctx to ensure it's displayed
                                await room.local_participant.publish_data(
                                    data=full_text.encode('utf-8'),
                                    topic="lk-chat",  # LiveKit chat topic
                                    reliable=True
                                )
                                logger.info(f"✓ Sent full agent response text ({len(full_text)} chars) as chat message")
                            except Exception as e:
                                logger.warning(f"Could not send full response text: {e}", exc_info=True)
        except Exception as e:
            logger.warning(f"Error in on_agent_turn_completed: {e}", exc_info=True)
    
    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        """Handle user turn completion - extract email and manage memory"""
        current_time = get_current_eastern_time()
        time_stamp = format_eastern_time(current_time)
        logger.debug(f"User turn completed at {time_stamp}")
        
        # Extract email from user message if mentioned
        if new_message and hasattr(new_message, 'content'):
            content = str(new_message.content) if hasattr(new_message.content, '__str__') else str(new_message.content)
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, content)
            if emails:
                self.user_email = emails[0]
                _email_state["email"] = emails[0]  # Update shared state for tools
                logger.info(f"User email updated from message: {self.user_email}")
        
        # Inject retrieved memories into chat context if available (from on_enter)
        # This ensures the agent has full conversation history from text mode
        if hasattr(self, '_retrieved_memories') and self._retrieved_memories and hasattr(self, 'chat_ctx') and self.chat_ctx:
            try:
                # Check if we've already added memory context (avoid duplicates)
                if not hasattr(self, '_memory_context_added'):
                    # Filter and validate memories - only use actual conversation memories
                    valid_memories = []
                    for mem in self._retrieved_memories[:20]:  # Top 20 memories
                        memory_text = mem.get('memory', str(mem))
                        # Only include memories that look like actual conversation content
                        # Skip generic or synthetic memories
                        if memory_text and len(memory_text.strip()) > 10:
                            # Check if it's a real conversation memory (contains user/assistant dialogue patterns)
                            if any(keyword in memory_text.lower() for keyword in ['user', 'said', 'asked', 'mentioned', 'discussed', 'talked', 'conversation']):
                                valid_memories.append(memory_text)
                    
                    if valid_memories:
                        memory_context = "\n".join([f"- {mem}" for mem in valid_memories])
                        # Add memory context to chat context so agent can use it
                        from livekit.agents.llm import ChatContext
                        chat_ctx = self.chat_ctx.copy()
                        # Add as a system message with strict rules about memory usage
                        context_text = f"Previous conversation context (ONLY reference what is explicitly stated below):\n{memory_context}\n\n🚨 CRITICAL: Only reference information EXPLICITLY in the memories above. If asked about something NOT listed, say 'I don't have that information from our previous conversations'. NEVER make up or guess conversation details."
                        chat_ctx.add_message(role="system", content=context_text)
                        await self.update_chat_ctx(chat_ctx)
                        self._memory_context_added = True
                        logger.info(f"✓ Injected {len(valid_memories)} validated memories into chat (filtered from {len(self._retrieved_memories)} total)")
                    else:
                        logger.info("No valid conversation memories found - skipping memory injection")
            except Exception as e:
                logger.warning(f"Could not inject memory context: {e}", exc_info=True)
        
        # Also retrieve memories periodically during conversation to refresh context
        if self._conversation_started and self.memory_manager.mem0_client:
            # Every 3rd message, refresh memories to get latest context
            if not hasattr(self, '_message_count'):
                self._message_count = 0
            self._message_count += 1
            if self._message_count % 3 == 0:  # Every 3 messages (more frequent)
                user_id = self.user_email or "default_user"
                try:
                    memories = await self.memory_manager.retrieve_memories(user_id, query="recent conversation and user preferences", limit=15)
                    if memories:
                        self._retrieved_memories = memories
                        logger.info(f"Refreshed {len(memories)} memories for ongoing conversation")
                except Exception as e:
                    logger.debug(f"Could not refresh memories: {e}")
        
        # Store conversation messages to Mem0 (ALL messages, not just recent)
        if self.memory_manager.mem0_client and new_message:
            user_id = self.user_email or "default_user"
            # Track which messages we've already stored to avoid duplicates
            if not hasattr(self, '_stored_message_ids'):
                self._stored_message_ids = set()
            
            # Schedule storage after a delay to allow assistant response to be added to context
            async def delayed_store():
                await asyncio.sleep(2)  # Wait for assistant to respond
                try:
                    if hasattr(self, 'chat_ctx') and self.chat_ctx:
                        messages = list(self.chat_ctx.messages)
                        if messages:
                            # Format ALL messages for Mem0 (not just recent ones)
                            formatted = []
                            for msg in messages:
                                # Create a unique ID for this message to avoid duplicates
                                if hasattr(msg, 'id'):
                                    msg_id = str(msg.id)
                                else:
                                    # Generate ID from content hash
                                    import hashlib
                                    content_str = str(getattr(msg, 'content', ''))
                                    msg_id = hashlib.md5(content_str.encode()).hexdigest()
                                
                                # Only store messages we haven't stored yet
                                if msg_id not in self._stored_message_ids:
                                    if hasattr(msg, 'role') and hasattr(msg, 'content'):
                                        content = msg.content
                                        # Use text_content property to properly extract all text
                                        text = msg.text_content if hasattr(msg, 'text_content') else str(content)
                                        formatted.append({
                                            "role": msg.role,
                                            "content": text
                                        })
                                        self._stored_message_ids.add(msg_id)
                            
                            if formatted:
                                logger.info(f"📤 Storing {len(formatted)} new messages to Mem0 (total stored: {len(self._stored_message_ids)})")
                                await self.memory_manager.store_messages(formatted, user_id)
                except Exception as e:
                    logger.error(f"Error in delayed Mem0 storage: {e}", exc_info=True)
            
            # Store asynchronously to not block the conversation
            task = asyncio.create_task(delayed_store())
            self._tasks.append(task)
            task.add_done_callback(lambda t: self._tasks.remove(t) if t in self._tasks else None)


server = AgentServer()

# Store agent reference for session end callback
_agent_instance = None


async def on_session_end(session_report):
    """Store final conversation to Mem0 when call ends - for chatbot mode"""
    global _agent_instance
    try:
        # Use stored agent instance to access conversation
        if _agent_instance and _agent_instance.memory_manager.mem0_client:
            user_id = _agent_instance.user_email or "default_user"
            # Get final conversation messages from agent's chat context
            if hasattr(_agent_instance, 'chat_ctx') and _agent_instance.chat_ctx:
                messages = list(_agent_instance.chat_ctx.messages)
                if messages:
                    # Format messages for Mem0
                    formatted = []
                    for msg in messages:
                        if hasattr(msg, 'role') and hasattr(msg, 'content'):
                            content = msg.content
                            # Use text_content property to properly extract all text
                            text = msg.text_content if hasattr(msg, 'text_content') else str(msg.content)
                            formatted.append({
                                "role": msg.role,
                                "content": text
                            })
                    if formatted:
                        logger.info(f"💾 Storing final conversation ({len(formatted)} messages) to Mem0 for chatbot mode")
                        await _agent_instance.memory_manager.store_messages(formatted, user_id)
                        logger.info("✓ Conversation stored - chatbot mode will have full context")
    except Exception as e:
        logger.error(f"Error storing final conversation to Mem0: {e}", exc_info=True)
    finally:
        _agent_instance = None  # Clear reference


@server.rtc_session(agent_name="Alex-2f2", on_session_end=on_session_end)
async def entrypoint(ctx: JobContext):
    """Main entrypoint for the agent session"""
    logger.info(f"🚀 Agent entrypoint called for room: {ctx.room.name}")
    logger.info(f"   Agent name: Alex-2f2")
    global _agent_instance
    
    agent = None
    session = None
    
    try:
        # Step 1: Create agent instance
        logger.info("📦 Step 1: Creating DefaultAgent instance...")
        try:
            agent = DefaultAgent(default_email=DEFAULT_EMAIL)
            _agent_instance = agent  # Store for session end callback and for tools to access
            tools = getattr(agent, '_calcom_tools', [])
            logger.info(f"✓ Agent created successfully. Tools count: {len(tools)}")
        except Exception as e:
            logger.error(f"✗ Failed to create agent instance: {e}", exc_info=True)
            raise
        
        # Step 2: Initialize LLM
        logger.info("🤖 Step 2: Initializing OpenAI RealtimeModel...")
        try:
            llm = openai.realtime.RealtimeModel(
                voice="alloy",
                temperature=0.7,
                turn_detection=TurnDetection(
                    type="semantic_vad",
                    eagerness="high",
                    create_response=True,
                    interrupt_response=True  # Critical for streaming - allows immediate interruption
                ),
                modalities=["text", "audio"],  # Support both text and audio streaming
            )
            logger.info("✓ OpenAI RealtimeModel initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to initialize RealtimeModel: {e}", exc_info=True)
            raise
        
        # Step 3: Create session
        logger.info("📱 Step 3: Creating AgentSession...")
        try:
            session = AgentSession(llm=llm)
            logger.info("✓ AgentSession created successfully")

            # Add event listener for conversation items (chat messages)
            async def on_conversation_item_added(event):
                """Handle conversation items (messages) being added - send assistant messages to chat"""
                try:
                    message = event.item
                    # Only process assistant messages (agent responses)
                    if hasattr(message, 'role') and message.role == 'assistant':
                        # Use the text_content property to get the full text
                        full_text = message.text_content if hasattr(message, 'text_content') else ""

                        if full_text and len(full_text.strip()) > 0:
                            # Send the complete response to chat
                            await ctx.room.local_participant.publish_data(
                                data=full_text.encode('utf-8'),
                                topic="lk-chat",
                                reliable=True
                            )
                            logger.info(f"✓ Sent assistant message to chat ({len(full_text)} chars)")
                except Exception as e:
                    logger.warning(f"Error in conversation_item_added handler: {e}", exc_info=True)

            # Wrap async callback in synchronous wrapper as required by .on()
            def conversation_item_added_wrapper(event):
                """Synchronous wrapper that creates a task for the async callback"""
                asyncio.create_task(on_conversation_item_added(event))
            
            session.on("conversation_item_added", conversation_item_added_wrapper)
            logger.info("✓ Registered conversation_item_added event handler")
        except Exception as e:
            logger.error(f"✗ Failed to create AgentSession: {e}", exc_info=True)
            raise
        
        # Step 4: Create audio manager
        logger.info("🎤 Step 4: Creating AudioSessionManager...")
        try:
            audio_manager = AudioSessionManager(session)
            logger.info("✓ AudioSessionManager created successfully")
        except Exception as e:
            logger.error(f"✗ Failed to create AudioSessionManager: {e}", exc_info=True)
            raise
        
        # Step 5: Set up event handlers
        logger.info("📡 Step 5: Registering event handlers...")
        try:
            def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                logger.info(f"Track published event: kind={publication.track.kind if publication.track else 'None'}, "
                           f"source={publication.source}, participant={participant.identity}")
                if (publication.track and 
                    publication.track.kind == rtc.TrackKind.KIND_AUDIO and 
                    publication.source == rtc.TrackSource.SOURCE_MICROPHONE):
                    logger.info("Microphone track published - calling handle_mic_unmuted")
                    audio_manager.handle_mic_unmuted()
                else:
                    logger.debug(f"Ignoring track published - not a microphone track")
            
            def on_track_unpublished(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                """Handle track unpublished event - detect when mic is muted"""
                logger.info(f"Track unpublished event: kind={publication.track.kind if publication.track else 'None'}, "
                           f"source={publication.source}, participant={participant.identity}")
                if (publication.track and 
                    publication.track.kind == rtc.TrackKind.KIND_AUDIO and 
                    publication.source == rtc.TrackSource.SOURCE_MICROPHONE):
                    logger.info("🔇 Microphone track unpublished - mic is muted, cutting off agent audio")
                    audio_manager.handle_mic_muted()
                else:
                    logger.debug(f"Ignoring track unpublished - not a microphone track")
            
            # Register event handlers BEFORE starting session
            ctx.room.on("track_published", on_track_published)
            ctx.room.on("track_unpublished", on_track_unpublished)
            logger.info("✓ Event handlers registered successfully")
        except Exception as e:
            logger.error(f"✗ Failed to register event handlers: {e}", exc_info=True)
            raise
        
        # Step 6: Start session (CRITICAL - this is where agent joins the room)
        logger.info("🚀 Step 6: Starting agent session (agent will join room)...")
        logger.info(f"   Room name: {ctx.room.name}")
        try:
            await session.start(
                agent=agent,
                room=ctx.room,
                room_options=room_io.RoomOptions(
                    audio_input=room_io.AudioInputOptions(
                        noise_cancellation=lambda params: (
                            noise_cancellation.BVCTelephony() 
                            if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP 
                            else noise_cancellation.BVC()
                        ),
                    ),
                    audio_output=True,  # Explicitly enable audio output
                    video_input=True,
                    # Use LiveKit's default text input behavior (interrupts and generates reply)
                    text_input=True,
                ),
            )
            logger.info("✓ Agent session started - waiting for agent to join room...")
            
            # Verify agent actually joined by checking room participants
            await asyncio.sleep(0.5)  # Give it a moment to join
            local_participant = ctx.room.local_participant
            if local_participant:
                logger.info(f"✓ Agent has joined the room as: {local_participant.identity}")
                logger.info(f"   Participant SID: {local_participant.sid}")
            else:
                logger.warning("⚠ Agent session started but local_participant is None")
        except Exception as e:
            logger.error(f"✗ CRITICAL: Failed to start agent session: {e}", exc_info=True)
            logger.error(f"   This error prevents the agent from joining the room!")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error message: {str(e)}")
            raise
        
        # Step 7: Configure audio output
        logger.info("🔊 Step 7: Configuring audio output...")
        try:
            session.output.set_audio_enabled(True)
            logger.info("✓ Audio output enabled - agent can speak")
        except Exception as e:
            logger.warning(f"⚠ Could not enable audio output initially: {e}")
            # Don't raise - this is not critical for joining
        
        # Step 8: Check for existing mic tracks
        logger.info("🎤 Step 8: Checking for existing microphone tracks...")
        try:
            audio_manager.check_existing_mic_tracks(ctx.room)
            logger.info("✓ Microphone check completed")
        except Exception as e:
            logger.warning(f"⚠ Error checking existing mic tracks: {e}")
            # Don't raise - this is not critical for joining
        
        # Step 9: Trigger initial greeting so agent speaks when call starts
        logger.info("👋 Step 9: Triggering initial greeting...")
        try:
            # Wait a moment to ensure everything is fully initialized and agent has joined
            await asyncio.sleep(1.5)  # Give more time for full initialization and audio track publishing
            
            # Verify agent is in the room
            local_participant = ctx.room.local_participant
            if not local_participant:
                logger.warning("⚠ Cannot trigger greeting - agent not in room yet")
                return
            
            logger.info(f"✓ Agent confirmed in room: {local_participant.identity}")
            
            # Check if agent has published audio tracks
            audio_tracks = [pub for pub in local_participant.track_publications.values() 
                          if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO]
            if audio_tracks:
                logger.info(f"✓ Agent has {len(audio_tracks)} audio track(s) published")
                for track in audio_tracks:
                    logger.info(f"   Audio track SID: {track.track.sid}, source: {track.source}")
            else:
                logger.warning("⚠ Agent has no audio tracks published yet - audio may not work")
            
            # Ensure audio output is enabled
            try:
                session.output.set_audio_enabled(True)
                logger.info("✓ Audio output confirmed enabled before greeting")
            except Exception as e:
                logger.error(f"✗ Failed to enable audio output: {e}", exc_info=True)
                # Continue anyway - might still work
            
            # Trigger a greeting that will make the agent speak
            logger.info("🎤 Triggering greeting - agent should start speaking now...")
            logger.info(f"   Room: {ctx.room.name}")
            logger.info(f"   Agent identity: {local_participant.identity}")
            
            # Use generate_reply for realtime models (OpenAI Realtime)
            handle = session.generate_reply(
                instructions="Greet the user warmly and let them know you're ready to help with their voice assistant needs."
            )
            logger.info("✓ Greeting triggered - waiting for agent to start speaking...")
            
            # Wait a bit to see if speech starts
            await asyncio.sleep(0.5)
            logger.info("✓ Greeting call completed - agent should be speaking now")
        except Exception as e:
            logger.error(f"✗ Could not trigger initial greeting: {e}", exc_info=True)
            # Don't raise - agent can still respond to user input
        
        logger.info("✅ Agent session started successfully - agent is ready!")
        logger.info(f"   Room: {ctx.room.name}")
        logger.info(f"   Agent joined as: {agent.__class__.__name__}")
        
    except Exception as e:
        logger.error(f"❌ FATAL ERROR in agent entrypoint: {e}", exc_info=True)
        logger.error(f"   Room: {ctx.room.name}")
        logger.error(f"   This error prevents the agent from joining the room!")
        logger.error(f"   The client will see: 'Agent did not join the room'")
        # Re-raise to let LiveKit know the agent failed to start
        raise


if __name__ == "__main__":
    logger.info("Starting agent server...")
    logger.info(f"Agent name: Alex-2f2")
    cli.run_app(server)
