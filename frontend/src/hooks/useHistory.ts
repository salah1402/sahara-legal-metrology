import { useState, useEffect, useCallback } from 'react';
import type { InspectionMetadata } from '../types/inspection';
import * as inspectionService from '../services/inspectionService';
import { showToast } from './useToast';

export function useHistory() {
  const [historyList, setHistoryList] = useState<InspectionMetadata[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);

  const reloadHistory = useCallback(async () => {
    setIsLoading(true);
    try {
      const list = await inspectionService.listInspections();
      setHistoryList(list);
    } catch (e) {
      console.error('Failed to load history list', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    reloadHistory();
  }, [reloadHistory]);

  const deleteInspection = useCallback(async (id: string) => {
    try {
      await inspectionService.deleteInspection(id);
      setHistoryList(prev => prev.filter(item => item.inspection_id !== id));
      showToast('info', 'Record Removed', 'Inspection record deleted from history.');
    } catch (e) {
      showToast('error', 'Error', 'Failed to delete record.');
    }
  }, []);

  const renameInspection = useCallback(async (id: string, displayName: string) => {
    const trimmed = displayName.trim();
    if (!trimmed) {
      showToast('warning', 'Invalid Name', 'Inspection title cannot be empty.');
      return;
    }

    try {
      const updated = await inspectionService.renameInspection(id, trimmed);
      setHistoryList(prev =>
        prev.map(item =>
          item.inspection_id === id ? { ...item, display_name: trimmed, updated_at: updated.updated_at } : item
        )
      );
      showToast('success', 'Renamed', `Inspection renamed to "${trimmed}".`);
    } catch (e) {
      showToast('error', 'Rename Failed', 'Unable to rename inspection.');
    }
  }, []);

  const filteredHistory = historyList.filter(item => {
    const matchesQuery = 
      !searchQuery ||
      item.inspection_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.display_name && item.display_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.product_name && item.product_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.brand_name && item.brand_name.toLowerCase().includes(searchQuery.toLowerCase()));

    const rawStatus = (item.status || '').toLowerCase().replace(/\s+/g, '_');
    const matchesStatus = 
      statusFilter === 'all' || 
      (statusFilter === 'passed' && (rawStatus.includes('pass') || (rawStatus.includes('compliant') && !rawStatus.includes('non')))) ||
      (statusFilter === 'failed' && (rawStatus.includes('fail') || rawStatus.includes('non_compliant') || rawStatus.includes('non-compliant'))) ||
      (statusFilter === 'needs_review' && rawStatus.includes('review')) ||
      rawStatus === statusFilter.toLowerCase();

    return matchesQuery && matchesStatus;
  });

  return {
    historyList: filteredHistory,
    totalCount: historyList.length,
    searchQuery,
    setSearchQuery,
    statusFilter,
    setStatusFilter,
    isLoading,
    reloadHistory,
    deleteInspection,
    renameInspection,
  };
}
