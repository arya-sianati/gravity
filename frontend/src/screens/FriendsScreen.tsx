import React, { useState, useEffect, useCallback } from 'react';
import {
  getFriends,
  getFriendsPresence,
  getIncomingFriendRequests,
  getOutgoingFriendRequests,
  searchUsers,
  sendFriendRequest,
  acceptFriendRequest,
  declineFriendRequest,
  cancelFriendRequest,
  removeFriend,
  getUserProfile,
} from '../api/friends';
import type {
  PublicUser,
  FriendPresenceItem,
  FriendshipRequest,
  PublicProfileResponse,
} from '../api/friends';

type Tab = 'friends' | 'requests' | 'search';

export const FriendsScreen: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('friends');

  // Friends & Presence state
  const [friends, setFriends] = useState<PublicUser[]>([]);
  const [presence, setPresence] = useState<FriendPresenceItem[]>([]);
  const [loadingFriends, setLoadingFriends] = useState(false);

  // Requests state
  const [incomingRequests, setIncomingRequests] = useState<FriendshipRequest[]>([]);
  const [outgoingRequests, setOutgoingRequests] = useState<FriendshipRequest[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<PublicUser[]>([]);
  const [searching, setSearching] = useState(false);

  // Profile modal state
  const [selectedProfile, setSelectedProfile] = useState<PublicProfileResponse | null>(null);

  // Notifications
  const [feedback, setFeedback] = useState<string | null>(null);

  const showFeedback = (msg: string) => {
    setFeedback(msg);
    setTimeout(() => setFeedback(null), 3000);
  };

  const fetchFriendsData = useCallback(async () => {
    setLoadingFriends(true);
    try {
      const [friendsList, presenceList] = await Promise.all([
        getFriends(),
        getFriendsPresence(),
      ]);
      setFriends(friendsList);
      setPresence(presenceList);
    } catch (err) {
      console.error('Failed to load friends:', err);
    } finally {
      setLoadingFriends(false);
    }
  }, []);

  const fetchRequestsData = useCallback(async () => {
    setLoadingRequests(true);
    try {
      const [inc, out] = await Promise.all([
        getIncomingFriendRequests(),
        getOutgoingFriendRequests(),
      ]);
      setIncomingRequests(inc);
      setOutgoingRequests(out);
    } catch (err) {
      console.error('Failed to load requests:', err);
    } finally {
      setLoadingRequests(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'friends') {
      fetchFriendsData();
    } else if (activeTab === 'requests') {
      fetchRequestsData();
    }
  }, [activeTab, fetchFriendsData, fetchRequestsData]);

  // Handle Search
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const results = await searchUsers(searchQuery);
      setSearchResults(results);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setSearching(false);
    }
  };

  // Actions
  const handleSendRequest = async (user: PublicUser) => {
    try {
      const res = await sendFriendRequest(user.id);
      if (res.action_result === 'accepted') {
        showFeedback(`Connected with @${user.username}!`);
      } else {
        showFeedback(`Friend request sent to @${user.username}`);
      }
      setSearchResults((prev) =>
        prev.map((u) =>
          u.id === user.id
            ? { ...u, friendship_status: res.action_result === 'accepted' ? 'accepted' : 'pending_outgoing' }
            : u
        )
      );
    } catch (err: any) {
      showFeedback(err.response?.data?.detail || 'Failed to send request');
    }
  };

  const handleAcceptRequest = async (req: FriendshipRequest) => {
    try {
      await acceptFriendRequest(req.id);
      showFeedback(`Accepted request from @${req.initiator.username}`);
      setIncomingRequests((prev) => prev.filter((r) => r.id !== req.id));
      fetchFriendsData();
    } catch {
      showFeedback('Failed to accept request');
    }
  };

  const handleDeclineRequest = async (req: FriendshipRequest) => {
    try {
      await declineFriendRequest(req.id);
      showFeedback(`Declined request from @${req.initiator.username}`);
      setIncomingRequests((prev) => prev.filter((r) => r.id !== req.id));
    } catch {
      showFeedback('Failed to decline request');
    }
  };

  const handleCancelRequest = async (req: FriendshipRequest) => {
    try {
      await cancelFriendRequest(req.id);
      showFeedback('Request cancelled');
      setOutgoingRequests((prev) => prev.filter((r) => r.id !== req.id));
    } catch {
      showFeedback('Failed to cancel request');
    }
  };

  const handleRemoveFriend = async (friend: PublicUser) => {
    if (!window.confirm(`Remove @${friend.username} from your friends?`)) return;
    try {
      await removeFriend(friend.id);
      showFeedback(`Removed @${friend.username}`);
      setFriends((prev) => prev.filter((f) => f.id !== friend.id));
      setPresence((prev) => prev.filter((p) => p.friend.id !== friend.id));
      if (selectedProfile?.user.id === friend.id) {
        setSelectedProfile(null);
      }
    } catch {
      showFeedback('Failed to remove friend');
    }
  };

  const handleOpenProfile = async (userId: number) => {
    try {
      const data = await getUserProfile(userId);
      setSelectedProfile(data);
    } catch {
      showFeedback('Could not load user profile');
    }
  };

  return (
    <div className="flex-1 bg-black text-white p-5 overflow-y-auto max-w-2xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-900">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Friends</h1>
          <p className="text-xs text-gray-400 mt-0.5">Mutual community, live presence & shared activities</p>
        </div>
      </div>

      {/* Toast Feedback */}
      {feedback && (
        <div className="mt-3 p-2.5 bg-indigo-950/80 border border-indigo-700/80 rounded-xl text-xs text-indigo-200 animate-fade-in shadow-lg shadow-indigo-950/40">
          {feedback}
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-2 mt-4 bg-gray-950 p-1 rounded-xl border border-gray-900">
        <button
          onClick={() => setActiveTab('friends')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
            activeTab === 'friends'
              ? 'bg-gray-800 text-white shadow'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <span>Friends</span>
          {friends.length > 0 && (
            <span className="px-1.5 py-0.2 text-[10px] rounded-full bg-indigo-600/60 text-indigo-200 font-mono">
              {friends.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('requests')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
            activeTab === 'requests'
              ? 'bg-gray-800 text-white shadow'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <span>Requests</span>
          {incomingRequests.length > 0 && (
            <span className="px-1.5 py-0.2 text-[10px] rounded-full bg-purple-600 text-white font-mono">
              {incomingRequests.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('search')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
            activeTab === 'search'
              ? 'bg-gray-800 text-white shadow'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <span>Find Friends</span>
        </button>
      </div>

      {/* TAB 1: FRIENDS & LIVE PRESENCE */}
      {activeTab === 'friends' && (
        <div className="mt-5 space-y-6">
          {/* Live Presence Feed */}
          {presence.length > 0 && (
            <div>
              <div className="flex items-center space-x-2 mb-3">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                  Active Now ({presence.length})
                </h3>
              </div>
              <div className="space-y-3">
                {presence.map((p) => (
                  <div
                    key={p.session_id}
                    className="p-3.5 bg-gradient-to-r from-emerald-950/30 to-gray-900/60 rounded-xl border border-emerald-900/40 flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <div className="w-10 h-10 rounded-full bg-gray-800 flex items-center justify-center text-lg shadow-inner">
                        {p.activity.icon || '⚡'}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleOpenProfile(p.friend.id)}
                            className="font-bold text-sm text-gray-200 hover:text-emerald-300 truncate"
                          >
                            {p.friend.display_name || p.friend.username}
                          </button>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 font-mono">
                            Lvl {p.friend.current_level}
                          </span>
                        </div>
                        <p className="text-xs text-gray-400 truncate">
                          {p.label || p.activity.name} &middot;{' '}
                          <span className="text-emerald-400">{p.location_display || 'Active'}</span>
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Friends Roster */}
          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 px-1">
              All Friends ({friends.length})
            </h3>

            {loadingFriends ? (
              <div className="py-8 text-center text-xs text-gray-500">Loading friends...</div>
            ) : friends.length === 0 ? (
              <div className="p-8 text-center bg-gray-900/40 rounded-2xl border border-gray-800/60 space-y-3">
                <div className="text-4xl">👥</div>
                <h4 className="text-sm font-semibold text-gray-300">No friends yet</h4>
                <p className="text-xs text-gray-500 max-w-xs mx-auto">
                  Search for members to connect, see live activities, and build your mutual circle!
                </p>
                <button
                  onClick={() => setActiveTab('search')}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold rounded-lg transition"
                >
                  Find Friends
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {friends.map((f) => (
                  <div
                    key={f.id}
                    className="p-3 bg-gray-900/50 hover:bg-gray-900/80 rounded-xl border border-gray-800/60 flex items-center justify-between transition"
                  >
                    <div
                      onClick={() => handleOpenProfile(f.id)}
                      className="flex items-center space-x-3 cursor-pointer min-w-0"
                    >
                      <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-700 to-purple-700 flex items-center justify-center font-bold text-sm text-white">
                        {(f.display_name || f.username).charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="font-bold text-sm text-gray-200 truncate">
                          {f.display_name || f.username}
                        </div>
                        <div className="text-xs text-gray-500 font-mono">
                          @{f.username} &middot; Level {f.current_level}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleRemoveFriend(f)}
                      className="text-xs text-gray-500 hover:text-red-400 p-2 rounded-lg hover:bg-red-950/20 transition"
                      title="Remove Friend"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: REQUESTS */}
      {activeTab === 'requests' && (
        <div className="mt-5 space-y-6">
          {/* Incoming */}
          <div>
            <h3 className="text-xs font-bold text-purple-400 uppercase tracking-wider mb-3 px-1">
              Incoming Requests ({incomingRequests.length})
            </h3>
            {loadingRequests ? (
              <div className="py-6 text-center text-xs text-gray-500">Loading requests...</div>
            ) : incomingRequests.length === 0 ? (
              <div className="p-4 text-center bg-gray-900/30 rounded-xl border border-gray-800/40 text-xs text-gray-500">
                No incoming friend requests.
              </div>
            ) : (
              <div className="space-y-2">
                {incomingRequests.map((req) => (
                  <div
                    key={req.id}
                    className="p-3 bg-gray-900/70 rounded-xl border border-purple-900/40 flex items-center justify-between"
                  >
                    <div
                      onClick={() => handleOpenProfile(req.initiator.id)}
                      className="flex items-center space-x-3 cursor-pointer min-w-0"
                    >
                      <div className="w-9 h-9 rounded-full bg-purple-800 flex items-center justify-center font-bold text-xs">
                        {(req.initiator.display_name || req.initiator.username).charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="font-bold text-xs text-gray-200 truncate">
                          {req.initiator.display_name || req.initiator.username}
                        </div>
                        <div className="text-[11px] text-gray-500 font-mono">
                          @{req.initiator.username} &middot; Lvl {req.initiator.current_level}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1.5">
                      <button
                        onClick={() => handleAcceptRequest(req)}
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold rounded-lg transition"
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => handleDeclineRequest(req)}
                        className="px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs font-medium text-gray-400 rounded-lg transition"
                      >
                        Decline
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Outgoing */}
          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 px-1">
              Sent Requests ({outgoingRequests.length})
            </h3>
            {outgoingRequests.length === 0 ? (
              <div className="p-4 text-center bg-gray-900/30 rounded-xl border border-gray-800/40 text-xs text-gray-500">
                No outgoing friend requests pending.
              </div>
            ) : (
              <div className="space-y-2">
                {outgoingRequests.map((req) => (
                  <div
                    key={req.id}
                    className="p-3 bg-gray-900/40 rounded-xl border border-gray-800/40 flex items-center justify-between"
                  >
                    <div
                      onClick={() => handleOpenProfile(req.recipient.id)}
                      className="flex items-center space-x-3 cursor-pointer min-w-0"
                    >
                      <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center font-bold text-xs text-gray-400">
                        {(req.recipient.display_name || req.recipient.username).charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="font-medium text-xs text-gray-300 truncate">
                          @{req.recipient.username}
                        </div>
                        <div className="text-[10px] text-gray-500">Pending approval</div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleCancelRequest(req)}
                      className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1 rounded bg-gray-800 hover:bg-gray-700"
                    >
                      Cancel
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: FIND FRIENDS (SEARCH) */}
      {activeTab === 'search' && (
        <div className="mt-5 space-y-4">
          <form onSubmit={handleSearch} className="flex space-x-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by username or name..."
              className="flex-1 px-3.5 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={searching}
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-bold rounded-xl transition"
            >
              {searching ? '...' : 'Search'}
            </button>
          </form>

          {/* Results */}
          <div className="space-y-2">
            {searchResults.map((user) => (
              <div
                key={user.id}
                className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/60 flex items-center justify-between"
              >
                <div
                  onClick={() => handleOpenProfile(user.id)}
                  className="flex items-center space-x-3 cursor-pointer min-w-0"
                >
                  <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-800 to-indigo-800 flex items-center justify-center font-bold text-sm">
                    {(user.display_name || user.username).charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-sm text-gray-200 truncate">
                      {user.display_name || user.username}
                    </div>
                    <div className="text-xs text-gray-500 font-mono">
                      @{user.username} &middot; Lvl {user.current_level}
                    </div>
                  </div>
                </div>

                <div>
                  {user.friendship_status === 'none' && (
                    <button
                      onClick={() => handleSendRequest(user)}
                      className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold rounded-lg transition"
                    >
                      Add Friend
                    </button>
                  )}
                  {user.friendship_status === 'pending_outgoing' && (
                    <span className="text-xs font-medium text-gray-400 px-2.5 py-1 rounded bg-gray-800">
                      Requested
                    </span>
                  )}
                  {user.friendship_status === 'pending_incoming' && (
                    <button
                      onClick={() => setActiveTab('requests')}
                      className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-xs font-bold rounded-lg transition"
                    >
                      Respond
                    </button>
                  )}
                  {user.friendship_status === 'accepted' && (
                    <span className="text-xs font-semibold text-emerald-400 px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-800/40">
                      Friends
                    </span>
                  )}
                </div>
              </div>
            ))}

            {searchResults.length === 0 && searchQuery.trim() && !searching && (
              <div className="p-8 text-center text-xs text-gray-500">
                No users found matching &ldquo;{searchQuery}&rdquo;.
              </div>
            )}
          </div>
        </div>
      )}

      {/* USER PROFILE MODAL */}
      {selectedProfile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-sm w-full p-5 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center font-bold text-lg text-white">
                  {(selectedProfile.user.display_name || selectedProfile.user.username).charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 className="font-bold text-base text-gray-100">
                    {selectedProfile.user.display_name || selectedProfile.user.username}
                  </h3>
                  <p className="text-xs text-gray-400 font-mono">@{selectedProfile.user.username}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedProfile(null)}
                className="text-gray-400 hover:text-white p-1"
              >
                ✕
              </button>
            </div>

            {/* Level & Streak */}
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="p-3 bg-gray-800/50 rounded-xl">
                <div className="text-[10px] text-gray-400 uppercase font-bold">Level</div>
                <div className="text-lg font-bold text-indigo-400">{selectedProfile.user.current_level}</div>
              </div>
              <div className="p-3 bg-gray-800/50 rounded-xl">
                <div className="text-[10px] text-gray-400 uppercase font-bold">Streak</div>
                <div className="text-lg font-bold text-orange-400">
                  {selectedProfile.streak.current}d 🔥
                </div>
              </div>
            </div>

            {/* Active Session (if available) */}
            {selectedProfile.active_session && (
              <div className="p-3.5 bg-emerald-950/30 border border-emerald-800/50 rounded-xl">
                <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider mb-1">
                  Active Now
                </div>
                <div className="text-sm font-bold text-gray-200 flex items-center space-x-1.5">
                  <span>{selectedProfile.active_session.activity_type.icon}</span>
                  <span>{selectedProfile.active_session.label || selectedProfile.active_session.activity_type.name}</span>
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  Started: {new Date(selectedProfile.active_session.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            )}

            {/* Badges */}
            {selectedProfile.badges.length > 0 && (
              <div>
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                  Badges ({selectedProfile.badges.length})
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {selectedProfile.badges.map((b) => (
                    <div
                      key={b.slug}
                      className="p-2 bg-gray-800/40 rounded-lg text-center border border-gray-700/40"
                    >
                      <div className="text-xl">{b.icon}</div>
                      <div className="text-xs font-semibold text-gray-200 mt-1 truncate">{b.name}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Button inside modal */}
            <div>
              {selectedProfile.user.friendship_status === 'none' && (
                <button
                  onClick={() => {
                    handleSendRequest(selectedProfile.user);
                    setSelectedProfile(null);
                  }}
                  className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 font-bold text-xs rounded-xl transition"
                >
                  Send Friend Request
                </button>
              )}
              {selectedProfile.user.friendship_status === 'accepted' && (
                <button
                  onClick={() => {
                    handleRemoveFriend(selectedProfile.user);
                  }}
                  className="w-full py-2 bg-red-950/40 hover:bg-red-900/60 border border-red-900/60 font-semibold text-xs text-red-300 rounded-xl transition"
                >
                  Remove Friend
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
