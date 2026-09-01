import React from 'react';
import { Menu, Scale, RefreshCw } from 'lucide-react';
import { UserProfileMenu } from '../auth/UserProfileMenu';
import type { User } from '../../types/auth';

export interface TopNavigationProps {
  onToggleSidebar: () => void;
  user: User | null;
  onLoginClick: () => void;
  onLogout: () => void;
  activeInspectionId: string | null;
  onReloadHistory: () => void;
}

export const TopNavigation: React.FC<TopNavigationProps> = ({
  onToggleSidebar,
  user,
  onLoginClick,
  onLogout,
  activeInspectionId,
  onReloadHistory,
}) => {
  return (
    <header className="h-14 bg-white border-b border-slate-200 px-3 sm:px-6 flex items-center justify-between gap-2 sm:gap-4 select-none sticky top-0 z-30 w-full">
      {/* Left: Mobile hamburger & breadcrumb / brand */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-2 -ml-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg lg:hidden flex items-center justify-center min-w-[40px] min-h-[40px]"
          aria-label="Open inspection history drawer"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Mobile Brand Name */}
        <div className="flex items-center gap-1.5 lg:hidden">
          <span className="text-sm font-bold text-slate-900 tracking-tight">SAHARA</span>
          <span className="text-[9px] font-mono font-medium text-primary-800 bg-primary-50 px-1 py-0.2 rounded border border-primary-200">
            LM
          </span>
        </div>

        {/* Desktop Breadcrumb */}
        <div className="hidden lg:flex items-center gap-2 text-xs min-w-0">
          <div className="flex items-center gap-1.5 text-slate-600 font-medium whitespace-nowrap">
            <Scale className="w-4 h-4 text-primary-800" />
            <span>Legal Metrology Inspection Workspace</span>
          </div>

          {activeInspectionId && (
            <>
              <span className="text-slate-300">/</span>
              <span className="font-mono text-[11px] font-semibold text-primary-800 bg-primary-50 px-2 py-0.5 rounded border border-primary-200 truncate max-w-[200px]">
                {activeInspectionId}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Right: Actions & User Auth */}
      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
        <button
          type="button"
          onClick={onReloadHistory}
          className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors hidden sm:flex items-center justify-center min-w-[36px] min-h-[36px]"
          title="Refresh inspection records"
          aria-label="Refresh inspection records"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        <div className="h-4 w-px bg-slate-200 hidden sm:block" />

        <UserProfileMenu
          user={user}
          onLoginClick={onLoginClick}
          onLogout={onLogout}
        />
      </div>
    </header>
  );
};
