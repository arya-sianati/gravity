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

import { getActivities } from '../api/activities';
import type { ActivityType, ActivityMetric } from '../api/activities';

import {
  getChallenges,
  createChallenge,
  acceptChallenge,
  declineChallenge,
  cancelChallenge,
} from '../api/challenges';
import type { FriendChallenge } from '../api/challenges';
import { useAuth } from '../context/AuthContext';

type Tab = 'friends' | 'requests' | 'search' | 'challenges';
type ChallengeFilter = 'all' | 'active' | 'pending' | 'completed';

export const FriendsScreen: React.FC = () => {
  const { user: currentUser } = useAuth();
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

  // Challenges state
  const [challenges, setChallenges] = useState<FriendChallenge[]>([]);
  const [loadingChallenges, setLoadingChallenges] = useState(false);
  const [challengeFilter, setChallengeFilter] = useState<ChallengeFilter>('all');
  const [showCreateChallengeModal, setShowCreateChallengeModal] = useState(false);
  const [availableActivities, setAvailableActivities] = useState<ActivityType[]>([]);

  // Create Challenge Form state
  const [createTitle, setCreateTitle] = useState('');
  const [createActivity, setCreateActivity] = useState<ActivityType | null>(null);
  const [createMetric, setCreateMetric] = useState<ActivityMetric | null>(null);
  const [createType, setCreateType] = useState<'first_to_target' | 'highest_by_deadline' | 'cooperative_target'>('first_to_target');
  const [createTargetValue, setCreateTargetValue] = useState('10');
  const [createDurationDays, setCreateDurationDays] = useState(3);
  const [createInvitees, setCreateInvitees] = useState<number[]>([]);
  const [creatingChallenge, setCreatingChallenge] = useState(false);

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

  const fetchChallengesData = useCallback(async () => {
    setLoadingChallenges(true);
    try {
      const filterArg = challengeFilter === 'all' ? undefined : challengeFilter;
      const list = await getChallenges(filterArg);
      setChallenges(list);
    } catch (err) {
      console.error('Failed to load challenges:', err);
    } finally {
      setLoadingChallenges(false);
    }
  }, [challengeFilter]);

  useEffect(() => {
    if (activeTab === 'friends') {
      fetchFriendsData();
    } else if (activeTab === 'requests') {
      fetchRequestsData();
    } else if (activeTab === 'challenges') {
      fetchChallengesData();
      getActivities().then((acts) => {
        setAvailableActivities(acts);
        if (acts.length > 0 && !createActivity) {
          setCreateActivity(acts[0]);
          if (acts[0].metrics && acts[0].metrics.length > 0) {
            setCreateMetric(acts[0].metrics[0]);
          }
        }
      }).catch(() => {});
      getFriends().then(setFriends).catch(() => {});
    }
  }, [activeTab, fetchFriendsData, fetchRequestsData, fetchChallengesData]);

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

  // Challenge actions
  const handleAcceptChallenge = async (chId: number) => {
    try {
      await acceptChallenge(chId);
      showFeedback('Accepted challenge invitation!');
      fetchChallengesData();
    } catch (err: any) {
      showFeedback(err.response?.data?.detail || 'Failed to accept challenge');
    }
  };

  const handleDeclineChallenge = async (chId: number) => {
    try {
      await declineChallenge(chId);
      showFeedback('Declined challenge invitation');
      fetchChallengesData();
    } catch (err: any) {
      showFeedback(err.response?.data?.detail || 'Failed to decline challenge');
    }
  };

  const handleCancelChallenge = async (chId: number) => {
    if (!window.confirm('Are you sure you want to cancel this challenge?')) return;
    try {
      await cancelChallenge(chId);
      showFeedback('Challenge cancelled');
      fetchChallengesData();
    } catch (err: any) {
      showFeedback(err.response?.data?.detail || 'Failed to cancel challenge');
    }
  };

  const handleActivityChange = (slug: string) => {
    const act = availableActivities.find((a) => a.slug === slug) || null;
    setCreateActivity(act);
    if (act && act.metrics && act.metrics.length > 0) {
      setCreateMetric(act.metrics[0]);
    } else {
      setCreateMetric(null);
    }
  };

  const handleToggleInvitee = (friendId: number) => {
    setCreateInvitees((prev) =>
      prev.includes(friendId) ? prev.filter((id) => id !== friendId) : [...prev, friendId]
    );
  };

  const handleCreateChallengeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createActivity || !createMetric) {
      showFeedback('Please select an activity and metric');
      return;
    }
    if (createInvitees.length === 0) {
      showFeedback('Please invite at least one friend');
      return;
    }
    const val = parseFloat(createTargetValue);
    if (createType !== 'highest_by_deadline' && (isNaN(val) || val <= 0)) {
      showFeedback('Target value must be greater than 0');
      return;
    }

    setCreatingChallenge(true);
    try {
      const now = new Date();
      const ends = new Date(now.getTime() + createDurationDays * 24 * 60 * 60 * 1000);

      await createChallenge({
        activity_type: createActivity.slug,
        metric: createMetric.slug,
        challenge_type: createType,
        target_value: createType === 'highest_by_deadline' ? null : val,
        starts_at: now.toISOString(),
        ends_at: ends.toISOString(),
        invitees: createInvitees,
        title: createTitle.trim() || undefined,
      });

      showFeedback('Challenge launched!');
      setShowCreateChallengeModal(false);
      setCreateTitle('');
      setCreateInvitees([]);
      fetchChallengesData();
    } catch (err: any) {
      showFeedback(err.response?.data?.detail || 'Failed to create challenge');
    } finally {
      setCreatingChallenge(false);
    }
  };

  const pendingInvitationsCount = challenges.filter(
    (c) => c.my_participant_info?.invitation_status === 'invited'
  ).length;

  return (
    <div className="flex-1 bg-black text-white p-5 overflow-y-auto max-w-2xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-900">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Friends & Challenges</h1>
          <p className="text-xs text-gray-400 mt-0.5">Mutual community, live presence & shared challenges</p>
        </div>
      </div>

      {/* Toast Feedback */}
      {feedback && (
        <div className="mt-3 p-2.5 bg-indigo-950/80 border border-indigo-700/80 rounded-xl text-xs text-indigo-200 animate-fade-in shadow-lg shadow-indigo-950/40">
          {feedback}
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-1.5 mt-4 bg-gray-950 p-1 rounded-xl border border-gray-900">
        <button
          onClick={() => setActiveTab('friends')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center space-x-1 ${
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
          onClick={() => setActiveTab('challenges')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center space-x-1 ${
            activeTab === 'challenges'
              ? 'bg-gray-800 text-white shadow'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <span>Challenges</span>
          {pendingInvitationsCount > 0 && (
            <span className="px-1.5 py-0.2 text-[10px] rounded-full bg-amber-500 text-black font-bold font-mono">
              {pendingInvitationsCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('requests')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center space-x-1 ${
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
          className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center space-x-1 ${
            activeTab === 'search'
              ? 'bg-gray-800 text-white shadow'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          <span>Find</span>
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
                  Search for members to connect, see live activities, and launch friend challenges!
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

      {/* TAB 2: FRIEND CHALLENGES */}
      {activeTab === 'challenges' && (
        <div className="mt-5 space-y-5">
          {/* Action Bar */}
          <div className="flex items-center justify-between">
            <div className="flex space-x-1.5 bg-gray-950 p-1 rounded-lg border border-gray-900">
              {(['all', 'active', 'pending', 'completed'] as ChallengeFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setChallengeFilter(f)}
                  className={`px-2.5 py-1 text-[11px] font-semibold rounded-md capitalize transition ${
                    challengeFilter === f
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            <button
              onClick={() => setShowCreateChallengeModal(true)}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold rounded-lg shadow-md transition flex items-center space-x-1"
            >
              <span>+ New Challenge</span>
            </button>
          </div>

          {/* Challenge List */}
          {loadingChallenges ? (
            <div className="py-8 text-center text-xs text-gray-500">Loading challenges...</div>
          ) : challenges.length === 0 ? (
            <div className="p-8 text-center bg-gray-900/40 rounded-2xl border border-gray-800/60 space-y-3">
              <div className="text-4xl">🏆</div>
              <h4 className="text-sm font-semibold text-gray-300">No challenges yet</h4>
              <p className="text-xs text-gray-500 max-w-xs mx-auto">
                Create friendly competitions or cooperative goals with your friends!
              </p>
              <button
                onClick={() => setShowCreateChallengeModal(true)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold rounded-lg transition"
              >
                Create First Challenge
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {challenges.map((ch) => {
                const isPendingMyAction = ch.my_participant_info?.invitation_status === 'invited';
                const isFirstToTarget = ch.challenge_type === 'first_to_target';
                const isHighest = ch.challenge_type === 'highest_by_deadline';
                const isCoop = ch.challenge_type === 'cooperative_target';

                return (
                  <div
                    key={ch.id}
                    className="p-4 bg-gray-900/60 rounded-2xl border border-gray-800/80 space-y-3"
                  >
                    {/* Top Row: Activity & Status */}
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-xl bg-gray-800 flex items-center justify-center text-xl shadow-inner">
                          {ch.activity_type.icon}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h3 className="font-bold text-sm text-gray-100">{ch.title}</h3>
                            <span
                              className={`text-[9px] px-1.5 py-0.2 rounded font-semibold uppercase tracking-wider ${
                                ch.status === 'active'
                                  ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
                                  : ch.status === 'completed'
                                  ? 'bg-purple-950/60 text-purple-400 border border-purple-800/50'
                                  : 'bg-gray-800 text-gray-400'
                              }`}
                            >
                              {ch.status}
                            </span>
                          </div>
                          <p className="text-[11px] text-gray-400 mt-0.5">
                            {isFirstToTarget && `First to ${ch.target_value} ${ch.metric.unit}`}
                            {isHighest && `Most ${ch.metric.name} by deadline`}
                            {isCoop && `Combined Goal: ${ch.target_value} ${ch.metric.unit}`}
                            {' &middot; '}
                            <span className="text-gray-500">
                              Ends {new Date(ch.ends_at).toLocaleDateString()}
                            </span>
                          </p>
                        </div>
                      </div>

                      {/* Status/Winner & Actions */}
                      <div className="flex items-center space-x-2">
                        {ch.winner && (
                          <div className="flex items-center space-x-1 text-xs font-bold text-amber-400 bg-amber-950/40 px-2.5 py-1 rounded-lg border border-amber-900/60">
                            <span>🏆</span>
                            <span>{ch.winner.display_name || ch.winner.username}</span>
                          </div>
                        )}
                        {currentUser && ch.created_by.id === currentUser.id && (ch.status === 'pending' || ch.status === 'active') && (
                          <button
                            onClick={() => handleCancelChallenge(ch.id)}
                            className="px-2 py-0.5 text-[10px] text-gray-500 hover:text-red-400 hover:bg-red-950/30 rounded border border-gray-800 hover:border-red-900/50 transition"
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Progress Section */}
                    {isCoop ? (
                      <div className="space-y-1.5 p-3 bg-gray-950/50 rounded-xl border border-gray-800/50">
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-400">Combined Progress</span>
                          <span className="font-bold text-indigo-300">
                            {ch.combined_progress || 0} / {ch.target_value} {ch.metric.unit}
                          </span>
                        </div>
                        <div className="h-2 w-full bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(
                                100,
                                (((ch.combined_progress || 0) / (ch.target_value || 1)) * 100)
                              )}%`,
                            }}
                          />
                        </div>
                        <div className="flex flex-wrap gap-2 pt-1 text-[11px] text-gray-400">
                          {ch.participants.map((p) => (
                            <span key={p.id}>
                              @{p.user.username}: {p.progress} {ch.metric.unit}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2 p-3 bg-gray-950/50 rounded-xl border border-gray-800/50">
                        {ch.participants.map((p) => {
                          const pct = ch.target_value
                            ? Math.min(100, (p.progress / ch.target_value) * 100)
                            : 0;

                          return (
                            <div key={p.id} className="space-y-1">
                              <div className="flex justify-between items-center text-xs">
                                <div className="flex items-center space-x-1.5">
                                  {p.rank && (
                                    <span className="font-mono text-[10px] text-gray-500">
                                      #{p.rank}
                                    </span>
                                  )}
                                  <span
                                    className={`font-semibold ${
                                      p.is_winner ? 'text-amber-400 font-bold' : 'text-gray-300'
                                    }`}
                                  >
                                    {p.user.display_name || p.user.username}
                                  </span>
                                  {p.is_winner && <span>🏆</span>}
                                </div>
                                <span className="text-gray-400 font-mono text-[11px]">
                                  {p.progress} {ch.metric.unit}
                                </span>
                              </div>
                              {isFirstToTarget && (
                                <div className="h-1.5 w-full bg-gray-800 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full transition-all duration-500 ${
                                      p.is_winner
                                        ? 'bg-amber-400'
                                        : 'bg-gradient-to-r from-indigo-500 to-purple-500'
                                    }`}
                                    style={{ width: `${pct}%` }}
                                  />
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Pending Invitation Actions */}
                    {isPendingMyAction && (
                      <div className="flex items-center justify-end space-x-2 pt-1 border-t border-gray-800/60">
                        <span className="text-xs text-amber-300 font-medium mr-auto">
                          You are invited!
                        </span>
                        <button
                          onClick={() => handleAcceptChallenge(ch.id)}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold rounded-lg transition"
                        >
                          Accept
                        </button>
                        <button
                          onClick={() => handleDeclineChallenge(ch.id)}
                          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs font-medium text-gray-400 rounded-lg transition"
                        >
                          Decline
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: REQUESTS */}
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

      {/* TAB 4: FIND FRIENDS (SEARCH) */}
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

      {/* CREATE CHALLENGE MODAL */}
      {showCreateChallengeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-md w-full p-5 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-2 border-b border-gray-800">
              <h3 className="font-bold text-base text-gray-100">Create Friend Challenge</h3>
              <button
                onClick={() => setShowCreateChallengeModal(false)}
                className="text-gray-400 hover:text-white p-1"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateChallengeSubmit} className="space-y-4 text-xs">
              {/* Challenge Title */}
              <div>
                <label className="block text-gray-400 mb-1 font-medium">Title (Optional)</label>
                <input
                  type="text"
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  placeholder="e.g. Weekend Sprint, 5 Game Battle"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Activity Type Selection */}
              <div>
                <label className="block text-gray-400 mb-1 font-medium">Activity</label>
                <select
                  value={createActivity?.slug || ''}
                  onChange={(e) => handleActivityChange(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-indigo-500"
                >
                  {availableActivities.map((a) => (
                    <option key={a.slug} value={a.slug}>
                      {a.icon} {a.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Metric Selection (Dynamically populated from selected activity!) */}
              <div>
                <label className="block text-gray-400 mb-1 font-medium">Metric</label>
                <select
                  value={createMetric?.slug || ''}
                  onChange={(e) => {
                    const m = createActivity?.metrics.find((x) => x.slug === e.target.value) || null;
                    setCreateMetric(m);
                  }}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-indigo-500"
                >
                  {createActivity?.metrics.map((m) => (
                    <option key={m.slug} value={m.slug}>
                      {m.name} ({m.unit || 'units'})
                    </option>
                  ))}
                </select>
              </div>

              {/* Challenge Type Selection */}
              <div>
                <label className="block text-gray-400 mb-1 font-medium">Challenge Mode</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { type: 'first_to_target' as const, label: 'First to Target' },
                    { type: 'highest_by_deadline' as const, label: 'Highest Metric' },
                    { type: 'cooperative_target' as const, label: 'Cooperative' },
                  ].map((ct) => (
                    <button
                      type="button"
                      key={ct.type}
                      onClick={() => setCreateType(ct.type)}
                      className={`p-2 rounded-xl border text-center transition ${
                        createType === ct.type
                          ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200 font-bold'
                          : 'bg-gray-800/40 border-gray-700/60 text-gray-400 hover:text-gray-200'
                      }`}
                    >
                      {ct.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Target Value (if applicable) */}
              {createType !== 'highest_by_deadline' && (
                <div>
                  <label className="block text-gray-400 mb-1 font-medium">
                    Target {createMetric?.name || 'Value'} ({createMetric?.unit || 'units'})
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={createTargetValue}
                    onChange={(e) => setCreateTargetValue(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              {/* Duration / Deadline */}
              <div>
                <label className="block text-gray-400 mb-1 font-medium">Duration</label>
                <div className="grid grid-cols-4 gap-2">
                  {[1, 3, 7, 14].map((d) => (
                    <button
                      type="button"
                      key={d}
                      onClick={() => setCreateDurationDays(d)}
                      className={`p-2 rounded-xl border text-center transition ${
                        createDurationDays === d
                          ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200 font-bold'
                          : 'bg-gray-800/40 border-gray-700/60 text-gray-400 hover:text-gray-200'
                      }`}
                    >
                      {d} {d === 1 ? 'day' : 'days'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Invite Friends */}
              <div>
                <label className="block text-gray-400 mb-1 font-medium">
                  Invite Friends ({createInvitees.length} selected)
                </label>
                {friends.length === 0 ? (
                  <p className="text-[11px] text-gray-500">
                    You have no accepted friends to invite. Connect with friends first!
                  </p>
                ) : (
                  <div className="max-h-32 overflow-y-auto space-y-1.5 p-2 bg-gray-800/40 rounded-xl border border-gray-700/40">
                    {friends.map((f) => {
                      const isChecked = createInvitees.includes(f.id);
                      return (
                        <div
                          key={f.id}
                          onClick={() => handleToggleInvitee(f.id)}
                          className={`p-2 rounded-lg cursor-pointer flex items-center justify-between transition ${
                            isChecked ? 'bg-indigo-950/60 text-indigo-200' : 'hover:bg-gray-800'
                          }`}
                        >
                          <div className="flex items-center space-x-2">
                            <span className="font-semibold">{f.display_name || f.username}</span>
                            <span className="text-[10px] text-gray-500 font-mono">@{f.username}</span>
                          </div>
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {}}
                            className="rounded bg-gray-700 border-gray-600 text-indigo-600"
                          />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={creatingChallenge || friends.length === 0}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-bold rounded-xl shadow-lg transition"
              >
                {creatingChallenge ? 'Launching...' : 'Launch Challenge 🚀'}
              </button>
            </form>
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
