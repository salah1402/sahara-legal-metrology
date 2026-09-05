import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { getApiConfig, setApiConfig } from '../../services/api';
import { Server, ToggleLeft, ToggleRight, Sparkles, Check } from 'lucide-react';
import { showToast } from '../../hooks/useToast';

export interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const currentConfig = getApiConfig();
  const [baseUrl, setBaseUrl] = useState(currentConfig.baseUrl);
  const [useDemoFixtures, setUseDemoFixtures] = useState(currentConfig.useDemoFixtures);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setApiConfig({
      baseUrl,
      useDemoFixtures,
    });
    showToast('success', 'Settings Saved', 'API connection and demonstration mode updated.');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="md"
      title="Inspection System Settings"
      subtitle="Configure Legal Metrology engine endpoints and mock adapter modes"
    >
      <form onSubmit={handleSave} className="space-y-4">
        {/* Backend API Base URL */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-primary-800" />
            <span>RapidOCR & Rule Engine Backend URL</span>
          </label>
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://sahara-legal-metrology-ze1m.onrender.com"
            className="w-full px-3 py-2 text-xs font-mono bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-800"
          />
          <p className="text-[11px] text-slate-400 mt-1">
            Target endpoints: <code className="font-mono text-[10px]">/ocr</code>, <code className="font-mono text-[10px]">/instructions/parse</code>, <code className="font-mono text-[10px]">/inspections</code>
          </p>
        </div>

        {/* Demo Fixtures Mode Toggle */}
        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-600" />
              <div>
                <span className="text-xs font-semibold text-slate-800 block">
                  SIH Demonstration / Offline Mode
                </span>
                <span className="text-[11px] text-slate-500">
                  Loads real packaged commodity sample labels & OCR coordinates offline
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setUseDemoFixtures(!useDemoFixtures)}
              className="text-primary-800 focus:outline-none"
            >
              {useDemoFixtures ? (
                <ToggleRight className="w-8 h-8 text-primary-800" />
              ) : (
                <ToggleLeft className="w-8 h-8 text-slate-400" />
              )}
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            leftIcon={<Check className="w-3.5 h-3.5" />}
          >
            Save Settings
          </Button>
        </div>
      </form>
    </Modal>
  );
};
