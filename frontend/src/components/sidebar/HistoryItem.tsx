import React, { useState, useRef, useEffect } from 'react';
import type { InspectionMetadata } from '../../types/inspection';
import { StatusChip } from '../common/StatusChip';
import { formatTimeAgo, getInspectionDisplayTitle } from '../../utils/formatters';
import { Trash2, Edit2, Check, X, RotateCcw } from 'lucide-react';
import { clsx } from 'clsx';

export interface HistoryItemProps {
  item: InspectionMetadata;
  isActive?: boolean;
  onSelect: () => void;
  onDelete?: () => void;
  onRename?: (id: string, newName: string) => void;
}

export const HistoryItem: React.FC<HistoryItemProps> = ({
  item,
  isActive = false,
  onSelect,
  onDelete,
  onRename,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const displayTitle = getInspectionDisplayTitle(item);
  const [editValue, setEditValue] = useState(displayTitle);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setEditValue(getInspectionDisplayTitle(item));
  }, [item.display_name, item.product_name]);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  const handleSaveRename = (e?: React.MouseEvent | React.FormEvent) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    const trimmed = editValue.trim();
    if (onRename) {
      onRename(item.inspection_id, trimmed);
    }
    setIsEditing(false);
  };

  const handleResetName = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onRename) {
      onRename(item.inspection_id, '');
    }
    setIsEditing(false);
  };

  const handleCancelRename = (e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    setEditValue(displayTitle);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveRename();
    } else if (e.key === 'Escape') {
      handleCancelRename();
    }
  };

  return (
    <div
      onClick={isEditing ? undefined : onSelect}
      className={clsx(
        'group relative p-2 rounded-xl border transition-all duration-150 cursor-pointer select-none text-left',
        isActive
          ? 'bg-white border-primary-800 shadow-sm ring-1 ring-primary-800'
          : 'bg-white/80 hover:bg-white border-slate-200/80 hover:border-slate-300 shadow-2xs'
      )}
    >
      {/* Inline Rename Form */}
      {isEditing ? (
        <div className="space-y-1" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center gap-1">
            <input
              ref={inputRef}
              type="text"
              value={editValue}
              placeholder="Enter title or leave blank to reset"
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              maxLength={120}
              className="w-full px-2 py-0.5 text-xs bg-white border border-primary-700 rounded focus:outline-none text-slate-900 font-medium"
            />
            <button
              type="button"
              onClick={handleSaveRename}
              className="p-1 text-emerald-600 hover:bg-emerald-50 rounded"
              title="Save title"
            >
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleCancelRename}
              className="p-1 text-slate-400 hover:bg-slate-100 rounded"
              title="Cancel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          {item.display_name && (
            <button
              type="button"
              onClick={handleResetName}
              className="text-[10px] text-slate-500 hover:text-primary-800 flex items-center gap-1 font-medium"
              title="Reset to automatic name"
            >
              <RotateCcw className="w-2.5 h-2.5" />
              <span>Reset to default name</span>
            </button>
          )}
        </div>
      ) : (
        /* Compact 2-Line Row Layout */
        <div className="space-y-1">
          {/* Top Line: Product Name & Relative Time */}
          <div className="flex items-center justify-between gap-1.5">
            <span
              className="text-xs font-bold text-slate-900 truncate leading-snug flex-1"
              title={displayTitle}
            >
              {displayTitle}
            </span>
            <span className="text-[10px] text-slate-400 font-mono whitespace-nowrap flex-shrink-0">
              {formatTimeAgo(item.created_at)}
            </span>
          </div>

          {/* Bottom Line: Compact Status & Hover Actions */}
          <div className="flex items-center justify-between gap-1">
            <StatusChip status={item.status} size="sm" showIcon={false} />

            {/* Hover Action Icons */}
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              {onRename && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsEditing(true);
                  }}
                  className="p-1 text-slate-400 hover:text-primary-800 hover:bg-primary-50 rounded transition-all"
                  title="Rename inspection"
                  aria-label="Rename inspection"
                >
                  <Edit2 className="w-3 h-3" />
                </button>
              )}

              {onDelete && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete();
                  }}
                  className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-all"
                  title="Delete inspection"
                  aria-label="Delete inspection"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
