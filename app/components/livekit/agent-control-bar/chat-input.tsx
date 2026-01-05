import { useEffect, useRef, useState } from 'react';
import { PaperPlaneRightIcon, SpinnerIcon, ImageIcon } from '@phosphor-icons/react/dist/ssr';
import { useRoomContext } from '@livekit/components-react';
import { Button } from '@/components/livekit/button';

interface ChatInputProps {
  chatOpen: boolean;
  isAgentAvailable?: boolean;
  onSend?: (message: string) => void;
  isConnected?: boolean;
  onStartSession?: () => void;
}

export function ChatInput({
  chatOpen,
  isAgentAvailable = false,
  onSend = async () => {},
  isConnected = false,
  onStartSession,
}: ChatInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isSending, setIsSending] = useState(false);
  const [message, setMessage] = useState<string>('');
  const room = useRoomContext();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const messageToSend = message.trim();
    if (!messageToSend) return;

    // Prevent duplicate sends
    if (isSending) return;

    // In text mode (not connected), messages should NOT trigger a call
    // Only the "Start Call" button should initiate a call
    // Messages will be handled by the chatbot API when not connected
    try {
      setIsSending(true);
      // Clear message immediately to prevent duplicate sends
      setMessage('');
      // Send message - will use chatbot API if not connected, LiveKit if connected
      await onSend(messageToSend);
    } catch (error) {
      console.error('Error sending message:', error);
      // If error, restore the message so user can retry
      setMessage(messageToSend);
    } finally {
      setIsSending(false);
    }
  };

  // Just update the message, don't start session on typing
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMessage(e.target.value);
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !room) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert('Image size must be less than 10MB');
      return;
    }

    try {
      setIsSending(true);
      
      // Read file as array buffer
      const arrayBuffer = await file.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      
      // Send file via byte stream on "images" topic
      const stream = await room.publishByteStream('images');
      await stream.write(uint8Array);
      await stream.close();
      
      console.log('Image sent successfully');
    } catch (error) {
      console.error('Error sending image:', error);
      alert('Failed to send image. Please try again.');
    } finally {
      setIsSending(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Allow sending even if not connected (will trigger connection)
  const isDisabled = isSending || message.trim().length === 0;

  // Always focus the input when component mounts or chat opens
  useEffect(() => {
    if (chatOpen) {
      // Small delay to ensure the input is rendered
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [chatOpen]);

  // Also focus on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      inputRef.current?.focus();
    }, 200);
    return () => clearTimeout(timer);
  }, []);

  // Always show the input - no animation hiding
  return (
    <div className="border-input/50 flex w-full items-start overflow-hidden border-b">
      <form
        onSubmit={handleSubmit}
        className="mb-3 flex grow items-end gap-2 rounded-md pl-1 text-sm"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageUpload}
          className="hidden"
          disabled={!chatOpen || (isConnected && !isAgentAvailable)}
        />
        <Button
          size="icon"
          type="button"
          variant="secondary"
          onClick={() => fileInputRef.current?.click()}
          disabled={!chatOpen || (isConnected && !isAgentAvailable) || isSending}
          title="Upload image"
          className="self-start"
        >
          <ImageIcon weight="bold" />
        </Button>
        <input
          autoFocus
          ref={inputRef}
          type="text"
          value={message}
          disabled={false}
          placeholder="Type a message..."
          onChange={handleInputChange}
          className="h-8 flex-1 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 [&::-webkit-search-cancel-button]:hidden [&::-webkit-clear-button]:hidden [&::-ms-clear]:hidden"
          style={{
            WebkitAppearance: 'none',
            MozAppearance: 'textfield',
          }}
        />
        <Button
          size="icon"
          type="submit"
          disabled={isDisabled}
          variant={isDisabled ? 'secondary' : 'primary'}
          title={isSending ? 'Sending...' : 'Send'}
          className="self-start"
        >
          {isSending ? (
            <SpinnerIcon className="animate-spin" weight="bold" />
          ) : (
            <PaperPlaneRightIcon weight="bold" />
          )}
        </Button>
      </form>
    </div>
  );
}
