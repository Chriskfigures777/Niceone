# Agent Audio Connection Fix - AI Prompt Documentation

## Problem Summary

The LiveKit voice agent was failing to connect to rooms and speak audio. Three critical issues were identified:

1. **Async Callback Registration Error**: The agent was trying to register an async callback directly with `.on()`, which LiveKit's event emitter doesn't support
2. **Room Connection Blocking**: The entrypoint was hanging because it tried to access `ctx.room.sid` before the room connection was established
3. **Room Connection Timeout**: The agent entrypoint wasn't completing within 10 seconds, causing LiveKit to timeout and shut down the agent

## Root Causes

### Issue 1: Async Callback Registration
- **Error**: `ValueError: Cannot register an async callback with .on(). Use asyncio.create_task within your synchronous callback instead.`
- **Location**: Line 417 in `agent.py` - `session.on("conversation_item_added", on_conversation_item_added)`
- **Cause**: LiveKit's event emitter requires synchronous callbacks. If you need async behavior, you must wrap it in a synchronous function that uses `asyncio.create_task()`

### Issue 2: Room SID Access Before Connection
- **Error**: Code hanging at `await ctx.room.sid` 
- **Location**: Lines 352 and 473 in `agent.py`
- **Cause**: The room connection is only established when `session.start()` is called. Trying to access `ctx.room.sid` before that causes the code to hang indefinitely

### Issue 3: Missing Audio Output Configuration
- **Issue**: Audio output wasn't explicitly enabled in RoomOptions
- **Location**: `session.start()` RoomOptions configuration
- **Cause**: While audio output is enabled by default, explicitly setting it ensures proper initialization

## Solutions Applied

### Fix 1: Wrap Async Callback in Synchronous Wrapper

**Before:**
```python
async def on_conversation_item_added(event):
    # async code here
    await ctx.room.local_participant.publish_data(...)

session.on("conversation_item_added", on_conversation_item_added)  # ❌ ERROR
```

**After:**
```python
async def on_conversation_item_added(event):
    # async code here
    await ctx.room.local_participant.publish_data(...)

# Wrap async callback in synchronous wrapper as required by .on()
def conversation_item_added_wrapper(event):
    """Synchronous wrapper that creates a task for the async callback"""
    asyncio.create_task(on_conversation_item_added(event))

session.on("conversation_item_added", conversation_item_added_wrapper)  # ✅ WORKS
```

**Key Learning**: LiveKit's `.on()` method requires synchronous callbacks. For async operations, create a synchronous wrapper that uses `asyncio.create_task()` to run the async function.

### Fix 2: Remove Blocking Room SID Access

**Before:**
```python
async def entrypoint(ctx: JobContext):
    logger.info(f"🚀 Agent entrypoint called for room: {ctx.room.name}")
    room_sid = await ctx.room.sid  # ❌ BLOCKS - room not connected yet
    logger.info(f"   Room SID: {room_sid}")
    # ... rest of code
```

**After:**
```python
async def entrypoint(ctx: JobContext):
    logger.info(f"🚀 Agent entrypoint called for room: {ctx.room.name}")
    # Don't access room.sid here - room connection happens in session.start()
    # ... rest of code
    
    # Only access room.sid AFTER session.start() completes
    await session.start(...)
    # Now room is connected, can access properties if needed
```

**Key Learning**: The room connection is established by `session.start()`. Don't try to access room properties like `sid` before calling `session.start()`. The room object exists but isn't connected until the session starts.

### Fix 3: Explicitly Enable Audio Output

**Before:**
```python
await session.start(
    agent=agent,
    room=ctx.room,
    room_options=room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(...),
        video_input=True,
        text_input=True,
        # audio_output not explicitly set
    ),
)
```

**After:**
```python
await session.start(
    agent=agent,
    room=ctx.room,
    room_options=room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(...),
        audio_output=True,  # ✅ Explicitly enable audio output
        video_input=True,
        text_input=True,
    ),
)
```

**Key Learning**: While audio output is enabled by default, explicitly setting it in RoomOptions ensures proper initialization and makes the intent clear.

### Fix 4: Add Automatic Greeting

**Added:**
```python
# Step 9: Trigger initial greeting so agent speaks when call starts
logger.info("👋 Step 9: Triggering initial greeting...")
try:
    # Wait for session to fully initialize
    await asyncio.sleep(1.5)
    
    # Verify agent is in the room
    local_participant = ctx.room.local_participant
    if not local_participant:
        logger.warning("⚠ Cannot trigger greeting - agent not in room yet")
        return
    
    # Ensure audio output is enabled
    session.output.set_audio_enabled(True)
    
    # Trigger greeting
    session.generate_reply(
        instructions="Greet the user warmly and let them know you're ready to help with their voice assistant needs."
    )
    logger.info("✓ Greeting triggered - agent should be speaking now")
except Exception as e:
    logger.error(f"✗ Could not trigger initial greeting: {e}", exc_info=True)
```

**Key Learning**: For realtime models (like OpenAI Realtime), use `session.generate_reply()` with `instructions` parameter to make the agent speak. This triggers the LLM to generate a response that will be spoken.

## Complete Fix Checklist

When fixing similar issues in LiveKit agents:

- [ ] **Check async callbacks**: If registering async functions with `.on()`, wrap them in synchronous functions that use `asyncio.create_task()`
- [ ] **Avoid pre-connection room access**: Don't access `ctx.room.sid` or other room properties before `session.start()` completes
- [ ] **Explicitly enable audio**: Set `audio_output=True` in RoomOptions even though it's the default
- [ ] **Verify connection**: Check `ctx.room.local_participant` exists after `session.start()` to confirm agent joined
- [ ] **Add greeting**: Use `session.generate_reply(instructions=...)` for realtime models to trigger initial speech
- [ ] **Enable audio output**: Call `session.output.set_audio_enabled(True)` after session starts
- [ ] **Check audio tracks**: Verify agent has published audio tracks before expecting speech

## Testing Verification

After applying fixes, verify:
1. ✅ Agent entrypoint completes without hanging
2. ✅ No "room connection not established" warnings
3. ✅ Agent joins room (check logs for "Agent has joined the room")
4. ✅ Audio tracks are published (check logs for "Agent has X audio track(s) published")
5. ✅ Agent speaks greeting when call starts
6. ✅ Agent responds to user voice input

## Related LiveKit Documentation

- Event Emitter: Requires synchronous callbacks
- AgentSession.start(): Establishes room connection
- RoomOptions.audio_output: Controls audio output
- session.generate_reply(): Triggers agent speech for realtime models
- session.output.set_audio_enabled(): Dynamically enables/disables audio

## Error Messages to Watch For

- `"Cannot register an async callback with .on()"` → Wrap in synchronous function
- `"The room connection was not established within 10 seconds"` → Check if `session.start()` is being called and completing
- `"Agent did not join the room"` → Verify session.start() succeeded and agent is in room



