import { useEffect, useState } from 'react';
import { checkHealth } from '../api/client';
import { useAuth } from '../context/AuthContext';

export const MapScreen: React.FC = () => {
  const { user } = useAuth();
  const [health, setHealth] = useState<string>('Checking backend...');

  useEffect(() => {
    checkHealth()
      .then((data) => setHealth(data.status))
      .catch((err) => setHealth('Error: ' + err.message));
  }, []);

  return (
    <div className="flex-1 bg-black flex flex-col items-center justify-center p-6 text-center relative">
      <div className="w-16 h-16 rounded-full bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center mb-4">
        <span className="text-2xl">🗺️</span>
      </div>
      <h1 className="text-xl font-bold text-white mb-1">
        Welcome, {user?.display_name || user?.username}!
      </h1>
      <p className="text-xs text-gray-400 mb-6">
        Live Activity Map & Heatmap will render here in Phase 07.
      </p>

      <div className="px-3.5 py-2 rounded-xl bg-gray-900 border border-gray-800 text-xs text-gray-400 flex items-center space-x-2">
        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
        <span>Backend Health: <span className="text-white font-mono">{health}</span></span>
      </div>
    </div>
  );
};
