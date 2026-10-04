import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ActiveSessionProvider } from './context/ActiveSessionContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppShell } from './components/AppShell';
import { LoginScreen } from './screens/LoginScreen';
import { RegisterScreen } from './screens/RegisterScreen';
import { MapScreen } from './screens/MapScreen';
import { PulseScreen } from './screens/PulseScreen';
import { FriendsScreen } from './screens/FriendsScreen';
import { ProfileScreen } from './screens/ProfileScreen';
import { StartActivityScreen } from './screens/StartActivityScreen';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ActiveSessionProvider>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<LoginScreen />} />
            <Route path="/register" element={<RegisterScreen />} />

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
              <Route path="friends" element={<FriendsScreen />} />
              <Route path="profile" element={<ProfileScreen />} />
              <Route path="start" element={<StartActivityScreen />} />
            </Route>
          </Routes>
        </ActiveSessionProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
