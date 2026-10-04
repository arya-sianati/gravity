import React, { useEffect, useState } from 'react';
import { getActivities } from '../api/activities';
import type { ActivityType } from '../api/activities';

export const StartActivityScreen: React.FC = () => {
  const [activities, setActivities] = useState<ActivityType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchActivities = async () => {
      try {
        setLoading(true);
        const data = await getActivities();
        if (mounted) {
          setActivities(data);
          setError(null);
        }
      } catch (err: any) {
        if (mounted) {
          setError(err.message || 'Failed to load activities');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchActivities();
    return () => { mounted = false; };
  }, []);

  return (
    <div className="flex-1 bg-gray-900 p-6 flex flex-col h-full overflow-y-auto">
      <h1 className="text-2xl font-bold text-white mb-6">Start Activity</h1>
      
      {loading && (
        <div className="flex justify-center items-center py-10">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white"></div>
        </div>
      )}

      {error && (
        <div className="bg-red-500 bg-opacity-20 text-red-100 p-4 rounded-lg mb-6">
          {error}
        </div>
      )}

      {!loading && !error && activities.length === 0 && (
        <div className="text-gray-400 text-center py-10">
          No activities available.
        </div>
      )}

      {!loading && !error && activities.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {activities.map(activity => (
            <button
              key={activity.id}
              className="bg-gray-800 hover:bg-gray-700 transition-colors rounded-xl p-4 flex flex-col items-center justify-center border border-gray-700 shadow-sm"
              style={{ borderBottomColor: activity.color, borderBottomWidth: 4 }}
            >
              <div className="text-4xl mb-2">{activity.icon}</div>
              <span className="text-white font-medium">{activity.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
