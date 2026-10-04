import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ActiveSessionProvider } from './context/ActiveSessionContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppShell } from './components/AppShell';

// Route-level code-splitting (Requirements 41, 42, 43)
const LoginScreen = lazy(() => import('./screens/LoginScreen').then((m) => ({ default: m.LoginScreen })));
const RegisterScreen = lazy(() => import('./screens/RegisterScreen').then((m) => ({ default: m.RegisterScreen })));
const MapScreen = lazy(() => import('./screens/MapScreen').then((m) => ({ default: m.MapScreen })));
const PulseScreen = lazy(() => import('./screens/PulseScreen').then((m) => ({ default: m.PulseScreen })));
const FriendsScreen = lazy(() => import('./screens/FriendsScreen').then((m) => ({ default: m.FriendsScreen })));
const ProfileScreen = lazy(() => import('./screens/ProfileScreen').then((m) => ({ default: m.ProfileScreen })));
const StartActivityScreen = lazy(() => import('./screens/StartActivityScreen').then((m) => ({ default: m.StartActivityScreen })));
const QRJoinScreen = lazy(() => import('./screens/QRJoinScreen').then((m) => ({ default: m.QRJoinScreen })));
const LeaderboardScreen = lazy(() => import('./screens/LeaderboardScreen').then((m) => ({ default: m.LeaderboardScreen })));

const ScreenFallback = () => (
  <div className="flex-1 w-full h-full flex flex-col items-center justify-center bg-gray-950 text-gray-400">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mb-2"></div>
    <span className="text-xs font-medium">Loading Gravity...</span>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ActiveSessionProvider>
          <Suspense fallback={<ScreenFallback />}>
            <Routes>
              {/* Public Auth Routes */}
              <Route path="/login" element={<LoginScreen />} />
              <Route path="/register" element={<RegisterScreen />} />
              <Route path="/join/:token" element={<ProtectedRoute><QRJoinScreen /></ProtectedRoute>} />

              {/* Protected Application Routes */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppShell />
                  </ProtectedRoute>
                }
              >
                <Route index element={<MapScreen />} />
                <Route path="pulse" element={<PulseScreen />} />
                <Route path="leaderboards" element={<LeaderboardScreen />} />
                <Route path="friends" element={<FriendsScreen />} />
                <Route path="profile" element={<ProfileScreen />} />
                <Route path="start" element={<StartActivityScreen />} />
              </Route>
            </Routes>
          </Suspense>
        </ActiveSessionProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
