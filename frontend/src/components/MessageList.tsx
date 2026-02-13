import type { Message } from '../types';
import AssistantMessage from './AssistantMessage';

export default function MessageList({ messages }: { messages: Message[] }) {
  if (messages.length === 0) {
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
    </div>
  );
}
