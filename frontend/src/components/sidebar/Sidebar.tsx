import React from 'react';
import type { InspectionMetadata } from '../../types/inspection';
import { HistoryList } from './HistoryList';
import { SidebarFooter } from './SidebarFooter';
import { Button } from '../common/Button';
import { Plus, X, ShieldCheck } from 'lucide-react';
import { clsx } from 'clsx';

export interface SidebarProps {
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  historyList: InspectionMetadata[];
  activeInspectionId: string | null;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  onSelectInspection: (id: string) => void;
  onDeleteInspection: (id: string) => void;
  onRenameInspection?: (id: string, newName: string) => void;
  onNewInspection: () => void;
  onOpenSettings: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpenMobile,
  onCloseMobile,
  historyList,
  activeInspectionId,
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  onSelectInspection,
  onDeleteInspection,
  onRenameInspection,
  onNewInspection,
  onOpenSettings,
}) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-40 lg:hidden transition-opacity duration-200"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Drawer Container */}
      <aside
        className={clsx(
          'fixed lg:static top-0 bottom-0 left-0 z-50 w-[85vw] max-w-[310px] sm:w-80 bg-[#FBFBFA] border-r border-slate-200 flex flex-col p-3.5 sm:p-4 transition-transform duration-200 ease-in-out',
          isOpenMobile ? 'translate-x-0 shadow-2xl' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* SAHARA App Branding & Mobile Close */}
        <div className="flex items-center justify-between pb-3.5 border-b border-slate-200/80 mb-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-white shadow-subtle flex-shrink-0">
              <ShieldCheck className="w-5 h-5 text-sky-400" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-1">
                <span>SAHARA</span>
                <span className="text-[9px] font-mono font-medium text-primary-800 bg-primary-50 px-1 py-0.2 rounded border border-primary-200">
                  LM
                </span>
              </h1>
              <p className="text-[10px] text-slate-500 truncate leading-tight">
                Legal Metrology Inspection System
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onCloseMobile}
            className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg lg:hidden flex items-center justify-center min-w-[36px] min-h-[36px]"
            aria-label="Close sidebar drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* New Inspection Primary CTA */}
        <div className="mb-3">
          <Button
            type="button"
            variant="primary"
            size="md"
            className="w-full justify-center min-h-[40px]"
            onClick={onNewInspection}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            New Inspection
          </Button>
        </div>

        {/* Scrollable History List with quick filters */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <HistoryList
            items={historyList}
            activeId={activeInspectionId}
            searchQuery={searchQuery}
            onSearchChange={onSearchChange}
            statusFilter={statusFilter}
            onStatusFilterChange={onStatusFilterChange}
            onSelectItem={onSelectInspection}
            onDeleteItem={onDeleteInspection}
            onRenameItem={onRenameInspection}
          />
        </div>

        {/* Sidebar Footer */}
        <div className="pt-2.5 border-t border-slate-200/80 mt-2">
          <SidebarFooter onOpenSettings={onOpenSettings} />
        </div>
      </aside>
    </>
  );
};
