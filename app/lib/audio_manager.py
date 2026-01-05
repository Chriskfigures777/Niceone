"""Audio session management for mic mute/unmute events - simplified mode switching"""
import logging
import asyncio
from livekit import rtc
from livekit.agents import AgentSession

logger = logging.getLogger("agent-Alex-2f2")


class AudioSessionManager:
    """
    Manages audio session state based on mic mute/unmute events.
    
    Key behavior:
    - Mute button ONLY mutes the user's mic (doesn't disable agent audio)
    - When mic is muted: Switch to "ChatGPT mode" (text conversation, agent can still speak)
    - When mic is unmuted: Switch to "call mode" (voice conversation)
    - Agent audio is ALWAYS enabled - user can always hear the agent
    - Text input works in both modes (default LiveKit behavior)
    """
    
    def __init__(self, session: AgentSession):
        self.session = session
        self.mic_enabled = False
        self._greeting_sent = False  # Track if greeting has been sent
    
    def handle_mic_unmuted(self) -> None:
        """
        Handle microphone being unmuted - switch to "call mode" (voice conversation).
        
        Agent audio stays enabled - user can hear the agent.
        Mic is now active - user can speak.
        
        NOTE: In call mode, mic is UNMUTED by default, so this is called when:
        - User manually unmutes their mic (after muting it)
        - Mic track is first detected when call starts
        """
        if not self.mic_enabled:
            self.mic_enabled = True
            logger.info("🎤 Microphone unmuted - CALL MODE active (voice conversation)")
            try:
                # Ensure audio output is enabled (should always be enabled)
                self.session.output.set_audio_enabled(True)
                logger.info("✓ Agent audio enabled - user can hear the agent")
                
                # Only trigger greeting if this is a manual unmute (not initial call start)
                # If greeting hasn't been sent, this might be the first interaction
                # But don't auto-greet - let user speak first in call mode
                # The greeting will be sent only if explicitly needed
            except Exception as e:
                logger.error(f"✗ Could not enable audio output: {e}", exc_info=True)
        else:
            logger.debug("Mic already enabled")
    
    def handle_mic_muted(self) -> None:
        """
        Handle microphone being muted - switch to "ChatGPT mode" (text conversation).
        
        IMPORTANT: This ONLY mutes the user's mic - agent audio stays enabled.
        User can still hear the agent speak, but can only communicate via text.
        Agent will respond in text mode (but can still speak if needed).
        """
        if self.mic_enabled:
            self.mic_enabled = False
            logger.info("🔇 Microphone muted - switching to CHATGPT MODE (text conversation)")
            logger.info("✓ Agent audio remains enabled - user can still hear the agent")
            logger.info("✓ User can communicate via text input")
            # DO NOT disable audio output - agent can still speak
            # DO NOT interrupt - let agent finish speaking if it's talking
            # Just mark that mic is muted, so we know we're in text mode
        else:
            logger.debug("Mic already muted - already in ChatGPT mode")
    
    async def _trigger_audio_greeting(self) -> None:
        """Trigger an audio greeting when mic is first unmuted"""
        try:
            # Ensure audio output is enabled
            self.session.output.set_audio_enabled(True)
            # Very short delay to ensure audio output is fully enabled and ready
            await asyncio.sleep(0.5)
            # Verify audio is still enabled before triggering response
            if self.mic_enabled:
                # Trigger a response that will make the agent speak immediately
                # Using instructions instead of user_input to avoid adding to chat history
                logger.info("Triggering audio greeting - agent should start speaking now")
                self.session.generate_reply(instructions="Greet the user warmly and let them know you're ready to help")
                logger.info("✓ Audio greeting triggered - agent should be speaking")
            else:
                logger.debug("Mic was muted before greeting could be triggered")
        except Exception as e:
            logger.error(f"Error triggering audio greeting: {e}", exc_info=True)
    
    async def _trigger_audio_acknowledgment(self) -> None:
        """Trigger an audio acknowledgment when mic is unmuted again"""
        try:
            # Ensure audio output is enabled
            self.session.output.set_audio_enabled(True)
            # Very short delay to ensure audio output is fully enabled and ready
            await asyncio.sleep(0.5)
            # Verify audio is still enabled before triggering response
            if self.mic_enabled:
                # Trigger a response that acknowledges readiness to continue
                # Using instructions to avoid adding to chat history
                logger.info("Triggering audio acknowledgment - agent should start speaking now")
                self.session.generate_reply(instructions="Acknowledge that you're ready to continue the conversation")
                logger.info("✓ Audio acknowledgment triggered - agent should be speaking")
            else:
                logger.debug("Mic was muted before acknowledgment could be triggered")
        except Exception as e:
            logger.error(f"Error triggering audio acknowledgment: {e}", exc_info=True)
    
    def check_existing_mic_tracks(self, room: rtc.Room) -> None:
        """
        Check for existing mic tracks when call starts.
        
        IMPORTANT: In call mode, mic should be UNMUTED by default.
        If mic track exists, we're in call mode - enable audio and mark mic as enabled.
        User can still mute/unmute their mic, but default is unmuted.
        """
        try:
            logger.info("Checking for existing microphone tracks...")
            found_mic = False
            for participant in room.remote_participants.values():
                logger.info(f"Checking participant: {participant.identity}, tracks: {len(participant.track_publications)}")
                for publication in participant.track_publications.values():
                    track_info = f"kind={publication.track.kind if publication.track else 'None'}, source={publication.source}"
                    logger.info(f"  Track: {track_info}")
                    if (publication.track and 
                        publication.track.kind == rtc.TrackKind.KIND_AUDIO and 
                        publication.source == rtc.TrackSource.SOURCE_MICROPHONE):
                        logger.info("✓ Found existing microphone track - CALL MODE active, mic is UNMUTED by default")
                        # In call mode, mic is UNMUTED by default
                        # Mark as enabled but don't trigger greeting - let user speak first
                        if not self.mic_enabled:
                            self.mic_enabled = True
                            logger.info("✓ Mic marked as enabled (unmuted) - user can speak")
                            # Ensure audio output is enabled (agent can speak)
                            try:
                                self.session.output.set_audio_enabled(True)
                                logger.info("✓ Agent audio enabled - ready for voice conversation")
                            except Exception as e:
                                logger.warning(f"Could not enable audio output: {e}")
                        found_mic = True
                        break
                if found_mic:
                    break
            if not found_mic:
                logger.info("No existing microphone tracks found - starting in CHATGPT MODE (text conversation)")
                logger.info("✓ Agent audio enabled - user can hear the agent")
                logger.info("✓ User can communicate via text input")
                # Ensure audio is enabled (agent can always speak)
                try:
                    self.session.output.set_audio_enabled(True)
                    logger.debug("✓ Confirmed audio output is enabled - agent can speak")
                except Exception as e:
                    logger.warning(f"Could not confirm audio is enabled: {e}")
        except Exception as e:
            logger.error(f"Error checking for existing mic tracks: {e}", exc_info=True)

