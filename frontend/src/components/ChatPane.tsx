import { useState, useCallback } from 'react';
import { useConversation, useSendMessage } from '../hooks/useConversations';
import { useSSE } from '../hooks/useSSE';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

export default function ChatPane({ conversationId }: { conversationId: string | null }) {
  const { data: conversation, isLoading, isError } = useConversation(conversationId);
  const sendMessage = useSendMessage();
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const { steps, isStreaming, isComplete, reset } = useSSE(conversationId, streaming);

  // When SSE completes, only clear optimistic state once refetched data has the real response.
  // This prevents a flash of empty content between "done" and the refetch completing.
  const lastMsg = conversation?.messages?.[conversation.messages.length - 1];
  const hasRealResponse = lastMsg?.role === 'assistant' && !!lastMsg.content;
  if (isComplete && pendingMessage !== null && hasRealResponse) {
    setPendingMessage(null);
    setStreaming(false);
    reset();
  }

  const handleSend = useCallback(
    (content: string) => {
      if (!conversationId) return;
      setSendError(null);
      setPendingMessage(content);
      setStreaming(true);
      sendMessage.mutate(
        { conversationId, content },
        {
          onError: () => {
            setSendError('Failed to send message. Try again.');
            setPendingMessage(null);
            setStreaming(false);
          },
        }
      );
    },
    [conversationId, sendMessage]
  );

  if (!conversationId) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-500">
        Select or create a conversation
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-500">
        Loading conversation...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-1 items-center justify-center text-red-400">
        Failed to load conversation
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      {sendError && (
        <div className="flex items-center justify-between bg-red-900/30 px-4 py-2 text-sm text-red-400">
          <span>{sendError}</span>
          <button
            onClick={() => setSendError(null)}
            className="ml-2 font-medium hover:text-red-200"
          >
            Dismiss
          </button>
        </div>
      )}
      <MessageList
        messages={conversation?.messages ?? []}
        pendingUserMessage={pendingMessage ?? undefined}
        streamingSteps={streaming ? steps : undefined}
        isStreaming={isStreaming}
      />
      <MessageInput onSend={handleSend} disabled={sendMessage.isPending || streaming} />
    </div>
  );
}
