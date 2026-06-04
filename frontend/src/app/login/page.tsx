'use client';

import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Zap, Mail, Lock, AlertTriangle, Cpu } from 'lucide-react';

export default function LoginPage() {
  const { login, loading } = useAuth();
  const router = useRouter();

  // Form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Validation / Error states
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [generalError, setGeneralError] = useState('');

  // Regex for basic email format
  const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const validate = () => {
    let isValid = true;

    if (!email.trim()) {
      setEmailError('Email is required');
      isValid = false;
    } else if (!EMAIL_REGEX.test(email)) {
      setEmailError('Please enter a valid email address');
      isValid = false;
    } else {
      setEmailError('');
    }

    if (!password) {
      setPasswordError('Password is required');
      isValid = false;
    } else if (password.length < 6) {
      setPasswordError('Password must be at least 6 characters');
      isValid = false;
    } else {
      setPasswordError('');
    }

    return isValid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError('');

    if (!validate()) return;

    try {
      await login({ email, password });
      router.push('/');
    } catch (err: any) {
      // Show backend error
      const message = err.message || 'Incorrect email or password. Please try again.';
      setGeneralError(message.replace('API Error 401:', '').replace('API Error 400:', '').trim());
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 p-4 font-sans relative overflow-hidden">
      {/* Dynamic Cybernetic/Grid Background Accents */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-35" />
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-violet-900/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-cyan-900/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Login Card */}
      <div className="w-full max-w-md bg-slate-900/30 backdrop-blur-xl border border-slate-800/80 rounded-xl p-8 relative shadow-2xl z-10 flex flex-col gap-6">
        {/* Glowing Corner Accents */}
        <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-violet-500 rounded-tl-sm pointer-events-none" />
        <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-violet-500 rounded-tr-sm pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-cyan-500 rounded-bl-sm pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-cyan-500 rounded-br-sm pointer-events-none" />

        {/* Brand Header */}
        <div className="flex flex-col items-center text-center gap-2">
          <div className="h-10 w-10 bg-violet-600 rounded-lg flex items-center justify-center shadow-lg shadow-violet-500/25">
            <Zap className="h-5 w-5 text-white animate-pulse" />
          </div>
          <h2 className="text-sm font-semibold tracking-[0.2em] text-transparent bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text font-mono uppercase mt-2">
            Marketing Agent OS
          </h2>
          <p className="text-xs text-slate-500 font-mono uppercase tracking-wider">
            Enterprise Decoupled JWT Gateway
          </p>
        </div>

        {/* Terminal Status Panel */}
        <div className="bg-slate-950 border border-slate-900 rounded p-3 font-mono text-[10px] text-slate-400 space-y-1 select-none">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-500"></span>
            <span>SYSTEM GATEWAY: ONLINE</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-violet-500"></span>
            <span>RESTRICTION: SECURE ENCRYPTED JWT</span>
          </div>
        </div>

        {/* General Error Alert */}
        {generalError && (
          <div className="flex items-start gap-2 bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs px-3.5 py-3 rounded font-mono">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-450 mt-0.5" />
            <div>
              <span className="font-bold text-rose-400 uppercase mr-1">Auth Failure:</span>
              {generalError}
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Email Input */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] font-bold tracking-widest text-slate-400 uppercase font-mono">
              Email Address
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <Mail className="h-4 w-4" />
              </span>
              <input
                type="email"
                placeholder="developer@agent-os.local"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (emailError) setEmailError('');
                }}
                disabled={loading}
                className={`w-full bg-slate-950/80 border text-slate-200 focus:border-violet-500 focus:ring-1 focus:ring-violet-500 rounded pl-10 pr-3 py-2 text-sm outline-none transition-all font-mono placeholder:text-slate-700 ${
                  emailError ? 'border-rose-500/50' : 'border-slate-800'
                }`}
              />
            </div>
            {emailError && (
              <span className="text-[10px] font-mono text-rose-400">{emailError}</span>
            )}
          </div>

          {/* Password Input */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] font-bold tracking-widest text-slate-400 uppercase font-mono">
              Secure Credentials
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <Lock className="h-4 w-4" />
              </span>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (passwordError) setPasswordError('');
                }}
                disabled={loading}
                className={`w-full bg-slate-950/80 border text-slate-200 focus:border-violet-500 focus:ring-1 focus:ring-violet-500 rounded pl-10 pr-3 py-2 text-sm outline-none transition-all font-mono placeholder:text-slate-700 ${
                  passwordError ? 'border-rose-500/50' : 'border-slate-800'
                }`}
              />
            </div>
            {passwordError && (
              <span className="text-[10px] font-mono text-rose-400">{passwordError}</span>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white font-bold uppercase tracking-widest text-xs py-2.5 rounded border border-violet-500/20 shadow-lg shadow-violet-500/10 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed mt-2 h-10"
          >
            {loading ? (
              <>
                <Cpu className="h-4 w-4 animate-spin text-cyan-200" />
                <span>Authorizing Session...</span>
              </>
            ) : (
              <span>INITIALIZE AUTHENTICATION</span>
            )}
          </button>
        </form>

        {/* Footer Link */}
        <div className="text-center font-mono text-xs text-slate-500 border-t border-slate-900 pt-4 flex flex-col gap-1 select-none">
          <span>First time accessing telemetry?</span>
          <Link
            href="/register"
            className="text-cyan-400 hover:text-cyan-300 font-bold uppercase tracking-wider transition-all"
          >
            Register Core Node &rarr;
          </Link>
        </div>
      </div>
    </main>
  );
}
