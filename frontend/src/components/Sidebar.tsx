import { useConversations, useCreateConversation } from '../hooks/useConversations';

export default function Sidebar({
  activeId,
  onSelect,
  onLogout,
}: {
  activeId: string | null;
  onSelect: (id: string) => void;
  onLogout: () => void;
}) {
  const { data: conversations, isLoading } = useConversations();
  const createConversation = useCreateConversation();

  const handleNew = async () => {
    const conversation = await createConversation.mutateAsync();
    onSelect(conversation.id);
  };

  return (
    <aside className="flex h-full w-64 flex-col border-r border-gray-200 bg-gray-50">
      <div className="p-3">
        <button
          onClick={handleNew}
          className="w-full rounded bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
        >
          New conversation
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto">
        {isLoading && (
          <p className="px-3 py-2 text-sm text-gray-500">Loading...</p>
        )}
        {conversations?.map((c) => (
          <button
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={`w-full truncate px-3 py-2 text-left text-sm hover:bg-gray-100 ${
              activeId === c.id ? 'bg-gray-200 font-medium' : ''
            }`}
          >
            {c.title || 'New conversation'}
          </button>
        ))}
      </nav>
      <div className="border-t border-gray-200 p-3">
        <button
          onClick={onLogout}
          className="w-full rounded px-3 py-2 text-sm text-gray-600 hover:bg-gray-200"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
