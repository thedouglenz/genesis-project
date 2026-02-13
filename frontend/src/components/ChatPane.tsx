import { useConversation, useSendMessage } from '../hooks/useConversations';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

export default function ChatPane({ conversationId }: { conversationId: string | null }) {
  const { data: conversation } = useConversation(conversationId);
  const sendMessage = useSendMessage();

  if (!conversationId) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-400">
        Select or create a conversation
      </div>
    );
  }

  const handleSend = (content: string) => {
    sendMessage.mutate({ conversationId, content });
  };

  return (
    <div className="flex flex-1 flex-col">
      <MessageList messages={conversation?.messages ?? []} />
      <MessageInput onSend={handleSend} disabled={sendMessage.isPending} />
    </div>
  );
}
