import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Egg, Lock, User } from 'lucide-react';

import { useAuth } from '../hooks/useAuth';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogin = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    const success = await login(username, password);
    if (success) {
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    } else {
      setError('Invalid credentials. Please try again.');
    }
    setIsLoading(false);
  };

  return (
    <div className="flex min-h-screen flex-col justify-center bg-[#F8FAFC] px-4 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex flex-col items-center justify-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-[1.7rem] bg-yolk-yellow shadow-[0_18px_40px_rgba(245,158,11,0.28)]">
            <Egg className="h-10 w-10 text-white" />
          </div>
          <h2 className="mt-6 flex items-center gap-2 text-center text-4xl font-extrabold tracking-tight text-dark-slate">
            Egg<span className="text-yolk-yellow">Sentry</span>
          </h2>
          <p className="mt-2 text-center text-sm font-semibold tracking-[0.22em] text-slate-400">
            USEP POULTRY
          </p>
          <p className="mt-2 text-center text-sm text-slate-500">
            Egg Counter with Tracking System
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="relative overflow-hidden border border-slate-200/80 bg-white px-4 py-8 shadow-[0_28px_70px_rgba(15,23,42,0.08)] sm:rounded-[1.75rem] sm:px-10">
          <div className="absolute left-0 top-0 h-1 w-full bg-yolk-yellow"></div>

          <form className="space-y-6" onSubmit={handleLogin}>
            <div className="space-y-1">
              <h3 className="text-xl font-bold text-dark-slate">Welcome Back</h3>
              <p className="text-sm leading-6 text-slate-500">
                Sign in to access your egg production dashboard
              </p>
            </div>

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-dark-slate">
                Username
              </label>
              <div className="relative mt-2">
                <User className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="block w-full rounded-xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-dark-slate shadow-sm outline-none transition focus:border-yolk-yellow focus:ring-3 focus:ring-amber-100"
                  placeholder="Enter your username"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-dark-slate">
                Password
              </label>
              <div className="relative mt-2">
                <Lock className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="block w-full rounded-xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-dark-slate shadow-sm outline-none transition focus:border-yolk-yellow focus:ring-3 focus:ring-amber-100"
                  placeholder="••••••••"
                />
              </div>
            </div>

            {error ? (
              <div className="flex items-start rounded-xl bg-red-50 p-3 text-sm text-alert-red">
                <span className="block sm:inline">{error}</span>
              </div>
            ) : null}

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-transparent bg-yolk-yellow px-4 py-3 text-sm font-semibold text-white shadow-[0_14px_32px_rgba(245,158,11,0.28)] transition hover:bg-amber-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yolk-yellow disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span>{isLoading ? 'Logging in...' : 'Login'}</span>
                {!isLoading ? <ArrowRight className="h-4 w-4" /> : null}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
