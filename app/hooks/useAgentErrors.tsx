import { useEffect } from 'react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { toastAlert } from '@/components/livekit/alert-toast';

export function useAgentErrors() {
  const agent = useAgent();
  const { isConnected, end } = useSessionContext();

  useEffect(() => {
    console.log('[useAgentErrors] Agent state:', {
      state: agent.state,
      isConnected,
      failureReasons: agent.failureReasons,
    });

    // Only show error for actual failures, but don't end session automatically
    // Allow user to continue with text chat even if agent hasn't joined yet
    if (isConnected && agent.state === 'failed') {
      const reasons = agent.failureReasons;
      console.error('[useAgentErrors] Agent failed:', reasons);

      // Show a non-blocking warning instead of ending the session
      toastAlert({
        title: 'Agent connection issue',
        description: (
          <>
            {reasons.length > 1 && (
              <ul className="list-inside list-disc">
                {reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            {reasons.length === 1 && <p className="w-full">{reasons[0]}</p>}
            <p className="mt-2 w-full">
              Make sure the agent server is running. Text chat may still work.
            </p>
          </>
        ),
      });

      // Don't automatically end the session - let user continue
    }
  }, [agent, isConnected, end]);
}
