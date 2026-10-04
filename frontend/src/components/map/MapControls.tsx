import React from 'react';
import { useNavigate } from 'react-router-dom';

interface MapControlsProps {
  onRecenter: () => void;
  locating: boolean;
}

export const MapControls: React.FC<MapControlsProps> = ({ onRecenter, locating }) => {
  const navigate = useNavigate();

  return (
    <div className="absolute bottom-24 right-4 z-10 flex flex-col gap-2.5 items-end">
      {/* Pulse button */}
      <button
        onClick={() => navigate('/pulse')}
        className="h-10 px-3.5 bg-gray-900/90 hover:bg-gray-800 text-white rounded-full flex items-center gap-1.5 shadow-lg border border-gray-700 backdrop-blur-md active:scale-95 transition-all text-xs font-bold"
        aria-label="Open Pulse Feed"
      >
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span>Pulse</span>
      </button>

      {/* Recenter button */}
      <button 
        onClick={onRecenter}
        disabled={locating}
        className="w-12 h-12 bg-gray-800 text-white rounded-full flex items-center justify-center shadow-lg border border-gray-600 active:scale-95 transition-transform"
        aria-label="Recenter Map"
      >
        {locating ? (
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm0 0c-1.657 0-3 1.343-3 3s1.343 3 3 3 3-1.343 3-3-1.343-3-3-3z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 2v2m0 16v2m8-10h2m-20 0H2" />
          </svg>
        )}
      </button>
    </div>
  );
};
