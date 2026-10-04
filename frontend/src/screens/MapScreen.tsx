import { useEffect, useState } from "react";
import { checkHealth } from '../api/client';

export const MapScreen: React.FC = () => {
  const [health, setHealth] = useState<string>('Checking backend...');

  useEffect(() => {
    checkHealth()
      .then((data) => setHealth(data.status))
      .catch((err) => setHealth('Error: ' + err.message));
  }, []);

  return (
    <div className="flex-1 bg-gray-900 flex flex-col items-center justify-center relative">
      <h1 className="text-2xl font-bold mb-4">Map View Placeholder</h1>
      <p className="text-gray-400">Backend Health: <span className="text-white font-mono">{health}</span></p>
    </div>
  );
};
