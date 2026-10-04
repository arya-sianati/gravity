import { Outlet, NavLink } from 'react-router-dom';

export const AppShell: React.FC = () => {
  return (
    <div className="flex flex-col h-full w-full max-w-md mx-auto bg-black relative shadow-lg overflow-hidden">
      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative overflow-hidden">
        <Outlet />
      </main>

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
