import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export interface StepState {
  step: string;
  status: string;
  summary?: string;
}

interface SSEEvent {
  step: string;
  status?: string;
  summary?: string;
}

export function useSSE(conversationId: string | null, enabled: boolean) {
  const [steps, setSteps] = useState<StepState[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const queryClient = useQueryClient();

  const reset = useCallback(() => {
    setSteps([]);
    setIsComplete(false);
    setIsStreaming(false);
  }, []);

  useEffect(() => {
    if (!conversationId || !enabled) {
      return;
    }

    reset();
    const controller = new AbortController();
    abortRef.current = controller;

    async function stream() {
      const token = localStorage.getItem('token');
      const baseUrl = import.meta.env.VITE_API_URL || '';

      let response: Response;
      try {
        response = await fetch(
          `${baseUrl}/api/conversations/${conversationId}/stream`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
            signal: controller.signal,
          }
        );
      } catch {
        return;
      }

      if (!response.ok || !response.body) {
        return;
      }

      setIsStreaming(true);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data:')) continue;

            const jsonStr = trimmed.slice(5).trim();
            if (!jsonStr) continue;

            let event: SSEEvent;
            try {
              event = JSON.parse(jsonStr);
            } catch {
              continue;
            }

            if (event.step === 'done') {
              setIsComplete(true);
              setIsStreaming(false);
              queryClient.invalidateQueries({
                queryKey: ['conversation', conversationId],
              });
              queryClient.invalidateQueries({
                queryKey: ['conversations'],
              });
              return;
            }

            setSteps((prev) => {
              const idx = prev.findIndex((s) => s.step === event.step);
              const updated: StepState = {
                step: event.step,
                status: event.status ?? 'running',
                summary: event.summary,
              };
              if (idx >= 0) {
                const next = [...prev];
                next[idx] = updated;
                return next;
              }
              return [...prev, updated];
            });
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return;
      } finally {
        setIsStreaming(false);
      }
    }

    stream();

    return () => {
      controller.abort();
      abortRef.current = null;
    };
  }, [conversationId, enabled, queryClient, reset]);

  return { steps, isComplete, isStreaming, reset };
}
