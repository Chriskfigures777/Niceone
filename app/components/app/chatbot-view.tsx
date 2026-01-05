'use client';

import React, { useEffect, useRef, useState } from 'react';
import type { ReceivedMessage } from '@livekit/components-react';
import { PaperPlaneRightIcon, SpinnerIcon } from '@phosphor-icons/react/dist/ssr';
import { Button } from '@/components/livekit/button';
import { ChatbotClient } from '@/lib/chatbot_client';
import { cn } from '@/lib/utils';
import { ScrollArea } from '../livekit/scroll-area/scroll-area';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatbotViewProps {
  userId?: string;
  email?: string;
  previousMessages?: ReceivedMessage[];
  onStartCall?: () => void;
}

export function ChatbotView({
  userId = 'default_user',
  email,
  previousMessages = [],
  onStartCall,
}: ChatbotViewProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [chatbotClient] = useState(() => new ChatbotClient(userId, email));
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Convert previous LiveKit messages to chatbot messages
  useEffect(() => {
    if (previousMessages.length > 0 && messages.length === 0) {
      const convertedMessages: ChatMessage[] = previousMessages
        .filter((msg) => msg.type === 'chatMessage' && msg.message && msg.from)
        .map((msg) => ({
          role: msg.from?.isLocal ? 'user' : 'assistant',
          content: msg.message || '',
          timestamp: new Date(msg.timestamp || Date.now()),
        }));

      if (convertedMessages.length > 0) {
        setMessages(convertedMessages);
        chatbotClient.setConversationHistory(
          convertedMessages.map((m) => ({ role: m.role, content: m.content }))
        );
      }
    }
  }, [previousMessages, chatbotClient, messages.length]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      // Use requestAnimationFrame for smoother scrolling
      requestAnimationFrame(() => {
        if (scrollAreaRef.current) {
          scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
        }
      });
    }
  }, [messages]);

  const handleSendMessage = async (message: string) => {
    if (!message.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    // Optimistic UI update - add user message immediately
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Clear input immediately for better UX
    if (inputRef.current) {
      inputRef.current.value = '';
    }

    try {
      const response = await chatbotClient.sendMessage(message);

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      // Focus input for next message
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
  };

  return (
    <section className="bg-background relative z-10 flex h-full w-full flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-background/95 supports-[backdrop-filter]:bg-background/60 border-b px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Chat Mode</h2>
            <p className="text-muted-foreground text-sm">
              Continue your conversation - all context is remembered
            </p>
          </div>
          {onStartCall && (
            <button
              onClick={onStartCall}
              className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-md px-4 py-2 transition-colors"
            >
              Start Call
            </button>
          )}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea ref={scrollAreaRef} className="h-full px-4 py-6">
          <div className="mx-auto max-w-2xl space-y-4">
            {messages.length === 0 && (
              <div className="text-muted-foreground py-12 text-center">
                <p className="mb-2 text-lg">Chat Mode Active</p>
                <p className="text-sm">
                  The call has ended, but you can continue chatting here.
                  <br />
                  All conversation history is remembered.
                </p>
              </div>
            )}
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={cn('flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                <div
                  className={cn(
                    'max-w-[80%] rounded-lg px-4 py-2',
                    msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'
                  )}
                >
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  <p className="mt-1 text-xs opacity-70">{msg.timestamp.toLocaleTimeString()}</p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg px-4 py-2">
                  <p className="text-muted-foreground text-sm">Thinking...</p>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Chat Input */}
      <div className="bg-background/95 supports-[backdrop-filter]:bg-background/60 border-t px-4 py-4 backdrop-blur">
        <div className="mx-auto max-w-2xl">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const input = e.currentTarget.querySelector('input') as HTMLInputElement;
              if (input?.value.trim()) {
                handleSendMessage(input.value);
              }
            }}
            className="flex items-center gap-2"
          >
            <input
              ref={inputRef}
              type="text"
              disabled={isLoading}
              placeholder="Type your message..."
              autoFocus
              className="border-input bg-background focus:ring-ring h-10 flex-1 rounded-md border px-4 text-sm focus:ring-2 focus:outline-none disabled:opacity-50"
            />
            <Button type="submit" disabled={isLoading} size="icon" variant="primary">
              {isLoading ? (
                <SpinnerIcon className="animate-spin" weight="bold" />
              ) : (
                <PaperPlaneRightIcon weight="bold" />
              )}
            </Button>
          </form>
        </div>
      </div>
    </section>
  );
}
