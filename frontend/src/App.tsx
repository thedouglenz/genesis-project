import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useCallback } from 'react';
import ChatLayout from './components/ChatLayout';
import LoginPage from './components/LoginPage';

function App() {
  const [authed, setAuthed] = useState(() => !!localStorage.getItem('token'));

  const handleLogin = useCallback(() => setAuthed(true), []);

  if (!authed) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatLayout />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
