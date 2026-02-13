import type { Message } from '../types';
import type { StepState } from '../hooks/useSSE';
import AssistantMessage from './AssistantMessage';
import ThinkingCollapsible from './ThinkingCollapsible';

interface MessageListProps {
  messages: Message[];
  pendingUserMessage?: string;
  streamingSteps?: StepState[];
  isStreaming?: boolean;
}

export default function MessageList({
  messages,
  pendingUserMessage,
  streamingSteps,
  isStreaming,
}: MessageListProps) {
  const hasContent = messages.length > 0 || pendingUserMessage;

  if (!hasContent) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-400">
        Ask a question about your data
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-4 overflow-y-auto p-4">
      {messages.map((msg) =>
        msg.role === 'user' ? (
          <div key={msg.id} className="flex justify-end">
            <div className="max-w-lg rounded-lg bg-blue-600 px-4 py-2 text-white">
              {msg.content}
            </div>
          </div>
        ) : (
          <div key={msg.id} className="flex justify-start">
            <AssistantMessage message={msg} />
          </div>
        )
      )}

      {pendingUserMessage && (
        <div className="flex justify-end">
          <div className="max-w-lg rounded-lg bg-blue-600 px-4 py-2 text-white">
            {pendingUserMessage}
          </div>
        </div>
      )}

      {streamingSteps && (
        <div className="flex justify-start">
          <div className="max-w-lg rounded-lg bg-gray-100 px-4 py-2 text-gray-900">
            <ThinkingCollapsible steps={streamingSteps} isStreaming={isStreaming ?? false} />
          </div>
        </div>
      )}
    </div>
  );
}
