import { Outlet, NavLink } from 'react-router-dom';
import { useActiveSession } from '../context/ActiveSessionContext';

export const AppShell: React.FC = () => {
  const { xpFeedback } = useActiveSession();

  return (
    <div className="flex flex-col h-full w-full max-w-md mx-auto bg-black relative shadow-lg overflow-hidden">
      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative overflow-hidden">
        <Outlet />
      </main>

      {/* XP Overlay Toast */}
      {xpFeedback && (
        <div className="absolute top-10 left-1/2 -translate-x-1/2 z-50 animate-bounce flex flex-col items-center pointer-events-none gap-2 w-full px-4 max-w-sm">
          <div className="bg-indigo-600/90 backdrop-blur-md px-6 py-3 rounded-full text-white font-bold text-lg shadow-[0_0_20px_rgba(79,70,229,0.5)] border border-indigo-400 whitespace-nowrap">
            +{xpFeedback.amount} XP
          </div>
          {xpFeedback.levelUp && (
            <div className="bg-yellow-500 text-black px-4 py-1 rounded-full font-black text-sm uppercase tracking-widest shadow-[0_0_15px_rgba(234,179,8,0.6)] whitespace-nowrap">
              Level Up! Lv {xpFeedback.newLevel}
            </div>
          )}
          {xpFeedback.badges_earned?.map(b => (
            <div key={b.slug} className="bg-amber-600/95 text-white px-4 py-2 rounded-xl font-bold text-sm shadow-[0_0_15px_rgba(217,119,6,0.6)] border border-amber-400 flex items-center space-x-2 w-max">
              <span className="text-xl">{b.icon}</span>
              <span>{b.name} Earned!</span>
            </div>
          ))}
        </div>
      )}

      {/* Bottom Navigation */}
      <nav className="h-16 bg-gray-950 border-t border-gray-800 flex justify-around items-center px-2 z-40 pb-safe">
        <NavItem to="/" label="Map" icon="M" />
        <NavItem to="/leaderboards" label="Rank" icon="L" />
        <NavItem to="/start" label="Start" icon="+" isPrimary />
        <NavItem to="/friends" label="Friends" icon="F" />
        <NavItem to="/profile" label="Profile" icon="U" />
      </nav>
    </div>
  );
};

const NavItem: React.FC<{ to: string; label: string; icon: string; isPrimary?: boolean }> = ({ to, label, icon, isPrimary }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex flex-col items-center justify-center w-14 h-14 rounded-full transition-colors ${
          isPrimary
            ? 'bg-indigo-600 text-white shadow-lg -translate-y-4 shadow-indigo-600/30'
            : isActive
            ? 'text-indigo-400'
            : 'text-gray-500 hover:text-gray-300'
        }`
      }
    >
      <div className="text-xl font-bold">{icon}</div>
      {!isPrimary && <span className="text-[10px] mt-1">{label}</span>}
    </NavLink>
  );
};
