import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { MapScreen } from './screens/MapScreen';
import { PulseScreen } from './screens/PulseScreen';
import { FriendsScreen } from './screens/FriendsScreen';
import { ProfileScreen } from './screens/ProfileScreen';
import { StartActivityScreen } from './screens/StartActivityScreen';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<MapScreen />} />
          <Route path="pulse" element={<PulseScreen />} />
          <Route path="friends" element={<FriendsScreen />} />
          <Route path="profile" element={<ProfileScreen />} />
          <Route path="start" element={<StartActivityScreen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
