'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'motion/react';
import {
  type ReceivedMessage,
  useChat,
  useSessionContext,
  useSessionMessages,
} from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { ChatTranscript } from '@/components/app/chat-transcript';
import { PreConnectMessage } from '@/components/app/preconnect-message';
import { TileLayout } from '@/components/app/tile-layout';
import {
  AgentControlBar,
  type ControlBarControls,
} from '@/components/livekit/agent-control-bar/agent-control-bar';
import { ChatbotClient } from '@/lib/chatbot_client';
import { cn } from '@/lib/utils';
import { ScrollArea } from '../livekit/scroll-area/scroll-area';

const MotionBottom = motion.create('div');

const BOTTOM_VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut',
  },
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'from-background pointer-events-none h-4 bg-linear-to-b to-transparent',
        top && 'bg-linear-to-b',
        bottom && 'bg-linear-to-t',
        className
      )}
    />
  );
}

interface SessionViewProps {
  appConfig: AppConfig;
  onStartSession?: () => void;
  isConnected?: boolean;
}

export const SessionView = ({
  appConfig,
  onStartSession,
  isConnected: isConnectedProp,
  ...props
}: React.ComponentProps<'section'> & SessionViewProps) => {
  const session = useSessionContext();
  const { messages: livekitMessages } = useSessionMessages(session);
  const { send: livekitSend } = useChat();
  const [chatOpen, setChatOpen] = useState(true); // Always show chat by default
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const isConnected = isConnectedProp ?? session.isConnected;

  // Local message state for text mode (when not connected)
  // Load from localStorage on mount
  const [textModeMessages, setTextModeMessages] = useState<ReceivedMessage[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('conversation_messages');
        if (stored) {
          const parsed = JSON.parse(stored);
          console.log(`📦 Loaded ${parsed.length} messages from localStorage`);
          return parsed;
        }
      } catch (error) {
        console.error('Error loading messages from localStorage:', error);
      }
    }
    return [];
  });

  // Save to localStorage whenever messages change
  useEffect(() => {
    if (typeof window !== 'undefined' && textModeMessages.length > 0) {
      try {
        localStorage.setItem('conversation_messages', JSON.stringify(textModeMessages));
        console.log(`💾 Saved ${textModeMessages.length} messages to localStorage`);
      } catch (error) {
        console.error('Error saving messages to localStorage:', error);
      }
    }
  }, [textModeMessages]);

  // Use chatbot client when not connected
  const chatbotClient = useMemo(() => new ChatbotClient('default_user', undefined), []);

  // Merge LiveKit messages with text mode messages
  // Always show text mode messages - they represent the conversation history
  const allMessages = useMemo(() => {
    // Combine text mode messages (from before call) with LiveKit messages (from call)
    // Text mode messages come first, then LiveKit messages
    // This ensures conversation continuity when switching to call mode
    const combined = [...textModeMessages, ...livekitMessages];

    // Remove duplicates based on message ID
    const uniqueMessages = combined.filter(
      (msg, index, self) => index === self.findIndex((m) => m.id === msg.id)
    );

    // Sort by timestamp to maintain chronological order
    return uniqueMessages.sort((a, b) => a.timestamp - b.timestamp);
  }, [livekitMessages, textModeMessages]);

  // NOTE: We do NOT re-send text mode messages when the call starts
  // The agent already has full context from Mem0 memories retrieved in on_enter()
  // Re-sending messages would cause duplicate responses
  // The messages are already stored in Mem0 and will be retrieved by the agent automatically

  // Handle starting a session - sync conversation history to Mem0 first
  const handleStartSession = async () => {
    if (!isConnected && chatbotClient) {
      // Sync conversation history to Mem0 before starting the call
      // This ensures the agent has access to all text mode conversation history
      try {
        // Convert textModeMessages to ChatbotClient format and set it
        const conversationHistory = textModeMessages
          .filter((msg) => msg.type === 'chatMessage' && msg.from)
          .map((msg) => ({
            role: (msg.from?.isLocal ? 'user' : 'assistant') as 'user' | 'assistant',
            content: msg.message,
          }));

        if (conversationHistory.length > 0) {
          chatbotClient.setConversationHistory(conversationHistory);
          console.log(
            `Syncing ${conversationHistory.length} messages to Mem0 before starting call...`
          );
        } else {
          console.log('No conversation history to sync');
        }

        const syncResult = await chatbotClient.syncToMem0();
        if (syncResult.success) {
          console.log('✓ Conversation history synced successfully:', syncResult.message);
        } else {
          const errorMsg = syncResult.error || 'Unknown error';
          console.warn('⚠ Failed to sync conversation history to Mem0:', errorMsg);
          console.warn(
            '⚠ The call will still start - agent will retrieve memories from Mem0 when needed'
          );
        }
      } catch (error) {
        const errorMsg =
          error instanceof Error
            ? error.message
            : typeof error === 'string'
              ? error
              : JSON.stringify(error) || 'Unknown error';
        console.error('Error syncing conversation history:', {
          error: errorMsg,
          errorType: error instanceof Error ? error.constructor.name : typeof error,
        });
        console.warn(
          '⚠ The call will still start - agent will retrieve memories from Mem0 when needed'
        );
      }
    }

    // Start the session (don't wait for sync to complete)
    if (onStartSession) {
      onStartSession();
    }
  };

  // Helper function to create a ReceivedMessage-like object for text mode
  const createTextModeMessage = (
    message: string,
    isLocal: boolean,
    id?: string
  ): ReceivedMessage => {
    const timestamp = Date.now();
    return {
      id: id || `text-mode-${timestamp}-${Math.random()}`,
      timestamp,
      message,
      from: {
        identity: isLocal ? 'user' : 'assistant',
        name: isLocal ? 'You' : 'Assistant',
        isLocal,
      },
      type: 'chatMessage',
    } as ReceivedMessage;
  };

  // Intercept message sending - use chatbot API when not connected
  const handleSendMessage = async (message: string) => {
    if (isConnected) {
      // Use LiveKit when connected - only send once
      await livekitSend(message);
    } else {
      // Use chatbot API when not connected
      // Add user message to local state immediately
      const userMessage = createTextModeMessage(message, true);
      setTextModeMessages((prev) => [...prev, userMessage]);

      try {
        // DO NOT send via LiveKit when not connected - this causes duplicates
        // Only use the chatbot API for text mode

        // Get chatbot response
        const response = await chatbotClient.sendMessage(message);

        // Add assistant response to local state
        const assistantMessage = createTextModeMessage(response.response, false);
        setTextModeMessages((prev) => [...prev, assistantMessage]);

        // DO NOT send assistant response via LiveKit - it's not connected yet
      } catch (error) {
        console.error('Error sending message to chatbot:', error);
        // Remove the user message if chatbot failed
        setTextModeMessages((prev) => prev.filter((msg) => msg.id !== userMessage.id));

        // Show error message
        const errorMessage = createTextModeMessage(
          'Sorry, I encountered an error. Please try again.',
          false
        );
        setTextModeMessages((prev) => [...prev, errorMessage]);
      }
    }
  };

  const controls: ControlBarControls = {
    leave: true,
    microphone: true,
    chat: appConfig.supportsChatInput,
    camera: appConfig.supportsVideoInput,
    screenShare: appConfig.supportsVideoInput,
  };

  // Track previous connection state to detect when call ends
  const prevConnectedRef = useRef(isConnected);
  // Track which LiveKit message IDs we've already saved to avoid duplicates
  const savedLiveKitMessageIdsRef = useRef<Set<string>>(new Set());

  // Auto-scroll when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [allMessages]);

  // Save LiveKit call messages to text mode state as they come in (to preserve them when call ends)
  useEffect(() => {
    if (isConnected && livekitMessages.length > 0) {
      // Save any new LiveKit messages that we haven't saved yet
      const newMessages = livekitMessages.filter(
        (msg) => !savedLiveKitMessageIdsRef.current.has(msg.id)
      );

      if (newMessages.length > 0) {
        console.log(`💾 Saving ${newMessages.length} call messages to preserve them`);
        // Mark these messages as saved
        newMessages.forEach((msg) => savedLiveKitMessageIdsRef.current.add(msg.id));

        setTextModeMessages((prev) => {
          // Combine existing messages with new call messages, remove duplicates, sort by timestamp
          const combined = [...prev, ...newMessages];
          const unique = combined.filter(
            (msg, index, self) => index === self.findIndex((m) => m.id === msg.id)
          );
          return unique.sort((a, b) => a.timestamp - b.timestamp);
        });
      }
    }
  }, [isConnected, livekitMessages]);

  // Also preserve messages when call ends (backup in case some weren't saved)
  useEffect(() => {
    const wasConnected = prevConnectedRef.current;
    const isNowConnected = isConnected;

    // When call ends (was connected, now not connected), save any remaining LiveKit messages
    if (wasConnected && !isNowConnected && livekitMessages.length > 0) {
      const unsavedMessages = livekitMessages.filter(
        (msg) => !savedLiveKitMessageIdsRef.current.has(msg.id)
      );

      if (unsavedMessages.length > 0) {
        console.log(`💾 Call ended - preserving ${unsavedMessages.length} remaining call messages`);
        unsavedMessages.forEach((msg) => savedLiveKitMessageIdsRef.current.add(msg.id));

        setTextModeMessages((prev) => {
          const combined = [...prev, ...unsavedMessages];
          const unique = combined.filter(
            (msg, index, self) => index === self.findIndex((m) => m.id === msg.id)
          );
          return unique.sort((a, b) => a.timestamp - b.timestamp);
        });
      }
    }

    // Update previous connection state
    prevConnectedRef.current = isConnected;
  }, [isConnected, livekitMessages]);

  return (
    <section className="bg-background relative z-10 h-full w-full overflow-hidden" {...props}>
      {/* Chat Transcript */}
      <div
        className={cn(
          'fixed inset-0 grid grid-cols-1 grid-rows-1',
          !chatOpen && 'pointer-events-none'
        )}
      >
        <Fade top className="absolute inset-x-4 top-0 h-40" />
        <ScrollArea ref={scrollAreaRef} className="px-4 pt-40 pb-[150px] md:px-6 md:pb-[200px]">
          <ChatTranscript
            hidden={!chatOpen}
            messages={allMessages}
            className="mx-auto max-w-2xl space-y-3 transition-opacity duration-300 ease-out"
          />
        </ScrollArea>
      </div>

      {/* Tile Layout */}
      <TileLayout chatOpen={chatOpen} />

      {/* Bottom */}
      <MotionBottom
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="fixed inset-x-3 bottom-0 z-50 md:inset-x-12"
      >
        {appConfig.isPreConnectBufferEnabled && (
          <PreConnectMessage messages={allMessages} className="pb-4" />
        )}
        <div className="bg-background relative mx-auto max-w-2xl pb-3 md:pb-12">
          <Fade bottom className="absolute inset-x-0 top-0 h-4 -translate-y-full" />
          <AgentControlBar
            controls={controls}
            isConnected={isConnected}
            onDisconnect={session.end}
            onChatOpenChange={setChatOpen}
            onStartSession={handleStartSession}
            onSendMessage={handleSendMessage}
          />
        </div>
      </MotionBottom>
    </section>
  );
};
