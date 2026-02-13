import { useState, useCallback } from 'react';
import { useConversation, useSendMessage } from '../hooks/useConversations';
import { useSSE } from '../hooks/useSSE';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

export default function ChatPane({ conversationId }: { conversationId: string | null }) {
  const { data: conversation } = useConversation(conversationId);
  const sendMessage = useSendMessage();
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);

  const { steps, isStreaming, isComplete, reset } = useSSE(conversationId, streaming);

  // When SSE completes, clear the optimistic state
  if (isComplete && pendingMessage !== null) {
    setPendingMessage(null);
    setStreaming(false);
    reset();
  }

  const handleSend = useCallback(
    (content: string) => {
      if (!conversationId) return;
      setPendingMessage(content);
      setStreaming(true);
      sendMessage.mutate({ conversationId, content });
    },
    [conversationId, sendMessage]
  );

  if (!conversationId) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-400">
        Select or create a conversation
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
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
