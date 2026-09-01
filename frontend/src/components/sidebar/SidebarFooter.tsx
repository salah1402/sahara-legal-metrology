import React from 'react';
import { Settings, Cpu } from 'lucide-react';
import { getApiConfig } from '../../services/api';

export interface SidebarFooterProps {
  onOpenSettings: () => void;
}

export const SidebarFooter: React.FC<SidebarFooterProps> = ({ onOpenSettings }) => {
  const config = getApiConfig();

  return (
    <div className="pt-3 border-t border-slate-200/80 space-y-2">
      {/* Backend Engine Status Pill */}
      <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-slate-100/90 text-[11px] text-slate-600">
        <div className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-primary-800" />
          <span className="font-medium">Backend Service:</span>
        </div>
        <span className="font-mono text-[10px] px-1.5 py-0.2 bg-white rounded border border-slate-200 text-slate-700">
          {config.useDemoFixtures ? 'Demo Adapter' : 'Live Engine'}
        </span>
      </div>

      {/* Action links */}
      <div className="flex items-center justify-between px-1 text-xs">
        <button
          type="button"
          onClick={onOpenSettings}
          className="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 transition-colors p-1 rounded hover:bg-slate-100"
        >
          <Settings className="w-3.5 h-3.5" />
          <span>Settings</span>
        </button>

        <span className="text-[10px] text-slate-400 font-mono">
          v1.0 • PCR 2011
        </span>
      </div>
    </div>
  );
};
