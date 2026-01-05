'use client';

import { useState, useEffect } from 'react';
import { XIcon } from '@phosphor-icons/react/dist/ssr';
import { Button } from '@/components/livekit/button';
import { cn } from '@/lib/utils';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEmailChange: (email: string) => void;
  currentEmail: string;
}

export function SettingsModal({ isOpen, onClose, onEmailChange, currentEmail }: SettingsModalProps) {
  const [email, setEmail] = useState(currentEmail);

  useEffect(() => {
    setEmail(currentEmail);
  }, [currentEmail]);

  const handleSave = () => {
    onEmailChange(email);
    // Store in localStorage
    if (email) {
      localStorage.setItem('calcom_email', email);
    } else {
      localStorage.removeItem('calcom_email');
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background border-input/50 dark:border-muted relative w-full max-w-md rounded-lg border p-6 shadow-lg">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
          aria-label="Close settings"
        >
          <XIcon weight="bold" size={20} />
        </button>
        
        <h2 className="text-lg font-semibold mb-4">Cal.com Settings</h2>
        
        <div className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-2">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your-email@example.com"
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              This email will be used to filter and create appointments in Cal.com
            </p>
          </div>
          
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleSave}>
              Save
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}





