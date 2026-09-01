import React, { useState } from 'react';
import type {
  ComplianceResult,
  RuleCheckResult,
  OverallStatus,
} from '../../types/compliance';
import type { Evidence } from '../../types/normalized';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  MinusCircle,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Scale,
  BookOpen,
  Info,
  Check,
  Search,
  RefreshCw,
  X
} from 'lucide-react';
import { clsx } from 'clsx';
import { Button } from '../common/Button';

export interface ComplianceReportViewProps {
  compliance?: ComplianceResult;
  onSelectEvidence?: (evidence: Evidence) => void;
  onRunCompliance?: () => void;
  isEvaluating?: boolean;
}

export const ComplianceReportView: React.FC<ComplianceReportViewProps> = ({
  compliance,
  onSelectEvidence,
  onRunCompliance,
  isEvaluating = false,
}) => {
  const [expandedRuleIds, setExpandedRuleIds] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSourceRule, setSelectedSourceRule] = useState<RuleCheckResult | null>(null);

  if (!compliance) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 text-center space-y-3 shadow-subtle w-full">
        <div className="w-12 h-12 rounded-2xl bg-primary-50 border border-primary-100 flex items-center justify-center text-primary-800 mx-auto">
          <Scale className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-bold text-slate-800">
          Legal Metrology Compliance Pending
        </h4>
        <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
          Evaluate statutory compliance under the Legal Metrology (Packaged Commodities) Rules, 2011.
        </p>
        {onRunCompliance && (
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={onRunCompliance}
            disabled={isEvaluating}
            className="w-full sm:w-auto min-h-[40px]"
            leftIcon={<RefreshCw className={clsx('w-4 h-4', isEvaluating && 'animate-spin')} />}
          >
            {isEvaluating ? 'Evaluating PCR 2011 Rules...' : 'Run Compliance Evaluation'}
          </Button>
        )}
      </div>
    );
  }

  const { overall_status, summary, checks } = compliance;
  const overallStatus = overall_status as OverallStatus;

  const toggleRuleExpand = (ruleId: string) => {
    setExpandedRuleIds((prev) => {
      const next = new Set(prev);
      if (next.has(ruleId)) {
        next.delete(ruleId);
      } else {
        next.add(ruleId);
      }
      return next;
    });
  };

  const expandAll = () => {
    setExpandedRuleIds(new Set(checks.map((c) => c.rule_id)));
  };

  const collapseAll = () => {
    setExpandedRuleIds(new Set());
  };

  const filteredChecks = checks.filter((c) => {
    if (statusFilter !== 'ALL' && c.status !== statusFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchNumber = c.rule_number.toLowerCase().includes(q);
      const matchTitle = c.title.toLowerCase().includes(q);
      const matchReason = c.reason.toLowerCase().includes(q);
      return matchNumber || matchTitle || matchReason;
    }
    return true;
  });

  return (
    <div className="space-y-3 sm:space-y-4 w-full">
      {/* 1. DOMINANT OVERALL RESULT BANNER */}
      <div
        className={clsx(
          'p-3.5 sm:p-4 rounded-2xl border shadow-subtle transition-all space-y-2 w-full',
          overallStatus === 'COMPLIANT' && 'bg-emerald-50/80 border-emerald-300 text-emerald-950',
          overallStatus === 'NON_COMPLIANT' && 'bg-rose-50/80 border-rose-300 text-rose-950',
          overallStatus === 'NEEDS_REVIEW' && 'bg-amber-50/80 border-amber-300 text-amber-950'
        )}
      >
        <div className="flex items-start sm:items-center justify-between gap-2.5">
          <div className="flex items-center gap-2.5 min-w-0">
            <div
              className={clsx(
                'w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center text-white shadow-sm flex-shrink-0',
                overallStatus === 'COMPLIANT'
                  ? 'bg-emerald-600'
                  : overallStatus === 'NON_COMPLIANT'
                  ? 'bg-rose-600'
                  : 'bg-amber-600'
              )}
            >
              {overallStatus === 'COMPLIANT' && <CheckCircle2 className="w-5 h-5 sm:w-6 sm:h-6" />}
              {overallStatus === 'NON_COMPLIANT' && <XCircle className="w-5 h-5 sm:w-6 sm:h-6" />}
              {overallStatus === 'NEEDS_REVIEW' && <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6" />}
            </div>

            <div className="min-w-0">
              <span className="text-[10px] font-mono uppercase tracking-wider font-semibold opacity-70 block">
                Legal Metrology Determination
              </span>
              <h3 className="text-sm sm:text-base font-bold tracking-tight break-words">
                {overallStatus === 'COMPLIANT'
                  ? 'PASS — COMPLIANT WITH PCR 2011'
                  : overallStatus === 'NON_COMPLIANT'
                  ? 'FAIL — STATUTORY VIOLATION'
                  : 'NEEDS REVIEW — INSUFFICIENT EVIDENCE'}
              </h3>
            </div>
          </div>

          <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 shadow-2xs flex-shrink-0">
            PCR 2011
          </span>
        </div>

        <p className="text-xs opacity-90 leading-relaxed pt-1 border-t border-black/5 break-words">
          {overallStatus === 'COMPLIANT'
            ? 'All mandatory packaged-commodity declarations are verified against statutory rules.'
            : overallStatus === 'NON_COMPLIANT'
            ? 'One or more mandatory Legal Metrology statutory requirements failed verification.'
            : 'Additional package panel views or physical inspection are required to establish full compliance.'}
        </p>
      </div>

      {/* 2. COMPACT RESULT SUMMARY INLINE BAR */}
      <div className="bg-white px-3 py-2.5 sm:px-3.5 sm:py-2.5 rounded-xl border border-slate-200 shadow-2xs flex items-center justify-between flex-wrap gap-2 text-xs w-full">
        <div className="flex items-center gap-1.5 font-bold text-slate-800 flex-shrink-0">
          <Scale className="w-4 h-4 text-primary-800" />
          <span>{summary.total_checks} Statutory Checks</span>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap text-[11px] sm:text-xs font-medium">
          <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" />
            <span>{summary.passed} Passed</span>
          </span>

          {summary.failed > 0 && (
            <span className="inline-flex items-center gap-1 text-rose-700 font-semibold bg-rose-50 px-2 py-0.5 rounded-md border border-rose-200">
              <XCircle className="w-3 h-3" />
              <span>{summary.failed} Failed</span>
            </span>
          )}

          {summary.needs_review > 0 && (
            <span className="inline-flex items-center gap-1 text-amber-800 font-semibold bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">
              <AlertTriangle className="w-3 h-3" />
              <span>{summary.needs_review} Review</span>
            </span>
          )}

          {(summary.exempt || 0) > 0 && (
            <span className="inline-flex items-center gap-1 text-purple-700 font-semibold bg-purple-50 px-2 py-0.5 rounded-md border border-purple-200">
              <Sparkles className="w-3 h-3" />
              <span>{summary.exempt} Exempt</span>
            </span>
          )}

          <span className="inline-flex items-center gap-1 text-slate-500 bg-slate-50 px-2 py-0.5 rounded-md border border-slate-200">
            <MinusCircle className="w-3 h-3" />
            <span>{summary.not_applicable} N/A</span>
          </span>
        </div>
      </div>

      {/* 3. DETAILED COMPLIANCE SECTION WITH PROGRESSIVE DISCLOSURE */}
      <div className="space-y-2.5 pt-1 w-full">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 w-full">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              Detailed Compliance Rules ({filteredChecks.length})
            </h4>
            <div className="flex items-center gap-1 text-[11px] text-slate-500">
              <span>•</span>
              <button
                type="button"
                onClick={expandAll}
                className="text-primary-800 hover:underline font-medium p-0.5"
              >
                Expand all
              </button>
              <span>/</span>
              <button
                type="button"
                onClick={collapseAll}
                className="text-slate-500 hover:underline p-0.5"
              >
                Collapse
              </button>
            </div>
          </div>

          {/* Compact Search Input */}
          <div className="relative w-full sm:w-56">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search rules..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary-800 text-slate-800 placeholder-slate-400"
            />
          </div>
        </div>

        {/* Status Filter Tabs (Scrollable on small mobile) */}
        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl border border-slate-200/80 overflow-x-auto text-xs w-full">
          {(['ALL', 'PASS', 'FAIL', 'NEEDS_REVIEW', 'EXEMPT', 'NOT_APPLICABLE'] as const).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={clsx(
                'px-2 py-1 rounded-lg font-medium whitespace-nowrap transition-colors text-[11px] min-h-[30px] flex items-center justify-center flex-shrink-0',
                statusFilter === st
                  ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              )}
            >
              {st === 'ALL'
                ? `All (${summary.total_checks})`
                : st === 'PASS'
                ? `Pass (${summary.passed})`
                : st === 'FAIL'
                ? `Fail (${summary.failed})`
                : st === 'NEEDS_REVIEW'
                ? `Review (${summary.needs_review})`
                : st === 'EXEMPT'
                ? `Exempt (${summary.exempt || 0})`
                : `N/A (${summary.not_applicable})`}
            </button>
          ))}
        </div>

        {/* Progressive Disclosure Rule Cards */}
        <div className="space-y-2 w-full">
          {filteredChecks.length === 0 ? (
            <div className="p-6 text-center bg-white rounded-2xl border border-slate-200 text-xs text-slate-400">
              No legal rule checks match the selected filter.
            </div>
          ) : (
            filteredChecks.map((check) => {
              const isExpanded = expandedRuleIds.has(check.rule_id);

              return (
                <div
                  key={check.rule_id}
                  className={clsx(
                    'rounded-xl border bg-white shadow-2xs transition-all overflow-hidden w-full',
                    check.status === 'PASS' && 'border-slate-200 hover:border-slate-300',
                    check.status === 'FAIL' && 'border-rose-200 bg-rose-50/20 hover:border-rose-300',
                    check.status === 'NEEDS_REVIEW' && 'border-amber-200 hover:border-amber-300',
                    check.status === 'EXEMPT' && 'border-purple-200 hover:border-purple-300',
                    check.status === 'NOT_APPLICABLE' && 'border-slate-200 opacity-85'
                  )}
                >
                  {/* Compact Clickable Header Row */}
                  <button
                    type="button"
                    onClick={() => toggleRuleExpand(check.rule_id)}
                    className="w-full p-2.5 sm:p-3 flex items-center justify-between gap-2 sm:gap-3 text-left hover:bg-slate-50/70 transition-colors min-h-[44px]"
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="text-[11px] sm:text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200 flex-shrink-0">
                        Rule {check.rule_number}
                      </span>
                      <span className="text-xs font-bold text-slate-900 leading-snug break-words line-clamp-2">
                        {check.title}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
                      {/* Compact Status Pill */}
                      <span
                        className={clsx(
                          'px-1.5 py-0.5 sm:px-2 rounded-full text-[9px] sm:text-[10px] font-bold tracking-wide uppercase flex items-center gap-1',
                          check.status === 'PASS' && 'bg-emerald-100 text-emerald-800 border border-emerald-200',
                          check.status === 'FAIL' && 'bg-rose-100 text-rose-800 border border-rose-200',
                          check.status === 'NEEDS_REVIEW' && 'bg-amber-100 text-amber-800 border border-amber-200',
                          check.status === 'EXEMPT' && 'bg-purple-100 text-purple-800 border border-purple-200',
                          check.status === 'NOT_APPLICABLE' && 'bg-slate-100 text-slate-600 border border-slate-200'
                        )}
                      >
                        {check.status === 'PASS' && <CheckCircle2 className="w-3 h-3" />}
                        {check.status === 'FAIL' && <XCircle className="w-3 h-3" />}
                        {check.status === 'NEEDS_REVIEW' && <AlertTriangle className="w-3 h-3" />}
                        {check.status === 'EXEMPT' && <Sparkles className="w-3 h-3" />}
                        {check.status === 'NOT_APPLICABLE' && <MinusCircle className="w-3 h-3" />}
                        <span>{check.status.replace('_', ' ')}</span>
                      </span>

                      {/* Expand / Collapse Chevron */}
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      )}
                    </div>
                  </button>

                  {/* Expanded Details Body */}
                  {isExpanded && (
                    <div className="p-3 pt-0 border-t border-slate-100 space-y-2.5 text-xs bg-slate-50/40">
                      {/* Observed vs Required Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs bg-white p-2.5 rounded-lg border border-slate-200/80 font-mono mt-2">
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 font-sans block">
                            Observed on Package:
                          </span>
                          <span className="text-slate-900 font-medium break-words">
                            {check.observed_value || (
                              <span className="italic text-slate-400 font-sans">
                                {check.status === 'NOT_APPLICABLE' ? 'Not Applicable' : check.status === 'EXEMPT' ? 'Statutory Exemption Established' : 'Not observed in supplied view'}
                              </span>
                            )}
                          </span>
                        </div>

                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 font-sans block">
                            Legal Requirement:
                          </span>
                          <span className="text-slate-700 break-words">
                            {check.required_value || 'Mandatory statutory declaration under PCR 2011'}
                          </span>
                        </div>
                      </div>

                      {/* Statutory Reason / Analysis */}
                      <div className="flex items-start gap-2 text-xs text-slate-700 leading-relaxed bg-white p-2.5 rounded-lg border border-slate-200/80">
                        <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                        <p className="break-words">
                          <strong className="font-semibold text-slate-900">Analysis:</strong> {check.reason}
                        </p>
                      </div>

                      {/* Exemption Audit Box if Exemption Info is present */}
                      {check.exemption && (
                        <div className="p-2.5 bg-purple-50/90 border border-purple-200 rounded-lg space-y-1 text-xs text-purple-950">
                          <div className="flex items-center gap-1.5 font-bold">
                            <Sparkles className="w-3.5 h-3.5 text-purple-700" />
                            <span>Statutory Exemption Audit (Rule {check.exemption.exemption_clause})</span>
                          </div>
                          <p className="text-[11px] text-purple-900 leading-snug break-words">
                            {check.exemption.reason}
                          </p>
                          {check.exemption.factual_conditions_checked.length > 0 && (
                            <div className="pt-1">
                              <span className="text-[10px] uppercase font-bold text-purple-700 block mb-0.5">Verified Conditions:</span>
                              <ul className="space-y-0.5 pl-2">
                                {check.exemption.factual_conditions_checked.map((cond, cIdx) => (
                                  <li key={cIdx} className="text-[11px] text-purple-950 flex items-center gap-1.5">
                                    <Check className="w-3 h-3 text-purple-600 flex-shrink-0" />
                                    <span>{cond}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Evidence Pills & Official Citation Trigger */}
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pt-1 text-xs">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-[11px] font-semibold text-slate-500 flex items-center gap-1">
                            <Scale className="w-3 h-3" /> Evidence ({check.evidence.length}):
                          </span>
                          {check.evidence.length === 0 ? (
                            <span className="text-[11px] text-slate-400 italic">None attached</span>
                          ) : (
                            check.evidence.map((ev, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => onSelectEvidence && onSelectEvidence(ev)}
                                className="px-2 py-0.5 rounded bg-sky-50 hover:bg-sky-100 border border-sky-200 text-sky-800 text-[11px] font-mono flex items-center gap-1 transition-colors"
                                title={`Click to highlight: "${ev.source_text}"`}
                              >
                                <span className="truncate max-w-[140px] sm:max-w-[180px]">"{ev.source_text}"</span>
                                <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                              </button>
                            ))
                          )}
                        </div>

                        <button
                          type="button"
                          onClick={() => setSelectedSourceRule(check)}
                          className="text-[11px] text-primary-800 hover:text-primary-900 font-medium flex items-center gap-1 hover:underline self-end sm:self-auto py-1"
                        >
                          <BookOpen className="w-3 h-3" />
                          <span>Gazette Citation</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Official Legal Source Citation Modal */}
      {selectedSourceRule && (
        <div
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-3 sm:p-4"
          onClick={() => setSelectedSourceRule(null)}
          aria-modal="true"
          role="dialog"
        >
          <div
            className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-4 sm:p-5 space-y-3.5 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-primary-800" />
                <h3 className="text-sm font-bold text-slate-900">
                  Gazette Authority & Legal Citation
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedSourceRule(null)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs text-slate-700">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-mono uppercase font-bold text-slate-400 block">
                  Statutory Rule Reference
                </span>
                <p className="font-bold text-slate-900">
                  Rule {selectedSourceRule.rule_number} — {selectedSourceRule.title}
                </p>
                <p className="text-[11px] text-slate-500 font-mono">
                  Rule ID: {selectedSourceRule.rule_id}
                </p>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] font-mono uppercase font-bold text-slate-400 block">
                  Statutory Analysis & Reason
                </span>
                <p className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-slate-800 leading-relaxed font-sans">
                  {selectedSourceRule.reason}
                </p>
              </div>

              {selectedSourceRule.legal_source && (
                <div className="space-y-1">
                  <span className="text-[10px] font-mono uppercase font-bold text-slate-400 block">
                    Gazette Notification
                  </span>
                  <p className="p-2.5 bg-sky-50 text-sky-900 rounded-xl border border-sky-200 font-mono text-[11px]">
                    {selectedSourceRule.legal_source.instrument} {selectedSourceRule.legal_source.notification ? `(${selectedSourceRule.legal_source.notification})` : ''} — Effective: {selectedSourceRule.legal_source.effective_from}
                  </p>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setSelectedSourceRule(null)}
              >
                Close Citation
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
