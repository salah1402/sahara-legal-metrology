import React from 'react';
import { Sparkles, CornerDownLeft, Scale, Tag, Calendar, Building } from 'lucide-react';

export interface InstructionInputProps {
  value: string;
  onChange: (val: string) => void;
  onSubmit?: () => void;
  disabled?: boolean;
}

const SUGGESTIONS = [
  {
    icon: <Scale className="w-3 h-3 text-primary-700" />,
    label: 'Mandatory PCR 2011 declarations',
    text: 'Check this package for all mandatory declarations under Legal Metrology (Packaged Commodities) Rules 2011.',
  },
  {
    icon: <Tag className="w-3 h-3 text-emerald-700" />,
    label: 'Extract MRP & Net Quantity',
    text: 'Extract the MRP, net quantity, unit sale price and verify unit formatting.',
  },
  {
    icon: <Building className="w-3 h-3 text-amber-700" />,
    label: 'Manufacturer & Origin details',
    text: 'Extract manufacturer address, packer details, country of origin, and consumer care email.',
  },
  {
    icon: <Calendar className="w-3 h-3 text-indigo-700" />,
    label: 'Mfg date & Expiry',
    text: 'Verify manufacturing date, best before period, and batch numbering.',
  },
];

export const InstructionInput: React.FC<InstructionInputProps> = ({
  value,
  onChange,
  onSubmit,
  disabled = false,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (onSubmit) onSubmit();
    }
  };

  return (
    <div className="space-y-2 sm:space-y-2.5 w-full">
      <div className="relative bg-white rounded-2xl border border-slate-200 shadow-subtle hover:border-slate-300 focus-within:border-primary-800 focus-within:ring-2 focus-within:ring-primary-800/20 transition-all p-2.5 sm:p-3 w-full">
        <div className="flex items-center gap-1.5 sm:gap-2 mb-1 px-1">
          <div className="w-5 h-5 rounded-md bg-primary-50 text-primary-800 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-semibold text-slate-700 truncate">Inspection Instructions</span>
          <span className="text-[10px] text-slate-400 ml-auto font-mono hidden sm:inline">LLM Parser</span>
        </div>

        <textarea
          rows={3}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="What would you like to verify? (e.g. 'Check mandatory declarations under PCR 2011')"
          className="w-full resize-none bg-transparent border-0 p-1 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:ring-0 focus:outline-none leading-relaxed"
        />

        <div className="flex items-center justify-between pt-1.5 border-t border-slate-100 px-1 text-[11px] text-slate-400">
          <span className="truncate max-w-[180px] sm:max-w-xs">
            Target: <code className="font-mono text-[10px] bg-slate-100 px-1 py-0.5 rounded text-slate-600">POST /api/instructions/parse</code>
          </span>
          <span className="flex items-center gap-1 flex-shrink-0 ml-2">
            <span className="hidden sm:inline">Press Enter to queue</span>
            <CornerDownLeft className="w-3 h-3 text-slate-400" />
          </span>
        </div>
      </div>

      {/* Suggested Quick Templates */}
      <div className="flex items-center gap-1 sm:gap-1.5 flex-wrap w-full">
        <span className="text-[11px] text-slate-400 font-medium mr-0.5 flex-shrink-0">Suggested:</span>
        {SUGGESTIONS.map((sug, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onChange(sug.text)}
            className="inline-flex items-center gap-1 text-[11px] sm:text-xs px-2 sm:px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200/80 transition-colors min-h-[28px]"
          >
            {sug.icon}
            <span>{sug.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
