import { useConversations, useCreateConversation, useDeleteConversation } from '../hooks/useConversations';

export default function Sidebar({
  activeId,
  onSelect,
  onLogout,
}: {
  activeId: string | null;
  onSelect: (id: string | null) => void;
  onLogout: () => void;
}) {
  const { data: conversations, isLoading } = useConversations();
  const createConversation = useCreateConversation();
  const deleteConversation = useDeleteConversation();

  const handleNew = async () => {
    const conversation = await createConversation.mutateAsync();
    onSelect(conversation.id);
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    deleteConversation.mutate(id);
    if (activeId === id) {
      onSelect(null);
    }
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
          <div
            key={c.id}
            className={`group flex items-center hover:bg-gray-100 ${
              activeId === c.id ? 'bg-gray-200' : ''
            }`}
          >
            <button
              onClick={() => onSelect(c.id)}
              className={`flex-1 truncate px-3 py-2 text-left text-sm ${
                activeId === c.id ? 'font-medium' : ''
              }`}
            >
              {c.title || 'New conversation'}
            </button>
            <button
              onClick={(e) => handleDelete(e, c.id)}
              className="mr-1 hidden rounded p-1 text-gray-400 hover:bg-gray-300 hover:text-gray-700 group-hover:block"
              title="Delete conversation"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
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
