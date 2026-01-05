# AI Refactoring Prompt: LiveKit Agent Code Refactoring and Bug Fixes

## ⚠️ CRITICAL FIRST STEP: Read LiveKit Documentation

**BEFORE starting any refactoring work, you MUST:**

1. **Use the MCP server to read LiveKit documentation extensively**
   - Access LiveKit documentation via the available MCP server tools
   - Read comprehensive documentation on the following topics:

2. **Required Documentation Topics to Read:**
   - **AgentSession**: How AgentSession works, lifecycle, events, and configuration
   - **Text Input Handling**: Default text input behavior, custom text input handlers, TextInputOptions
   - **Audio Output Management**: How to enable/disable audio output, audio output options
   - **RoomOptions**: Complete RoomOptions API, input/output options, participant management
   - **RealtimeModel**: OpenAI RealtimeModel integration, modalities (text/audio), turn detection
   - **Track Events**: track_published, track_unpublished events, how to handle mic mute/unmute
   - **Session Events**: user_input_transcribed, agent_state_changed, conversation_item_added
   - **Best Practices**: Recommended patterns for voice AI agents, common pitfalls to avoid

3. **Documentation Search Strategy:**
   - Search for "AgentSession" and read all relevant pages
   - Search for "text input" and "text output" handling
   - Search for "audio output" and "audio input" configuration
   - Search for "RoomOptions" and "RoomIO" documentation
   - Search for "RealtimeModel" integration patterns
   - Read examples of working voice agents
   - Look for troubleshooting guides related to text/audio issues

4. **Understanding Requirements:**
   - Understand how default text input behavior works (interrupts agent and generates reply)
   - Understand when and how to use custom text input handlers
   - Understand the relationship between audio output enabled/disabled and response modality
   - Understand how track events relate to mic state
   - Understand the proper way to trigger responses programmatically

5. **Document Key Findings:**
   - Note any recommended patterns for text/audio switching
   - Note any known issues or limitations
   - Note best practices for session configuration
   - Note proper error handling patterns

**Only proceed with refactoring after you have thoroughly read and understood the LiveKit documentation.**

## Objective
Refactor the `app/agent.py` file (currently 709 lines) down to 250-300 lines by extracting components into separate modules, while fixing critical bugs related to text input and audio output functionality.

## Current Issues to Fix

### Bug 1: Text Input Not Working
**Problem**: When users send text messages, the agent does not respond. Text messages are not being processed or the responses are not being generated.

**Root Cause**: The custom text input handler may be interfering with the default LiveKit behavior, or the `generate_reply` method is not being called correctly.

**Fix Requirements**:
- Ensure text messages trigger agent responses that appear in the chat
- Use LiveKit's default text input behavior (interrupts agent and generates reply)
- If custom handler is needed, ensure it properly calls `session.generate_reply(user_input=message)`
- Text responses should appear in the chat interface

### Bug 2: Audio Output Not Working on Unmute
**Problem**: When the user clicks the unmute button, the agent should immediately start speaking, but it doesn't.

**Root Cause**: Audio output may not be enabled properly when mic is unmuted, or the greeting trigger is not working.

**Fix Requirements**:
- When mic is unmuted (track_published event for microphone), enable audio output immediately
- Trigger an immediate audio greeting/acknowledgment when mic is first unmuted
- Ensure audio output is enabled before triggering the response
- The agent should speak immediately when unmuted, not wait for user input

### Bug 3: Audio/Text Mode Switching
**Problem**: The agent should respond in text mode for text messages and audio mode when mic is enabled, but the switching is not working correctly.

**Fix Requirements**:
- Text messages → text responses (audio output disabled)
- Mic unmuted → audio responses (audio output enabled)
- Mic muted → text-only mode (audio output disabled)
- Smooth switching between modes without breaking communication

## Refactoring Strategy

### Step 1: Extract Components to Separate Files

Create the following new files:

