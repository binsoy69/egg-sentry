import React from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Camera, History, LayoutDashboard, LogOut, Egg, Settings } from 'lucide-react';

import { useAuth } from '../../hooks/useAuth';

const Navbar = () => {
  const { isAuthenticated, logout, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  if (!isAuthenticated) return null;

  const getNavClass = ({ isActive }) =>
    `flex items-center px-4 py-2 rounded-full transition-colors duration-200 ${
      isActive
        ? 'bg-amber-50 text-yolk-yellow font-semibold'
        : 'text-slate-500 hover:bg-slate-50 hover:text-dark-slate'
    }`;

  const modifyButtonClass = `flex items-center px-4 py-2 rounded-full transition-colors duration-200 ${
    location.pathname === '/' && location.search.includes('modifyCamera=1')
      ? 'bg-amber-50 text-yolk-yellow font-semibold'
      : 'text-slate-500 hover:bg-slate-50 hover:text-dark-slate'
  }`;

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/95 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 justify-between">
          <div className="flex">
            <div className="flex flex-shrink-0 items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-yolk-yellow">
                <Egg className="h-5 w-5 text-white" />
              </div>
              <div className="leading-tight">
                <span className="block text-lg font-bold text-dark-slate">
                  Egg<span className="text-yolk-yellow">Sentry</span>
                </span>
                <span className="block text-[10px] font-semibold tracking-[0.22em] text-slate-400">
                  USEP POULTRY
                </span>
              </div>
            </div>

            <div className="hidden sm:ml-8 sm:flex sm:items-center sm:space-x-2">
              <NavLink to="/" className={getNavClass} end>
                <LayoutDashboard className="mr-2 h-4 w-4" />
                Dashboard
              </NavLink>
              <NavLink to="/history" className={getNavClass}>
                <History className="mr-2 h-4 w-4" />
                History
              </NavLink>
              <NavLink to="/settings" className={getNavClass}>
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </NavLink>
              <button
                type="button"
                onClick={() => navigate('/?modifyCamera=1')}
                className={modifyButtonClass}
              >
                <Camera className="mr-2 h-4 w-4" />
                Modify Camera
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <span className="hidden text-sm font-medium text-slate-500 sm:block">
              {user?.display_name || user?.username}
            </span>
            <button
              onClick={logout}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-500 transition-colors duration-200 hover:bg-red-50 hover:text-alert-red"
              title="Logout"
            >
              <span className="inline-flex items-center gap-2">
                <LogOut className="h-4 w-4" />
                Logout
              </span>
            </button>
          </div>
        </div>
      </div>

      <div className="flex justify-around border-t border-gray-100 bg-white py-2 sm:hidden">
        <NavLink to="/" className={({ isActive }) => `flex flex-col items-center p-2 rounded-lg ${isActive ? 'text-yolk-yellow' : 'text-slate-500'}`} end>
          <LayoutDashboard className="h-5 w-5" />
          <span className="mt-1 text-[10px] font-medium">Dashboard</span>
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => `flex flex-col items-center p-2 rounded-lg ${isActive ? 'text-yolk-yellow' : 'text-slate-500'}`}>
          <History className="h-5 w-5" />
          <span className="mt-1 text-[10px] font-medium">History</span>
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `flex flex-col items-center p-2 rounded-lg ${isActive ? 'text-yolk-yellow' : 'text-slate-500'}`}>
          <Settings className="h-5 w-5" />
          <span className="mt-1 text-[10px] font-medium">Settings</span>
        </NavLink>
        <button
          type="button"
          onClick={() => navigate('/?modifyCamera=1')}
          className={`flex flex-col items-center p-2 rounded-lg ${
            location.pathname === '/' && location.search.includes('modifyCamera=1') ? 'text-yolk-yellow' : 'text-slate-500'
          }`}
        >
          <Camera className="h-5 w-5" />
          <span className="mt-1 text-[10px] font-medium">Modify</span>
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
