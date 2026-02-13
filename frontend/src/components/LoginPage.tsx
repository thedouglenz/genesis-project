import { useState } from 'react';
import client from '../api/client';

export default function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const { data } = await client.post('/api/auth/login', {
        username,
        password,
      });
      localStorage.setItem('token', data.token);
      onLogin();
    } catch {
      setError('Invalid credentials');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg bg-white p-8 shadow"
      >
        <h1 className="text-2xl font-bold text-gray-900">Sign in</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700"
        >
          Sign in
        </button>
      </form>
    </div>
  );
}
