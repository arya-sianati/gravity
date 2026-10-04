import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getJoinPreview, joinByToken } from '../api/sessions';

export const QRJoinScreen: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    if (!token) return;
    
    getJoinPreview(token)
      .then(data => {
        setPreview(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.response?.data?.detail || 'Failed to load session preview.');
        setLoading(false);
      });
  }, [token]);

  const handleJoin = async () => {
    if (!token) return;
    setJoining(true);
    try {
      await joinByToken(token);
      // Success, redirect to home which should pull up active session view
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to join session.');
      setJoining(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-gray-900 text-white">
        <p>Loading session details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-screen w-screen items-center justify-center bg-gray-900 text-white px-4">
        <div className="bg-red-900/30 p-6 rounded-lg text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={() => navigate('/')}
            className="bg-gray-800 px-4 py-2 rounded text-white font-medium"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-gray-900 text-white p-6 relative">
      <div className="flex-1 flex flex-col justify-center max-w-md mx-auto w-full">
        <div className="bg-gray-800 p-8 rounded-2xl shadow-xl flex flex-col items-center text-center">
          <div 
            className="w-20 h-20 flex items-center justify-center rounded-full mb-4 text-4xl shadow-inner"
            style={{ backgroundColor: preview.activity.color + '40', color: preview.activity.color }}
          >
            {preview.activity.icon}
          </div>
          
          <h2 className="text-2xl font-bold mb-1">{preview.label || preview.activity.name}</h2>
          <p className="text-gray-400 mb-6">{preview.participant_count} participant{preview.participant_count !== 1 ? 's' : ''} active</p>
          
          <button
            onClick={handleJoin}
            disabled={joining}
            className="w-full py-4 rounded-xl font-bold text-lg transition-transform active:scale-95"
            style={{ 
              backgroundColor: preview.activity.color,
              color: '#fff',
              opacity: joining ? 0.7 : 1
            }}
          >
            {joining ? 'Joining...' : 'Join Activity'}
          </button>
          
          <button
            onClick={() => navigate('/')}
            disabled={joining}
            className="mt-4 text-gray-400 font-medium py-2 px-4 hover:text-white"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
