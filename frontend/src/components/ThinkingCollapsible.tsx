import { useState, useEffect } from 'react';

interface ThinkingCollapsibleProps {
  steps: { step: string; status: string; summary?: string }[];
  isStreaming: boolean;
}

const STEP_LABELS: Record<string, { running: string; done: string }> = {
  plan: { running: 'Planning...', done: 'Planned' },
  explore: { running: 'Exploring data...', done: 'Explored data' },
  answer: { running: 'Generating answer...', done: 'Generated answer' },
};

function StepLabel({ step, status }: { step: string; status: string }) {
  const labels = STEP_LABELS[step] ?? { running: step, done: step };
  const isRunning = status === 'running' || status === 'started';
  return <span>{isRunning ? labels.running : labels.done}</span>;
}

function Spinner() {
  return (
    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
  );
}

function Checkmark() {
  return (
    <svg className="h-3.5 w-3.5 text-green-500" viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default function ThinkingCollapsible({ steps, isStreaming }: ThinkingCollapsibleProps) {
  const [expanded, setExpanded] = useState(isStreaming);

  useEffect(() => {
    if (isStreaming) setExpanded(true);
    else setExpanded(false);
  }, [isStreaming]);

  const label = isStreaming
    ? 'Thinking...'
    : `Thought for ${steps.length} step${steps.length !== 1 ? 's' : ''}`;

  return (
    <div className="my-2 rounded-lg bg-gray-50 text-sm">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-gray-600 hover:text-gray-900"
      >
        <svg
          className={`h-3 w-3 transition-transform ${expanded ? 'rotate-90' : ''}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
            clipRule="evenodd"
          />
        </svg>
        <span>{label}</span>
        {isStreaming && <Spinner />}
      </button>

      {expanded && (
        <div className="space-y-1 px-3 pb-2">
          {steps.map((s, i) => {
            const isRunning = s.status === 'running' || s.status === 'started';
            return (
              <div key={i} className="flex flex-col gap-0.5 pl-4">
                <div className="flex items-center gap-2">
                  {isRunning ? <Spinner /> : <Checkmark />}
                  <StepLabel step={s.step} status={s.status} />
                </div>
                {s.summary && (
                  <p className="pl-5.5 text-xs text-gray-400">{s.summary}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
