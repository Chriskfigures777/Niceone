'use client';

import { type HTMLAttributes, useCallback, useEffect, useState } from 'react';
import { Track } from 'livekit-client';
import { useChat, useRemoteParticipants } from '@livekit/components-react';
import {
  ChatTextIcon,
  GearIcon,
  PhoneDisconnectIcon,
  PhoneIcon,
} from '@phosphor-icons/react/dist/ssr';
import { SettingsModal } from '@/components/app/settings-modal';
import { TrackToggle } from '@/components/livekit/agent-control-bar/track-toggle';
import { Button } from '@/components/livekit/button';
import { Toggle } from '@/components/livekit/toggle';
import { cn } from '@/lib/utils';
import { ChatInput } from './chat-input';
import { UseInputControlsProps, useInputControls } from './hooks/use-input-controls';
import { usePublishPermissions } from './hooks/use-publish-permissions';
import { TrackSelector } from './track-selector';

export interface ControlBarControls {
  leave?: boolean;
  camera?: boolean;
  microphone?: boolean;
  screenShare?: boolean;
  chat?: boolean;
}

export interface AgentControlBarProps extends UseInputControlsProps {
  controls?: ControlBarControls;
  isConnected?: boolean;
  onChatOpenChange?: (open: boolean) => void;
  onDeviceError?: (error: { source: Track.Source; error: Error }) => void;
  onStartSession?: () => void;
  onSendMessage?: (message: string) => Promise<void>; // Optional custom message handler
}

/**
 * A control bar specifically designed for voice assistant interfaces
 */
export function AgentControlBar({
  controls,
  saveUserChoices = true,
  className,
  isConnected = false,
  onDisconnect,
  onDeviceError,
  onChatOpenChange,
  onStartSession,
  onSendMessage: customSendMessage,
  ...props
}: AgentControlBarProps & HTMLAttributes<HTMLDivElement>) {
  const { send } = useChat();
  const participants = useRemoteParticipants();
  const [chatOpen, setChatOpen] = useState(true); // Start with chat open so input is always available
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [userEmail, setUserEmail] = useState<string>('');
  const publishPermissions = usePublishPermissions();

  useEffect(() => {
    // Load email from localStorage
    const storedEmail = localStorage.getItem('calcom_email') || '';
    setUserEmail(storedEmail);
  }, []);

  const handleEmailChange = (email: string) => {
    setUserEmail(email);
    // Notify agent about email change via chat
    if (email && isConnected) {
      send(`My email address is ${email}. Please use this email to filter my appointments.`);
    }
  };
  const {
    micTrackRef,
    cameraToggle,
    microphoneToggle,
    screenShareToggle,
    handleAudioDeviceChange,
    handleVideoDeviceChange,
    handleMicrophoneDeviceSelectError,
    handleCameraDeviceSelectError,
  } = useInputControls({ onDeviceError, saveUserChoices });

  // In call mode, mic should be UNMUTED by default
  // Enable mic when call starts (if not already enabled)
  useEffect(() => {
    if (isConnected && !microphoneToggle.enabled) {
      // Call just started - enable mic by default (unmuted)
      microphoneToggle.toggle(true);
    }
  }, [isConnected]); // Only run when connection state changes

  const handleSendMessage = async (message: string) => {
    // Use custom handler if provided (for chatbot mode), otherwise use LiveKit
    if (customSendMessage) {
      await customSendMessage(message);
    } else {
      await send(message);
    }
  };

  const handleToggleTranscript = useCallback(
    (open: boolean) => {
      setChatOpen(open);
      onChatOpenChange?.(open);
    },
    [onChatOpenChange, setChatOpen]
  );

  const visibleControls = {
    leave: controls?.leave ?? true,
    microphone: controls?.microphone ?? publishPermissions.microphone,
    screenShare: controls?.screenShare ?? publishPermissions.screenShare,
    camera: controls?.camera ?? publishPermissions.camera,
    chat: controls?.chat ?? publishPermissions.data,
  };

  const isAgentAvailable = participants.some((p) => p.isAgent);

  return (
    <div
      aria-label="Voice assistant controls"
      className={cn(
        'bg-background border-input/50 dark:border-muted flex flex-col rounded-[31px] border p-3 drop-shadow-md/3',
        className
      )}
      {...props}
    >
      {/* Chat Input */}
      {visibleControls.chat && (
        <ChatInput
          chatOpen={chatOpen}
          isAgentAvailable={isAgentAvailable || !isConnected}
          onSend={handleSendMessage}
          isConnected={isConnected}
          onStartSession={onStartSession}
        />
      )}

      <div className="flex gap-1">
        <div className="flex grow gap-1">
          {/* Toggle Microphone - only show when connected */}
          {isConnected && visibleControls.microphone && (
            <TrackSelector
              kind="audioinput"
              aria-label="Toggle microphone"
              source={Track.Source.Microphone}
              pressed={microphoneToggle.enabled}
              disabled={microphoneToggle.pending}
              audioTrackRef={micTrackRef}
              onPressedChange={microphoneToggle.toggle}
              onMediaDeviceError={handleMicrophoneDeviceSelectError}
              onActiveDeviceChange={handleAudioDeviceChange}
            />
          )}

          {/* Toggle Camera - only show when connected */}
          {isConnected && visibleControls.camera && (
            <TrackSelector
              kind="videoinput"
              aria-label="Toggle camera"
              source={Track.Source.Camera}
              pressed={cameraToggle.enabled}
              pending={cameraToggle.pending}
              disabled={cameraToggle.pending}
              onPressedChange={cameraToggle.toggle}
              onMediaDeviceError={handleCameraDeviceSelectError}
              onActiveDeviceChange={handleVideoDeviceChange}
            />
          )}

          {/* Toggle Screen Share - only show when connected */}
          {isConnected && visibleControls.screenShare && (
            <TrackToggle
              size="icon"
              variant="secondary"
              aria-label="Toggle screen share"
              source={Track.Source.ScreenShare}
              pressed={screenShareToggle.enabled}
              disabled={screenShareToggle.pending}
              onPressedChange={screenShareToggle.toggle}
            />
          )}

          {/* Toggle Transcript - always visible */}
          <Toggle
            size="icon"
            variant="secondary"
            aria-label="Toggle transcript"
            pressed={chatOpen}
            onPressedChange={handleToggleTranscript}
          >
            <ChatTextIcon weight="bold" />
          </Toggle>

          {/* Settings - always visible */}
          <Toggle
            size="icon"
            variant="secondary"
            aria-label="Settings"
            pressed={settingsOpen}
            onPressedChange={setSettingsOpen}
          >
            <GearIcon weight="bold" />
          </Toggle>
        </div>

        {/* Start Call button when not connected, End Call when connected */}
        {!isConnected && onStartSession ? (
          <Button variant="primary" onClick={onStartSession} className="font-mono">
            <PhoneIcon weight="bold" />
            <span className="hidden md:inline">START CALL</span>
            <span className="inline md:hidden">CALL</span>
          </Button>
        ) : (
          isConnected &&
          visibleControls.leave && (
            <Button variant="destructive" onClick={onDisconnect} className="font-mono">
              <PhoneDisconnectIcon weight="bold" />
              <span className="hidden md:inline">END CALL</span>
              <span className="inline md:hidden">END</span>
            </Button>
          )
        )}
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onEmailChange={handleEmailChange}
        currentEmail={userEmail}
      />
    </div>
  );
}
