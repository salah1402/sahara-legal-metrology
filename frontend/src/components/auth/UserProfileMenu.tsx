import React, { useState, useRef, useEffect } from 'react';
import type { User } from '../../types/auth';
import { LogOut, Shield, ChevronDown, Award } from 'lucide-react';

export interface UserProfileMenuProps {
  user: User | null;
  onLoginClick: () => void;
  onLogout: () => void;
}

export const UserProfileMenu: React.FC<UserProfileMenuProps> = ({
  user,
  onLoginClick,
  onLogout,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!user) {
    return (
      <button
        type="button"
        onClick={onLoginClick}
        className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-subtle"
      >
        <Shield className="w-3.5 h-3.5 text-primary-800" />
        <span>Officer Sign In</span>
      </button>
    );
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2.5 p-1.5 pr-2.5 rounded-lg hover:bg-slate-100 transition-colors focus:outline-none"
      >
        <div className="w-7 h-7 rounded-full bg-primary-800 text-white flex items-center justify-center text-xs font-semibold shadow-subtle">
          {user.name.slice(0, 2).toUpperCase()}
        </div>
        <div className="hidden md:flex flex-col text-left">
          <span className="text-xs font-medium text-slate-800 leading-tight">{user.name}</span>
          <span className="text-[10px] text-slate-500 leading-none">{user.badgeId}</span>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-modal border border-slate-200/90 py-2 z-50 animate-slide-down">
          <div className="px-4 py-2 border-b border-slate-100">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-primary-800 uppercase tracking-wider mb-1">
              <Award className="w-3.5 h-3.5" />
              <span>{user.designation}</span>
            </div>
            <p className="text-xs font-semibold text-slate-900">{user.name}</p>
            <p className="text-[11px] text-slate-500 truncate">{user.email}</p>
            <div className="mt-2 text-[10px] bg-slate-50 p-2 rounded border border-slate-100 text-slate-600">
              <p><span className="font-semibold">Dept:</span> {user.department}</p>
              <p><span className="font-semibold">Jurisdiction:</span> {user.jurisdictionZone}</p>
            </div>
          </div>

          <div className="pt-1">
            <button
              onClick={() => {
                setIsOpen(false);
                onLogout();
              }}
              className="w-full flex items-center gap-2 px-4 py-2 text-xs text-rose-700 hover:bg-rose-50 transition-colors text-left font-medium"
            >
              <LogOut className="w-4 h-4 text-rose-600" />
              <span>Sign Out of Terminal</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
