import { useState } from 'react';
import Sidebar from './Sidebar';
import ChatPane from './ChatPane';

export default function ChatLayout({ onLogout }: { onLogout: () => void }) {
  const [activeId, setActiveId] = useState<string | null>(null);

  return (
    <div className="flex h-screen">
      <Sidebar activeId={activeId} onSelect={setActiveId} onLogout={onLogout} />
      <ChatPane conversationId={activeId} />
    </div>
  );
}
