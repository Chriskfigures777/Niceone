'use client';

import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { SessionView } from '@/components/app/session-view';

const MotionSessionView = motion.create(SessionView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start } = useSessionContext();

  // Always show SessionView - it handles both connected (call) and disconnected (chatbot) modes
  return (
    <AnimatePresence mode="wait">
      <MotionSessionView 
        key="session-view" 
        {...VIEW_MOTION_PROPS} 
        appConfig={appConfig}
        onStartSession={start}
        isConnected={isConnected}
      />
    </AnimatePresence>
  );
}
