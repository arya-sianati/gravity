import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getXPHistory, getMyBadges } from '../api/client';
import type { XPTransaction, BadgeEarned, StreakInfo } from '../api/client';

export const ProfileScreen: React.FC = () => {
  const { user, logout, updateProfile } = useAuth();

  const [isEditing, setIsEditing] = useState(false);
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [saving, setSaving] = useState(false);
  const [updatingPrivacy, setUpdatingPrivacy] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  
  const [history, setHistory] = useState<XPTransaction[]>([]);
  const [badges, setBadges] = useState<BadgeEarned[]>([]);
  const [streak, setStreak] = useState<StreakInfo | null>(null);

  useEffect(() => {
    if (user) {
      getXPHistory().then(setHistory).catch(() => {});
      getMyBadges().then(res => {
        setBadges(res.badges);
        setStreak(res.streak);
      }).catch(() => {});
    }
  }, [user]);

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

  const handlePrivacyChange = async (mode: 'hidden' | 'blurred' | 'friends' | 'exact') => {
    if (mode === user.location_privacy_mode || updatingPrivacy) return;
    try {
      setUpdatingPrivacy(true);
      await updateProfile({ location_privacy_mode: mode });
      setSaveMessage(`Location privacy updated to ${getPrivacyLabel(mode)}`);
      setTimeout(() => setSaveMessage(null), 3000);
    } catch {
      setSaveMessage('Failed to update privacy settings.');
    } finally {
      setUpdatingPrivacy(false);
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

  // Safe destructure with defaults for new api fields
  const levelProgress = user.level_progress || 0;
  const levelStart = user.level_start_xp || 0;
  const nextLevelXp = user.next_level_xp || 100;
  const remaining = nextLevelXp - user.total_xp;

  return (
    <div className="flex-1 bg-black text-white px-5 pb-5 pt-[calc(env(safe-area-inset-top,0px)+1.25rem)] overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-900">
        <h1 className="text-xl font-bold tracking-tight">Profile</h1>
        <button
          onClick={logout}
          className="text-xs text-red-400 hover:text-red-300 font-medium px-3.5 py-2.5 rounded-xl bg-red-950/40 border border-red-900/60 active:scale-95 min-h-[44px] flex items-center"
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

      {/* Level Progress */}
      <div className="mt-4 p-4 bg-gray-900/50 rounded-xl border border-gray-800/80">
        <div className="flex justify-between items-end mb-2">
          <div>
            <span className="text-xs font-bold text-indigo-400">Level {user.current_level}</span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-gray-400 uppercase font-bold tracking-wider">{user.total_xp} XP</span>
          </div>
        </div>
        
        <div className="h-2 w-full bg-gray-800 rounded-full overflow-hidden relative">
          <div 
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
            style={{ width: `${levelProgress * 100}%` }}
          />
        </div>
        
        <div className="flex justify-between mt-1.5">
          <span className="text-[10px] text-gray-500">{levelStart}</span>
          <span className="text-[10px] text-purple-400 font-medium">{remaining} XP to go!</span>
          <span className="text-[10px] text-gray-500">{nextLevelXp}</span>
        </div>
      </div>

      {/* Streak */}
      {streak && (
        <div className="mt-4 p-3.5 bg-gray-900/50 rounded-xl border border-gray-800/80 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">Activity Streak</span>
            <div className="text-2xl font-extrabold text-orange-500 mt-0.5 flex items-center space-x-2">
              <span>{streak.current} Days</span>
              {streak.current > 0 && <span className="text-lg">🔥</span>}
            </div>
          </div>
          <div className="text-right">
            <span className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">Longest</span>
            <div className="text-lg font-bold text-gray-300 mt-0.5">{streak.longest}</div>
          </div>
        </div>
      )}

      {/* Badges */}
      {badges.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 px-1">Badges Earned</h3>
          <div className="grid grid-cols-2 gap-3">
            {badges.map(b => (
              <div key={b.slug} className="p-3 bg-gray-900/40 rounded-xl border border-gray-800/50 flex flex-col items-center text-center space-y-2">
                <div className="text-3xl">{b.icon}</div>
                <div>
                  <div className="text-sm font-bold text-gray-200">{b.name}</div>
                  <div className="text-[10px] text-gray-500 leading-tight mt-1">{b.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 px-1">Recent XP</h3>
          <div className="space-y-2">
            {history.slice(0, 5).map(tx => (
              <div key={tx.id} className="p-3 bg-gray-900/40 rounded-lg border border-gray-800/50 flex justify-between items-center">
                <div>
                  <div className="text-sm font-medium text-gray-200">{tx.description || tx.reason}</div>
                  <div className="text-[10px] text-gray-500">{new Date(tx.created_at).toLocaleDateString()} &middot; {tx.activity_type || 'System'}</div>
                </div>
                <div className="text-sm font-bold text-indigo-400">
                  +{tx.amount}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Location Privacy Settings */}
      <div className="mt-6 p-4 bg-gray-900/60 rounded-2xl border border-gray-800/80">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider">
              Location Privacy Mode
            </h3>
            <p className="text-[11px] text-gray-500 mt-0.5">
              Controls coordinate precision and visibility across Map, Pulse, and Friends.
            </p>
          </div>
          {updatingPrivacy && (
            <span className="text-xs text-indigo-400 animate-pulse font-mono">Saving...</span>
          )}
        </div>

        <div className="space-y-2.5 mt-3">
          {([
            {
              mode: 'blurred' as const,
              label: 'Blurred / Approximate',
              badge: 'Recommended',
              description: 'Snaps coordinates to ~500m grid cells. Others only see generalized areas and coarse distance estimates.',
              icon: '🌫️',
            },
            {
              mode: 'friends' as const,
              label: 'Friends Only',
              description: 'Accepted friends see your exact coordinates and live distance. Strangers see blurred approximate locations.',
              icon: '👥',
            },
            {
              mode: 'hidden' as const,
              label: 'Hidden / Ghost',
              description: 'Completely hidden on Map, Pulse, and Friends Presence. Only you can see your own active session.',
              icon: '👻',
            },
            {
              mode: 'exact' as const,
              label: 'Exact / Public',
              description: 'Precise coordinates and accurate distances are visible to all users on the map and discovery feeds.',
              icon: '📍',
            },
          ]).map((opt) => {
            const isSelected = user.location_privacy_mode === opt.mode;
            return (
              <div
                key={opt.mode}
                role="button"
                tabIndex={0}
                onClick={() => handlePrivacyChange(opt.mode)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handlePrivacyChange(opt.mode);
                  }
                }}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-start space-x-3 min-h-[48px] active:scale-[0.99] ${
                  isSelected
                    ? 'bg-indigo-950/40 border-indigo-600/80 shadow-md shadow-indigo-950/50'
                    : 'bg-gray-900/40 border-gray-800/60 hover:bg-gray-800/40 hover:border-gray-700/60'
                }`}
              >
                <div className="text-xl mt-0.5">{opt.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className={`text-xs font-bold ${isSelected ? 'text-indigo-200' : 'text-gray-200'}`}>
                      {opt.label}
                    </span>
                    {opt.badge && (
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-600/50 text-indigo-200 font-semibold uppercase tracking-wider">
                        {opt.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-gray-400 mt-0.5 leading-snug">
                    {opt.description}
                  </p>
                </div>
                <div className="mt-1">
                  <div
                    className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                      isSelected
                        ? 'border-indigo-500 bg-indigo-600'
                        : 'border-gray-600 bg-gray-800'
                    }`}
                  >
                    {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Membership Info */}
      <div className="mt-6 text-center text-[10px] text-gray-600 font-mono mb-8">
        Member since {new Date(user.created_at).toLocaleDateString()}
      </div>
    </div>
  );
};
