import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export const ProfileScreen: React.FC = () => {
  const { user, logout, updateProfile } = useAuth();

  const [isEditing, setIsEditing] = useState(false);
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  if (!user) {
    return null;
  }

  const handleSave = async () => {
    try {
      setSaving(true);
      setSaveMessage(null);
      await updateProfile({ display_name: displayName.trim() });
      setIsEditing(false);
      setSaveMessage('Profile updated successfully!');
      setTimeout(() => setSaveMessage(null), 3000);
    } catch {
      setSaveMessage('Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  const getPrivacyLabel = (mode: string) => {
    switch (mode) {
      case 'exact':
        return 'Exact Location';
      case 'blurred':
        return 'Blurred / Approximate';
      case 'friends':
        return 'Friends Only';
      case 'hidden':
        return 'Hidden';
      default:
        return mode;
    }
  };

  return (
    <div className="flex-1 bg-black text-white p-5 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-900">
        <h1 className="text-xl font-bold tracking-tight">Profile</h1>
        <button
          onClick={logout}
          className="text-xs text-red-400 hover:text-red-300 font-medium px-3 py-1.5 rounded-lg bg-red-950/40 border border-red-900/60"
        >
          Sign Out
        </button>
      </div>

      {saveMessage && (
        <div className="mt-3 p-2.5 bg-indigo-950/60 border border-indigo-800 rounded-lg text-xs text-indigo-200">
          {saveMessage}
        </div>
      )}

      {/* User Info Card */}
      <div className="mt-4 p-4 bg-gray-900/80 rounded-2xl border border-gray-800 flex items-center space-x-4">
        <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-xl font-extrabold shadow-md shadow-indigo-600/30">
          {(user.display_name || user.username).charAt(0).toUpperCase()}
        </div>

        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                disabled={saving}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="Display Name"
              />
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-2.5 py-1 bg-indigo-600 rounded text-xs font-semibold hover:bg-indigo-500 disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={() => {
                  setDisplayName(user.display_name);
                  setIsEditing(false);
                }}
                className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-400 hover:text-gray-200"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold text-base truncate">{user.display_name || user.username}</h2>
                <p className="text-xs text-gray-400 font-mono">@{user.username}</p>
              </div>
              <button
                onClick={() => setIsEditing(true)}
                className="text-xs text-indigo-400 hover:text-indigo-300 ml-2"
              >
                Edit
              </button>
            </div>
          )}

          {user.email && <p className="text-xs text-gray-500 truncate mt-1">{user.email}</p>}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mt-4">
        <div className="p-3.5 bg-gray-900/50 rounded-xl border border-gray-800/80">
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">Gravity Level</span>
          <div className="text-2xl font-extrabold text-indigo-400 mt-0.5">Lv. {user.current_level}</div>
        </div>

        <div className="p-3.5 bg-gray-900/50 rounded-xl border border-gray-800/80">
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">Total XP</span>
          <div className="text-2xl font-extrabold text-purple-400 mt-0.5">{user.total_xp} <span className="text-xs font-normal text-gray-400">XP</span></div>
        </div>
      </div>

      {/* Privacy Mode Info */}
      <div className="mt-4 p-4 bg-gray-900/40 rounded-xl border border-gray-800/60">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-300">Location Privacy</span>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-950/60 text-indigo-300 border border-indigo-800/50">
            {getPrivacyLabel(user.location_privacy_mode)}
          </span>
        </div>
        <p className="text-[11px] text-gray-500 mt-2 leading-relaxed">
          Full privacy configuration controls will unlock in Phase 16.
        </p>
      </div>

      {/* Membership Info */}
      <div className="mt-6 text-center text-[10px] text-gray-600 font-mono">
        Member since {new Date(user.created_at).toLocaleDateString()}
      </div>
    </div>
  );
};