1. **`app/lib/ssl_config.py`** (20-30 lines)
   - Extract SSL certificate configuration (lines 22-41)
   - Export a function `configure_ssl()` that sets up SSL for macOS compatibility
   - Import and call in main agent file

2. **`app/lib/agent_instructions.py`** (170-180 lines)
   - Extract the long instructions string (lines 99-270)
   - Create a function `get_agent_instructions(default_email: str, time_context: str, current_time_et)` that returns the instructions
   - Include all the timezone, booking, and workflow instructions
   - Keep the dynamic parts (email, time context) as parameters

3. **`app/lib/memory_manager.py`** (80-100 lines)
   - Extract Mem0 memory handling (lines 309-463)
   - Create a `MemoryManager` class with methods:
     - `retrieve_memories(user_id, query=None)`
     - `store_messages(messages, user_id)`
   - Handle all Mem0 client interactions
   - Import and use in DefaultAgent class

4. **`app/lib/audio_manager.py`** (120-150 lines)
   - Extract `AudioSessionManager` class (lines 469-614)
   - Keep all mic mute/unmute handling logic
   - Keep text input handler (but fix it to work properly)
   - Keep audio greeting/acknowledgment triggers
   - Export the class for use in entrypoint

5. **`app/lib/image_handler.py`** (30-40 lines)
   - Extract image upload handling (lines 374-386)
   - Create a function or class method for handling image byte streams
   - Keep the base64 encoding and ImageContent creation

### Step 2: Simplify Main Agent File

The refactored `app/agent.py` should contain:

1. **Imports** (15-20 lines)
   - All necessary imports
   - Import from new modules

2. **Configuration** (30-40 lines)
   - Environment variable loading
   - Client initialization (CalCom, Mem0)
   - Logging setup
   - Call `configure_ssl()` from ssl_config module

3. **DefaultAgent Class** (80-100 lines)
   - `__init__`: Initialize with tools and instructions (call `get_agent_instructions()`)
   - `on_enter`: Set up image handler and video tracking (call image handler from module)
   - `on_user_turn_completed`: Extract email, call memory manager methods
   - Keep minimal, delegate to extracted modules

4. **Entrypoint Function** (60-80 lines)
   - Create agent and session
   - Set up audio manager
   - Register track event handlers
   - Start session with proper room options
   - Initialize audio state

5. **Main Block** (5-10 lines)
   - CLI startup

**Target**: 250-300 lines total

## Critical Functionality to Preserve

1. **All Cal.com Integration**: Booking, cancellation, rescheduling functionality
2. **Timezone Handling**: UTC ↔ Eastern Time conversion logic
3. **Mem0 Memory**: User memory storage and retrieval
4. **Image Upload**: Byte stream image handling
5. **Video Vision**: Live video feed processing
6. **Email Extraction**: Automatic email detection from messages
7. **Tool Integration**: All Cal.com tools must work
8. **Logging**: Maintain comprehensive logging for debugging

## Code Quality Requirements

1. **Error Handling**: Maintain try/except blocks with proper logging
2. **Type Hints**: Keep type annotations where present
3. **Documentation**: Add docstrings to new modules and functions
4. **Imports**: Organize imports logically (stdlib, third-party, local)
5. **Naming**: Use clear, descriptive names
6. **Separation of Concerns**: Each module should have a single responsibility

## Testing Checklist

After refactoring, verify:

- [ ] Text messages are received and agent responds in chat
- [ ] Unmuting mic enables audio and agent speaks immediately
- [ ] Muting mic disables audio and switches to text-only mode
- [ ] Cal.com bookings can be created, viewed, and cancelled
- [ ] Timezone conversions work correctly (UTC ↔ Eastern)
- [ ] Mem0 memory storage and retrieval works
- [ ] Image uploads are processed correctly
- [ ] Email extraction from messages works
- [ ] All tools are accessible and functional
- [ ] Logging provides useful debugging information

## Implementation Notes

**IMPORTANT**: Apply knowledge from LiveKit documentation when implementing these fixes.

