# AI Prompt: Fix Microphone Auto-Enable and Audio Output Issues

## Problem Summary

We have a LiveKit voice agent application with two critical bugs:

### Bug 1: Microphone Auto-Enables on Text Send
**Issue**: When a user presses Enter or clicks the send button to send a text message, the microphone automatically turns on (unmutes). This should NOT happen - the mic should only turn on when the user explicitly clicks the microphone toggle button.

**Expected Behavior**: 
- User types a message and presses Enter/send → Message sends, mic stays OFF
- User clicks mic button → Mic turns ON
- User sends another text message → Mic stays in whatever state it was (ON or OFF)

**Current Behavior**:
- User types a message and presses Enter/send → Message sends, mic automatically turns ON (unwanted)

### Bug 2: Audio Output Not Enabling When Mic is Unmuted
**Issue**: When the user manually clicks the unmute button to turn on the microphone, the agent's audio output is not being enabled. The agent should respond in voice mode when the mic is on, but it's not working.

**Expected Behavior**:
- User clicks unmute button → Mic turns ON → Agent audio output enables → Agent responds in voice
- User clicks mute button → Mic turns OFF → Agent audio output disables → Agent responds in text only

**Current Behavior**:
- User clicks unmute button → Mic turns ON → Agent audio output does NOT enable → Agent still responds in text only (broken)

## Technical Context

### Architecture
- **Frontend**: Next.js/React with LiveKit React components
- **Backend**: Python agent using LiveKit Agents framework
- **Agent Model**: OpenAI Realtime API (supports both text and audio modalities)

### Key Files

1. **Frontend - Chat Input Component**: `app/components/livekit/agent-control-bar/chat-input.tsx`
   - Handles text message sending
   - Should NOT interact with microphone state

2. **Frontend - Agent Control Bar**: `app/components/livekit/agent-control-bar/agent-control-bar.tsx`
   - Contains microphone toggle button
   - Uses `useInputControls` hook for mic state management
   - Currently has a `useEffect` that disables mic on connection (may need adjustment)

3. **Frontend - Input Controls Hook**: `app/components/livekit/agent-control-bar/hooks/use-input-controls.ts`
   - Uses `useTrackToggle` from `@livekit/components-react` for mic toggle
   - Uses `usePersistentUserChoices` to save/restore mic state
   - The `handleToggleMicrophone` function saves the mic state

4. **Backend - Agent Entrypoint**: `app/agent.py` (lines 433-530)
   - Registers `track_published` and `track_unpublished` event handlers
   - Should enable/disable audio output based on mic state
   - Currently checks for existing tracks after session starts (lines 520-530)

### Current Implementation Details

**Agent Side (Python)**:
- Event handlers registered before session starts (line 496-497)
- `on_track_published`: Should enable audio output when mic track is published
- `on_track_unpublished`: Should disable audio output when mic track is unpublished
- After session starts, checks for existing mic tracks (lines 520-530)
- Starts with audio output disabled (line 516)

**Frontend Side (React)**:
- `useTrackToggle` hook manages mic state
- `usePersistentUserChoices` may be restoring a saved "mic enabled" state
- `useEffect` in agent-control-bar.tsx tries to disable mic on connection (may have issues)

## Root Cause Analysis Needed

### For Bug 1 (Mic Auto-Enabling):
1. **Check if `usePersistentUserChoices` is restoring mic state**: The hook might be reading from localStorage and auto-enabling the mic when the session starts or when a message is sent.

2. **Check if `useTrackToggle` has default behavior**: The `useTrackToggle` hook from LiveKit might have some default behavior that enables the mic.

3. **Check if session start triggers mic enable**: When the session starts (triggered by sending first message), something might be enabling the mic.

4. **Check for event handlers**: Look for any event handlers that might be listening to message send events and enabling the mic.

5. **Check browser permissions**: Browser might be auto-enabling mic when audio context is created.

### For Bug 2 (Audio Output Not Enabling):
1. **Event handler timing**: The `track_published` event might be firing before the event handler is registered, or the event might not be firing at all.

2. **Event handler registration**: The event handlers are registered before `session.start()`, but they might need to be registered differently or checked after session starts.

3. **Track detection logic**: The check for existing tracks (lines 520-530) might not be working correctly - verify the logic for detecting mic tracks.

4. **Session state**: The `session.output.set_audio_enabled(True)` call might be failing silently - check for exceptions.

5. **OpenAI Realtime API behavior**: The Realtime API might need the modalities to be set differently, or there might be a conflict between text and audio modalities.

6. **Track source matching**: Verify that `rtc.TrackSource.SOURCE_MICROPHONE` is the correct source type being published.

## Investigation Steps

1. **Add comprehensive logging**:
   - Log when mic toggle is called and from where
   - Log when `track_published` event fires
   - Log when `set_audio_enabled` is called and its result
   - Log the state of `mic_enabled` variable
   - Log when text messages are sent

2. **Check event flow**:
   - Verify `track_published` event is actually firing when mic is toggled
   - Verify the event handler is being called
   - Verify the track source and kind match the conditions

3. **Test timing**:
   - Check if there's a race condition between session start and event handler registration
   - Check if the existing track check happens too early or too late

4. **Verify state management**:
   - Check if `mic_enabled` variable is being updated correctly
   - Check if there are multiple instances of the variable or state conflicts

## Required Fixes

### Fix 1: Prevent Mic Auto-Enable
- Ensure mic starts disabled when session starts, regardless of saved preferences
- Ensure sending text messages does NOT trigger mic enable
- Only allow mic to be enabled via explicit user click on mic button
- Consider clearing saved mic preference on session start, or preventing restoration

### Fix 2: Enable Audio Output When Mic Unmuted
- Ensure `track_published` event handler is working correctly
- Ensure `session.output.set_audio_enabled(True)` is being called and succeeding
- Fix the existing track detection logic if needed
- Add error handling and logging to diagnose failures
- Consider alternative approaches if event-based detection isn't working

## Testing Requirements

After fixes:
1. Start session → Mic should be OFF
2. Send text message → Mic should stay OFF
3. Click mic button to unmute → Mic turns ON, agent audio output enables
4. Send text message while mic is ON → Mic stays ON, agent responds in text (audio output temporarily disabled for that message)
5. Click mic button to mute → Mic turns OFF, agent audio output disables
6. Send text message while mic is OFF → Mic stays OFF, agent responds in text

## Additional Notes

- The agent uses OpenAI Realtime API which supports both text and audio modalities
- The `custom_text_input_handler` function disables audio output when text is received (this is correct)
- The agent should start with audio output disabled (text-only mode)
- Audio output should only be enabled when mic is unmuted
- The frontend uses LiveKit React components which handle track publishing/unpublishing

## Code References

- Agent entrypoint: `app/agent.py` lines 433-530
- Chat input: `app/components/livekit/agent-control-bar/chat-input.tsx`
- Control bar: `app/components/livekit/agent-control-bar/agent-control-bar.tsx`
- Input controls hook: `app/components/livekit/agent-control-bar/hooks/use-input-controls.ts`

## Expected Outcome

After the fix:
- Mic only enables when user explicitly clicks the mic button
- Sending text messages never enables the mic
- When mic is unmuted, agent audio output enables and agent responds in voice
- When mic is muted, agent audio output disables and agent responds in text only
- All state transitions work smoothly without race conditions





