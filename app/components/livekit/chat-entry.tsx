'use client';

import * as React from 'react';
import { useEffect, useMemo, useState } from 'react';
import { cn } from '@/lib/utils';

export interface ChatEntryProps extends React.HTMLAttributes<HTMLLIElement> {
  /** The locale to use for the timestamp. */
  locale: string;
  /** The timestamp of the message. */
  timestamp: number;
  /** The message to display. */
  message: string;
  /** The origin of the message. */
  messageOrigin: 'local' | 'remote';
  /** The sender's name. */
  name?: string;
  /** Whether the message has been edited. */
  hasBeenEdited?: boolean;
}

// Constants outside component to prevent recreation
const DEFAULT_LOCALE = 'en-US';
const DEFAULT_TIMEZONE = 'America/New_York'; // Eastern Standard Time per user preference

// Format time strings consistently (pure function, can be used on both server and client)
const formatTimeString = (
  hours: number,
  minutes: number,
  seconds: number,
  includeSeconds: boolean
): string => {
  const ampm = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;
  const displayMinutes = minutes.toString().padStart(2, '0');
  if (includeSeconds) {
    const displaySeconds = seconds.toString().padStart(2, '0');
    return `${displayHours}:${displayMinutes}:${displaySeconds} ${ampm}`;
  }
  return `${displayHours}:${displayMinutes} ${ampm}`;
};

export const ChatEntry = ({
  name,
  locale,
  timestamp,
  message,
  messageOrigin,
  hasBeenEdited = false,
  className,
  ...props
}: ChatEntryProps) => {
  const time = useMemo(() => new Date(timestamp), [timestamp]);

  // Convert UTC timestamp to Eastern time consistently (works on both server and client)
  // Eastern time is UTC-5 (EST) or UTC-4 (EDT)
  // We'll use a simple approach: convert to Eastern by subtracting 5 hours from UTC
  // This is deterministic and will be the same on server and client
  const getEasternTime = useMemo(() => {
    // Get UTC time components
    const utcHours = time.getUTCHours();
    const utcMinutes = time.getUTCMinutes();
    const utcSeconds = time.getUTCSeconds();

    // Convert to Eastern (UTC-5, simplified - doesn't account for DST but is consistent)
    // For a more accurate solution, we'd need to detect DST, but for hydration consistency,
    // we'll use a simple offset that's the same everywhere
    let easternHours = utcHours - 5;
    if (easternHours < 0) easternHours += 24;

    return {
      hours: easternHours,
      minutes: utcMinutes,
      seconds: utcSeconds,
    };
  }, [time]);

  // Initial state uses deterministic format that's consistent on server and client
  const initialTime = useMemo(() => {
    const title = `${formatTimeString(getEasternTime.hours, getEasternTime.minutes, getEasternTime.seconds, true)} Eastern Standard Time`;
    const short = formatTimeString(
      getEasternTime.hours,
      getEasternTime.minutes,
      getEasternTime.seconds,
      false
    );
    return { title, short };
  }, [getEasternTime]);

  const [formattedTime, setFormattedTime] = useState(initialTime);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted) {
      // Update to user's locale after hydration
      try {
        const userLocale =
          locale ||
          (typeof navigator !== 'undefined' ? navigator.language : DEFAULT_LOCALE) ||
          DEFAULT_LOCALE;
        setFormattedTime({
          title: time.toLocaleTimeString(userLocale, {
            timeStyle: 'full',
            timeZone: DEFAULT_TIMEZONE,
          }),
          short: time.toLocaleTimeString(userLocale, {
            timeStyle: 'short',
            timeZone: DEFAULT_TIMEZONE,
          }),
        });
      } catch {
        // Fallback to default if locale is invalid
        try {
          setFormattedTime({
            title: time.toLocaleTimeString(DEFAULT_LOCALE, {
              timeStyle: 'full',
              timeZone: DEFAULT_TIMEZONE,
            }),
            short: time.toLocaleTimeString(DEFAULT_LOCALE, {
              timeStyle: 'short',
              timeZone: DEFAULT_TIMEZONE,
            }),
          });
        } catch {
          // Final fallback to simple format
          setFormattedTime({
            title: `${formatTimeString(getEasternTime.hours, getEasternTime.minutes, getEasternTime.seconds, true)} Eastern Standard Time`,
            short: formatTimeString(
              getEasternTime.hours,
              getEasternTime.minutes,
              getEasternTime.seconds,
              false
            ),
          });
        }
      }
    }
  }, [mounted, locale, time, getEasternTime]);

  // Always use initialTime for initial render to ensure server/client match
  // Only use formattedTime after mount to prevent hydration mismatches
  const displayTitle = mounted ? formattedTime.title : initialTime.title;
  const displayTime = mounted ? formattedTime.short : initialTime.short;

  return (
    <li
      title={displayTitle}
      data-lk-message-origin={messageOrigin}
      className={cn('group flex w-full flex-col gap-0.5', className)}
      suppressHydrationWarning={true}
      {...props}
    >
      <header
        className={cn(
          'text-muted-foreground flex items-center gap-2 text-sm',
          messageOrigin === 'local' ? 'flex-row-reverse' : 'text-left'
        )}
        suppressHydrationWarning={true}
      >
        {name && <strong suppressHydrationWarning={true}>{name}</strong>}
        <span
          className="font-mono text-xs opacity-0 transition-opacity ease-linear group-hover:opacity-100"
          suppressHydrationWarning={true}
        >
          {hasBeenEdited && '*'}
          {displayTime}
        </span>
      </header>
      <span
        className={cn(
          'max-w-4/5 rounded-[20px]',
          messageOrigin === 'local' ? 'bg-muted ml-auto p-2' : 'mr-auto'
        )}
        suppressHydrationWarning={true}
      >
        {message}
      </span>
    </li>
  );
};