1. **Text Input Handler**: 
   - Based on LiveKit docs, understand the default behavior: text input interrupts agent and generates reply
   - If keeping custom handler, ensure it calls `session.generate_reply(user_input=message)` correctly
   - Consider using default LiveKit behavior (`text_input=True`) if custom handler causes issues
   - Audio output should be disabled when processing text input
   - Follow LiveKit's recommended patterns for text input handling

2. **Audio Output Management**:
   - Based on LiveKit docs, understand how `session.output.set_audio_enabled()` works
   - Start with audio disabled by default
   - Enable when mic track is published (track_published event)
   - Disable when mic track is unpublished (track_unpublished event)
   - Trigger greeting immediately after enabling audio
   - Use proper async patterns for triggering responses

3. **Session Configuration**:
   - Follow LiveKit documentation for RoomOptions configuration
   - Use `text_input=True` for default text handling (or TextInputOptions if custom handler needed)
   - Configure `audio_input` with noise cancellation per LiveKit recommendations
   - Enable `video_input=True` for vision capabilities
   - Set up proper room options according to LiveKit best practices

4. **Event Handling**:
   - Use LiveKit's recommended patterns for track event handlers
   - Register event handlers BEFORE starting the session
   - Handle track_published and track_unpublished events correctly
   - Consider using session events (user_input_transcribed, etc.) if helpful

5. **Error Recovery**:
   - If text input fails, log error and attempt fallback
   - If audio enable fails, log error but continue
   - Don't let errors in one module break the entire agent
   - Follow LiveKit's error handling patterns from documentation

## Expected File Structure After Refactoring

```
app/
├── agent.py (250-300 lines) - Main entrypoint and agent class
├── lib/
│   ├── __init__.py
│   ├── ssl_config.py (20-30 lines) - SSL configuration
│   ├── agent_instructions.py (170-180 lines) - Agent instructions template
│   ├── memory_manager.py (80-100 lines) - Mem0 memory handling
│   ├── audio_manager.py (120-150 lines) - Audio session management
│   ├── image_handler.py (30-40 lines) - Image upload handling
│   ├── calcom_tools.py (existing, keep as is)
│   ├── calcom_client.py (existing, keep as is)
│   └── time_utils.py (existing, keep as is)
```

## Success Criteria

1. ✅ Main `agent.py` file is 250-300 lines
2. ✅ All functionality preserved and working
3. ✅ Text messages trigger responses in chat
4. ✅ Unmuting mic triggers immediate audio response
5. ✅ Code is modular and maintainable
6. ✅ No functionality is lost
7. ✅ All bugs are fixed

## Additional Context

- The agent uses OpenAI RealtimeModel with both text and audio modalities
- The frontend uses LiveKit React components
- The agent must support both text chat and voice conversation
- Cal.com integration is critical for booking functionality
- Mem0 is used for conversation memory (optional if API key not set)

---

**Instructions for AI Tool**: 

**STEP 0: READ DOCUMENTATION FIRST (MANDATORY)**
1. Use MCP server to access LiveKit documentation
2. Read extensively about AgentSession, text input, audio output, RoomOptions, RealtimeModel
3. Understand recommended patterns and best practices
4. Document key findings before proceeding

**STEP 1: Analyze Current Code**
1. Read the current `app/agent.py` file completely
2. Understand the current implementation and identify issues
3. Map current functionality to LiveKit documentation patterns

**STEP 2: Refactor and Fix**
1. Follow the refactoring strategy to extract components
2. Apply LiveKit best practices from documentation
3. Fix the bugs related to text input and audio output using proper LiveKit patterns
4. Ensure all functionality is preserved
5. Use correct LiveKit APIs and patterns throughout

**STEP 3: Verify**
1. Test that the refactored code works correctly
2. Verify text input triggers responses
3. Verify audio works on unmute
4. Maintain code quality and error handling
5. Ensure compliance with LiveKit recommended patterns

