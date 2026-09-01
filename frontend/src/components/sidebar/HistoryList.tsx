import React from 'react';
import type { InspectionMetadata } from '../../types/inspection';
import { HistoryItem } from './HistoryItem';
import { EmptyState } from '../common/EmptyState';
import { Search, PackageOpen } from 'lucide-react';

export interface HistoryListProps {
  items: InspectionMetadata[];
  activeId?: string | null;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  onSelectItem: (id: string) => void;
  onDeleteItem: (id: string) => void;
  onRenameItem?: (id: string, newName: string) => void;
  onNewInspectionClick?: () => void;
}

const FILTER_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'needs_review', label: 'Needs Review' },
  { key: 'passed', label: 'Passed' },
  { key: 'failed', label: 'Failed' },
] as const;

export const HistoryList: React.FC<HistoryListProps> = ({
  items,
  activeId,
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  onSelectItem,
  onDeleteItem,
  onRenameItem,
}) => {
  return (
    <div className="flex flex-col h-full space-y-2.5">
      {/* Search Input */}
      <div className="relative">
        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search inspections..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-100 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-1 focus:ring-primary-800 text-slate-800 placeholder-slate-400"
        />
      </div>

      {/* Quick Filter Tabs: All, Needs Review, Passed, Failed */}
      <div className="flex items-center gap-1 overflow-x-auto pb-0.5 text-xs">
        {FILTER_OPTIONS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => onStatusFilterChange(f.key)}
            className={`px-2 py-1 rounded-md text-[11px] font-medium whitespace-nowrap transition-colors ${
              statusFilter === f.key
                ? 'bg-slate-900 text-white font-semibold shadow-2xs'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Items Scrollable List */}
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-0.5">
        {items.length === 0 ? (
          <EmptyState
            icon={<PackageOpen className="w-6 h-6 text-slate-400" />}
            title="No inspections found"
            description="Upload or capture a packaged commodity label to start an inspection."
            className="py-6 px-2"
          />
        ) : (
          items.map((item) => (
            <HistoryItem
              key={item.inspection_id}
              item={item}
              isActive={activeId === item.inspection_id}
              onSelect={() => onSelectItem(item.inspection_id)}
              onDelete={() => onDeleteItem(item.inspection_id)}
              onRename={onRenameItem}
            />
          ))
        )}
      </div>
    </div>
  );
};
