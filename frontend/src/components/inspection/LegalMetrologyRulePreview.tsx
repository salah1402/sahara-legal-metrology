import React from 'react';
import type { LegalMetrologyRuleCheck } from '../../types/inspection';
import { Scale, Clock, ExternalLink, AlertCircle } from 'lucide-react';
import { clsx } from 'clsx';

export interface LegalMetrologyRulePreviewProps {
  ruleChecks?: LegalMetrologyRuleCheck[];
  onSelectEvidenceId?: (id: string) => void;
}

const PCR_STANDARD_RULES: LegalMetrologyRuleCheck[] = [
  {
    rule_id: 'R6_1_A',
    rule_name: 'Manufacturer / Packer Name & Address',
    regulation_ref: 'Rule 6(1)(a) PCR 2011',
    description: 'Name and complete postal address of the manufacturer, packer, or importer.',
    status: 'pending',
  },
  {
    rule_id: 'R6_1_AA',
    rule_name: 'Country of Origin Declaration',
    regulation_ref: 'Rule 6(1)(aa) PCR 2011',
    description: 'Country of origin or manufacture/assembly on principal display panel.',
    status: 'pending',
  },
  {
    rule_id: 'R6_1_B',
    rule_name: 'Net Quantity with Metric Units',
    regulation_ref: 'Rule 6(1)(b) & Rule 12',
    description: 'Net quantity in standard SI units (g, kg, ml, l) with prescribed minimum numeral height.',
    status: 'pending',
  },
  {
    rule_id: 'R6_1_D',
    rule_name: 'Month & Year of Manufacture / Packing',
    regulation_ref: 'Rule 6(1)(d) PCR 2011',
    description: 'Month and year in which commodity is manufactured, packed, or imported.',
    status: 'pending',
  },
  {
    rule_id: 'R6_1_E',
    rule_name: 'Maximum Retail Price (MRP)',
    regulation_ref: 'Rule 6(1)(e) PCR 2011',
    description: 'MRP stated as "Max. Retail Price Rs. ... Inclusive of all taxes".',
    status: 'pending',
  },
  {
    rule_id: 'R6_1_F',
    rule_name: 'Consumer Care Helpline Details',
    regulation_ref: 'Rule 6(1)(f) PCR 2011',
    description: 'Name, address, phone number, and email of consumer grievance officer.',
    status: 'pending',
  },
  {
    rule_id: 'R6_1_M',
    rule_name: 'Unit Sale Price Declaration',
    regulation_ref: 'Rule 6(1)(m) PCR 2011',
    description: 'Unit sale price in rupees per g/kg/ml/l as required for packaged goods.',
    status: 'pending',
  },
];

export const LegalMetrologyRulePreview: React.FC<LegalMetrologyRulePreviewProps> = ({
  ruleChecks,
  onSelectEvidenceId,
}) => {
  const displayRules = ruleChecks || PCR_STANDARD_RULES;

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-subtle">
      {/* Header */}
      <div className="p-3.5 border-b border-slate-100 bg-slate-50/70 space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-primary-800" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              PCR 2011 Compliance Checklist
            </h4>
          </div>
          <span className="text-[10px] font-medium text-slate-600 bg-slate-200/80 px-2 py-0.5 rounded-full">
            Future Rule Engine
          </span>
        </div>
        <p className="text-[11px] text-slate-500">
          Raw OCR evidence will be evaluated against Legal Metrology Rules (PCR 2011) in Phase 2.
        </p>
      </div>

      {/* Information Banner */}
      <div className="p-3 bg-amber-50/70 border-b border-amber-100 flex items-start gap-2 text-xs text-amber-900">
        <AlertCircle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
        <p className="text-[11px] leading-snug">
          <strong>Notice:</strong> Raw OCR text extraction complete. Legal Metrology rule engine evaluations have not been run yet.
        </p>
      </div>

      {/* Rules list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 max-h-[480px]">
        {displayRules.map((rule) => {
          return (
            <div
              key={rule.rule_id}
              className={clsx(
                'p-3 rounded-xl border transition-all text-xs space-y-1.5 border-slate-200 bg-white hover:bg-slate-50/60'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                  <span className="font-semibold text-slate-800">{rule.rule_name}</span>
                </div>

                <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-slate-50 border border-slate-200 text-slate-600 whitespace-nowrap">
                  {rule.regulation_ref}
                </span>
              </div>

              <p className="text-[11px] text-slate-500 leading-relaxed pl-5">
                {rule.description}
              </p>

              {rule.detected_text && (
                <div className="pl-5 pt-1">
                  <div className="p-2 rounded bg-slate-50 border border-slate-200/90 text-[11px] font-mono text-slate-700 flex items-center justify-between gap-2">
                    <span className="truncate">
                      <strong className="font-semibold text-slate-500 font-sans">Evidence:</strong> {rule.detected_text}
                    </span>
                    {rule.evidence_region_id && onSelectEvidenceId && (
                      <button
                        type="button"
                        onClick={() => onSelectEvidenceId(rule.evidence_region_id!)}
                        className="text-[10px] text-primary-800 hover:underline flex items-center gap-0.5 flex-shrink-0 font-sans"
                      >
                        <span>View OCR</span>
                        <ExternalLink className="w-2.5 h-2.5" />
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
