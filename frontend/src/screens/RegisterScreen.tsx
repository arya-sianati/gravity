import { useState } from 'react';
import { useNavigate, useLocation, Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const RegisterScreen: React.FC = () => {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';
  if (user) {
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!username.trim() || !password) {
      setError('Username and password are required.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    try {
      setSubmitting(true);
      await register({
        username: username.trim(),
        display_name: displayName.trim() || undefined,
        email: email.trim() || undefined,
        password,
      });
      navigate(from, { replace: true });
    } catch (err: any) {
      const data = err.response?.data;
      if (data?.username) {
        setError(Array.isArray(data.username) ? data.username[0] : data.username);
      } else if (data?.password) {
        setError(Array.isArray(data.password) ? data.password[0] : data.password);
      } else if (data?.detail) {
        setError(data.detail);
      } else {
        setError('Registration failed. Please verify your details.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[100dvh] max-w-md mx-auto bg-black text-white p-6 justify-center pt-safe pb-safe overflow-y-auto">
      <div className="mb-6 text-center">
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
          GRAVITY
        </h1>
        <p className="text-gray-400 text-sm mt-2">Join the movement</p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-950/60 border border-red-800 rounded-lg text-red-200 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1">
            Username *
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={submitting}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-sm"
            placeholder="Choose username"
            autoComplete="username"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1">
            Display Name
          </label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            disabled={submitting}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-sm"
            placeholder="Public display name"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1">
            Email (optional)
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={submitting}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-sm"
            placeholder="name@example.com"
            autoComplete="email"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1">
            Password (min 8 chars) *
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={submitting}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-sm"
            placeholder="Password"
            autoComplete="new-password"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1">
            Confirm Password *
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={submitting}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-sm"
            placeholder="Confirm password"
            autoComplete="new-password"
            required
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full mt-3 py-3 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors shadow-lg shadow-indigo-600/30"
        >
          {submitting ? 'Creating account...' : 'Create Account'}
        </button>
      </form>

      <div className="mt-5 text-center text-xs text-gray-400">
        Already have an account?{' '}
        <Link to="/login" state={{ from: location.state?.from }} className="text-indigo-400 hover:underline font-medium">
          Sign In
        </Link>
      </div>
    </div>
  );
};
