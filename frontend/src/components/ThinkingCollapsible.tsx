import { useState, useEffect } from 'react';
import type { PipelineData } from '../types';

interface StreamingProps {
  steps: { step: string; status: string; summary?: string }[];
  isStreaming: boolean;
  pipelineData?: never;
}

interface PersistedProps {
  pipelineData: PipelineData;
  steps?: never;
  isStreaming?: never;
}

type ThinkingCollapsibleProps = StreamingProps | PersistedProps;

const STEP_LABELS: Record<string, { running: string; done: string; info: string }> = {
  plan: { running: 'Planning...', done: 'Planned', info: 'Analyzes your question and decides what data to look for' },
  explore: { running: 'Exploring data...', done: 'Explored data', info: 'Queries the database to gather relevant data' },
  answer: { running: 'Generating answer...', done: 'Generated answer', info: 'Formats the results into text, tables, or charts' },
};

function InfoIcon({ tooltip }: { tooltip: string }) {
  return (
    <span
      title={tooltip}
      className="ml-1 inline-flex h-3.5 w-3.5 cursor-help items-center justify-center rounded-full bg-gray-600 text-[9px] font-bold text-gray-400"
    >
      i
    </span>
  );
}

function StepLabel({ step, status }: { step: string; status: string }) {
  const labels = STEP_LABELS[step] ?? { running: step, done: step, info: '' };
  const isRunning = status === 'running' || status === 'started';
  return (
    <span className="inline-flex items-center">
      {isRunning ? labels.running : labels.done}
      {labels.info && <InfoIcon tooltip={labels.info} />}
    </span>
  );
}

function Spinner() {
  return (
    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
  );
}

function Checkmark() {
  return (
    <svg className="h-3.5 w-3.5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default function ThinkingCollapsible(props: ThinkingCollapsibleProps) {
  const isPersisted = 'pipelineData' in props && !!props.pipelineData;
  const isStreaming = isPersisted ? false : (props as StreamingProps).isStreaming;

  const [expanded, setExpanded] = useState(isStreaming);

  useEffect(() => {
    if (!isPersisted) {
      if (isStreaming) setExpanded(true);
      else setExpanded(false);
    }
  }, [isStreaming, isPersisted]);

  if (isPersisted) {
    const { pipelineData } = props as PersistedProps;
    const stepCount = pipelineData.steps.length;
    const label = `Analyzed in ${stepCount} step${stepCount !== 1 ? 's' : ''}`;

    return (
      <div className="my-2 rounded-lg bg-gray-700/50 text-sm">
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-gray-400 hover:text-gray-200"
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
        </button>

        {expanded && (
          <div className="space-y-1 px-3 pb-2">
            {pipelineData.steps.map((s, i) => (
              <div key={i} className="flex flex-col gap-0.5 pl-4">
                <div className="flex items-center gap-2">
                  {s.status === 'completed' ? <Checkmark /> : <Spinner />}
                  <StepLabel step={s.name} status={s.status} />
                </div>
                {s.summary && (
                  <p className="pl-5.5 text-xs text-gray-400">{s.summary}</p>
                )}
                {s.query_strategy && (
                  <p className="pl-5.5 text-xs text-gray-500">
                    Strategy: {s.query_strategy}
                  </p>
                )}
                {s.queries && s.queries.length > 0 && (
                  <div className="pl-5.5 space-y-0.5">
                    {s.queries.map((q, qi) => (
                      <code key={qi} className="block text-xs text-gray-500 font-mono truncate">
                        {q}
                      </code>
                    ))}
                  </div>
                )}
                {s.exploration_notes && (
                  <p className="pl-5.5 text-xs text-gray-500">{s.exploration_notes}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Streaming mode
  const { steps } = props as StreamingProps;
  const label = isStreaming
    ? 'Thinking...'
    : `Thought for ${steps.length} step${steps.length !== 1 ? 's' : ''}`;

  return (
    <div className="my-2 rounded-lg bg-gray-700/50 text-sm">
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
