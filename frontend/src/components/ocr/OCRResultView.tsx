import React, { useState, useEffect } from 'react';
import type { InspectionRecord } from '../../types/inspection';
import type { Evidence } from '../../types/normalized';
import { BoundingBoxCanvas } from './BoundingBoxCanvas';
import { OCRRegionList } from './OCRRegionList';
import { StructuredDataView } from '../inspection/StructuredDataView';
import { ComplianceReportView } from '../compliance/ComplianceReportView';
import { StatusChip } from '../common/StatusChip';
import { Button } from '../common/Button';
import {
  ArrowLeft,
  Download,
  FileText,
  Layers,
  Database,
  Scale,
  ChevronDown,
  ChevronUp,
  Cpu,
  FileCheck2,
  Plus
} from 'lucide-react';
import { formatDate, getInspectionDisplayTitle } from '../../utils/formatters';
import { showToast } from '../../hooks/useToast';
import { evaluateCompliance } from '../../services/complianceService';
import { exportInspectionPDF, triggerBlobDownload, getInspectionSummary } from '../../services/reportService';
import { clsx } from 'clsx';

export interface OCRResultViewProps {
  record: InspectionRecord;
  selectedImageIndex: number;
  onSelectImageIndex: (index: number) => void;
  selectedOcrId: string | null;
  hoveredOcrId: string | null;
  onSelectOcrId: (id: string | null) => void;
  onHoverOcrId: (id: string | null) => void;
  showOcrBoxes: boolean;
  onToggleShowOcrBoxes: () => void;
  onBackToNew: () => void;
}

export const OCRResultView: React.FC<OCRResultViewProps> = ({
  record,
  selectedImageIndex,
  onSelectImageIndex,
  selectedOcrId,
  hoveredOcrId,
  onSelectOcrId,
  onHoverOcrId,
  showOcrBoxes,
  onToggleShowOcrBoxes,
  onBackToNew,
}) => {
  const [activeTab, setActiveTab] = useState<'compliance' | 'technical'>('compliance');
  const [technicalSubTab, setTechnicalSubTab] = useState<'structured' | 'tokens' | 'json'>('structured');
  const [jsonViewType, setJsonViewType] = useState<'all' | 'compliance' | 'normalized' | 'raw_ocr'>('all');
  const [isEvaluatingCompliance, setIsEvaluatingCompliance] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [showAuditDetails, setShowAuditDetails] = useState(false);
  const [executiveSummary, setExecutiveSummary] = useState<string>('');

  const activeImage = record.images[selectedImageIndex] || record.images[0];
  const regions = record.ocrResult?.images?.[selectedImageIndex]?.ocr ||
                  record.ocrResult?.images?.[0]?.ocr ||
                  (record.ocrResult as any)?.ocr ||
                  (record.ocrResult as any)?.regions ||
                  [];

  // Fetch or generate sanitized executive summary
  useEffect(() => {
    let isMounted = true;
    async function loadSummary() {
      try {
        const res = await getInspectionSummary(record.id);
        if (isMounted && res?.summary) {
          setExecutiveSummary(res.summary);
        }
      } catch {
        // Deterministic fallback if endpoint unavailable
        if (isMounted && record.compliance) {
          const comp = record.compliance;
          const status = comp.overall_status;
          const comm = getInspectionDisplayTitle(record.metadata);
          if (status === 'COMPLIANT') {
            setExecutiveSummary(
              `The package label inspection for ${comm} concluded as COMPLIANT under the Legal Metrology (Packaged Commodities) Rules, 2011. All ${comp.summary.total_checks} statutory declarations evaluated satisfied mandatory requirements.`
            );
          } else if (status === 'NON_COMPLIANT') {
            setExecutiveSummary(
              `The package label inspection for ${comm} resulted in a NON-COMPLIANT determination under PCR 2011 due to ${comp.summary.failed} statutory violation(s).`
            );
          } else {
            setExecutiveSummary(
              `The package label inspection for ${comm} resulted in NEEDS REVIEW because several mandatory declarations could not be fully verified from the supplied package images.`
            );
          }
        }
      }
    }
    loadSummary();
    return () => {
      isMounted = false;
    };
  }, [record.id, record.compliance, record.metadata]);

  const handleSelectEvidence = (evidence: Evidence) => {
    if (evidence.image_id) {
      const imgIdx = record.images.findIndex((img) => img.id === evidence.image_id);
      if (imgIdx !== -1 && imgIdx !== selectedImageIndex) {
        onSelectImageIndex(imgIdx);
      }
    }

    if (evidence.source_text) {
      const match = regions.find(
        (r: any) =>
          r.text.toLowerCase().includes(evidence.source_text.toLowerCase()) ||
          evidence.source_text.toLowerCase().includes(r.text.toLowerCase())
      );
      if (match) {
        onSelectOcrId(match.id);
        return;
      }
    }
    if (regions.length > 0) {
      onSelectOcrId(regions[0].id);
    }
  };

  const handleRunCompliance = async () => {
    if (!record.normalized) {
      showToast('warning', 'Missing Structured Data', 'Please normalize OCR data before running compliance.');
      return;
    }

    setIsEvaluatingCompliance(true);
    try {
      const result = await evaluateCompliance(record.id);
      record.compliance = result;
      showToast('success', 'Compliance Evaluated', `PCR 2011 evaluation completed: ${result.overall_status}`);
    } catch (e: any) {
      showToast('error', 'Evaluation Failed', e.message || 'Error running compliance evaluation.');
    } finally {
      setIsEvaluatingCompliance(false);
    }
  };

  const handleExportPdf = async () => {
    setIsExportingPdf(true);
    try {
      const blob = await exportInspectionPDF(record.id);
      const filename = `SAHARA_Inspection_${record.id}.pdf`;
      triggerBlobDownload(blob, filename);
      showToast('success', 'PDF Export Ready', `Downloaded official report: ${filename}`);
    } catch (e: any) {
      showToast('error', 'Export Failed', e.message || 'Unable to generate PDF report.');
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handleDownloadRecord = () => {
    const jsonStr = JSON.stringify(record, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SAHARA_Record_${record.id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('info', 'JSON Exported', `Downloaded record bundle for ${record.id}`);
  };

  const getActiveJsonPayload = () => {
    switch (jsonViewType) {
      case 'compliance':
        return record.compliance || { status: 'pending' };
      case 'normalized':
        return record.normalized || { status: 'pending' };
      case 'raw_ocr':
        return record.ocrResult || { status: 'pending' };
      case 'all':
      default:
        return record;
    }
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(getActiveJsonPayload(), null, 2));
    showToast('success', 'Copied', 'JSON payload copied to clipboard.');
  };

  const displayTitle = getInspectionDisplayTitle(record.metadata);

  return (
    <div className="space-y-3 sm:space-y-4 w-full">
      {/* 1. INSPECTION PAGE HEADER */}
      <div className="bg-white rounded-2xl border border-slate-200 p-3 sm:p-5 shadow-subtle flex flex-col md:flex-row items-start md:items-center justify-between gap-3 sm:gap-4 w-full">
        <div className="space-y-1 min-w-0 w-full md:flex-1">
          {/* Back Navigation & Breadcrumb */}
          <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap mb-0.5">
            <button
              type="button"
              onClick={onBackToNew}
              className="inline-flex items-center gap-1 text-xs font-semibold text-primary-800 hover:text-primary-900 transition-colors py-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Inspections</span>
            </button>
            <span className="text-slate-300 text-xs">/</span>
            <span className="text-[11px] font-mono text-slate-500 font-semibold truncate max-w-[140px] sm:max-w-none">
              {record.id}
            </span>
            <span className="text-slate-300 text-xs hidden sm:inline">•</span>
            <span className="text-[11px] text-slate-400 hidden sm:inline">
              {formatDate(record.metadata.created_at)}
            </span>
          </div>

          {/* Product Name Title + Status Badge */}
          <div className="flex items-center gap-2 flex-wrap">
            <h2
              className="text-base sm:text-lg md:text-xl font-bold text-slate-900 leading-snug break-words"
              title={displayTitle}
            >
              {displayTitle}
            </h2>
            <StatusChip status={record.metadata.status} />
          </div>

          {record.instructionPrompt && (
            <p className="text-xs text-slate-500 italic max-w-2xl truncate pt-0.5">
              Instruction: "{record.instructionPrompt}"
            </p>
          )}
        </div>

        {/* Action Buttons: Responsive Grid on Mobile, Flex on Desktop */}
        <div className="grid grid-cols-2 sm:flex sm:items-center gap-2 w-full md:w-auto flex-shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
          <Button
            variant="primary"
            size="sm"
            onClick={handleExportPdf}
            disabled={isExportingPdf}
            leftIcon={<FileText className="w-4 h-4" />}
            className="w-full justify-center min-h-[38px]"
          >
            {isExportingPdf ? 'Exporting...' : 'Export PDF'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadRecord}
            leftIcon={<Download className="w-4 h-4" />}
            className="w-full justify-center min-h-[38px]"
          >
            Export JSON
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={onBackToNew}
            leftIcon={<Plus className="w-3.5 h-3.5 sm:hidden" />}
            className="col-span-2 sm:col-span-1 w-full justify-center min-h-[38px] text-slate-600"
          >
            New Inspection
          </Button>
        </div>
      </div>

      {/* 2. COLLAPSIBLE AUDIT & ENGINE DETAILS (Progressive disclosure) */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-2xs w-full">
        <button
          type="button"
          onClick={() => setShowAuditDetails(!showAuditDetails)}
          className="w-full px-3.5 py-2.5 bg-slate-50/70 hover:bg-slate-100/70 flex items-center justify-between text-xs text-slate-600 font-medium transition-colors"
        >
          <div className="flex items-center gap-2 min-w-0">
            <Cpu className="w-3.5 h-3.5 text-primary-800 flex-shrink-0" />
            <span className="font-semibold text-slate-800 truncate">Audit & Engine Details</span>
            <span className="text-slate-400 hidden sm:inline">|</span>
            <span className="text-slate-500 hidden md:inline truncate">
              RapidOCR ONNX → Nemotron 3 Ultra 550B → Deterministic PCR 2011
            </span>
          </div>
          <div className="flex items-center gap-1 text-slate-400 flex-shrink-0 ml-2">
            <span className="text-[11px]">{showAuditDetails ? 'Hide' : 'Details'}</span>
            {showAuditDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </div>
        </button>

        {showAuditDetails && (
          <div className="p-3 border-t border-slate-200 bg-white grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">OCR Layer</span>
              <div className="font-semibold text-slate-900">RapidOCR ONNX Engine</div>
              <div className="text-[11px] text-slate-500 font-mono mt-0.5">{regions.length} text regions extracted</div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Normalization Layer</span>
              <div className="font-semibold text-slate-900">NVIDIA Nemotron 3 Ultra</div>
              <div className="text-[11px] text-slate-500 font-mono mt-0.5">Semantic JSON schema mapped</div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Legal Engine</span>
              <div className="font-semibold text-slate-900">PCR 2011 Registry</div>
              <div className="text-[11px] text-slate-500 font-mono mt-0.5">PCR-2011-CURRENT (GSR 202(E))</div>
            </div>
          </div>
        )}
      </div>

      {/* Multi-image thumbnail selector if multiple package views exist */}
      {record.images.length > 1 && (
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 w-full">
          <span className="text-xs text-slate-500 font-medium whitespace-nowrap flex-shrink-0">
            Views:
          </span>
          {record.images.map((img, idx) => (
            <button
              key={img.id}
              onClick={() => onSelectImageIndex(idx)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium transition-all whitespace-nowrap flex-shrink-0 ${
                selectedImageIndex === idx
                  ? 'bg-primary-800 text-white border-primary-800 shadow-2xs font-semibold'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Label #{idx + 1}</span>
            </button>
          ))}
        </div>
      )}

      {/* 3. WORKSPACE LAYOUT (2-COLUMN ON DESKTOP, TRUE SINGLE-COLUMN FLOW ON MOBILE) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 sm:gap-5 items-start w-full">
        {/* Evidence / Product Image Viewer (Left on Desktop, Natural Middle on Mobile) */}
        <div className="lg:col-span-6 xl:col-span-6 lg:sticky lg:top-20 order-2 lg:order-1 w-full min-w-0">
          {activeImage ? (
            <BoundingBoxCanvas
              imageUrl={activeImage.previewUrl}
              imageName={activeImage.name}
              regions={regions}
              selectedRegionId={selectedOcrId}
              hoveredRegionId={hoveredOcrId}
              onSelectRegion={onSelectOcrId}
              onHoverRegion={onHoverOcrId}
              showBoxes={showOcrBoxes}
              onToggleShowBoxes={onToggleShowOcrBoxes}
            />
          ) : (
            <div className="h-48 sm:h-64 flex items-center justify-center bg-white rounded-2xl border border-slate-200 text-xs text-slate-400">
              No active label image selected
            </div>
          )}
        </div>

        {/* Compliance Workbench & Technical Inspector (Right on Desktop, Top/Bottom Flow on Mobile) */}
        <div className="lg:col-span-6 xl:col-span-6 flex flex-col space-y-3.5 sm:space-y-4 order-1 lg:order-2 w-full min-w-0">
          {/* Primary View Switcher: Compliance Report vs Technical Data */}
          <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200 w-full">
            <button
              type="button"
              onClick={() => setActiveTab('compliance')}
              className={clsx(
                'flex-1 flex items-center justify-center gap-1.5 py-2 px-2.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap min-h-[38px]',
                activeTab === 'compliance'
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              )}
            >
              <Scale className="w-3.5 h-3.5 text-primary-800 flex-shrink-0" />
              <span>Compliance Report</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('technical')}
              className={clsx(
                'flex-1 flex items-center justify-center gap-1.5 py-2 px-2.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap min-h-[38px]',
                activeTab === 'technical'
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              )}
            >
              <Database className="w-3.5 h-3.5 text-primary-800 flex-shrink-0" />
              <span>Technical Data</span>
            </button>
          </div>

          {/* TAB 1: COMPLIANCE REPORT FLOW */}
          {activeTab === 'compliance' && (
            <div className="space-y-3 sm:space-y-4 w-full">
              {/* Executive Summary Card */}
              {executiveSummary && (
                <div className="bg-white p-3.5 sm:p-4 rounded-xl border border-slate-200 shadow-2xs space-y-1 text-xs w-full">
                  <div className="flex items-center gap-1.5 font-bold text-slate-900">
                    <FileCheck2 className="w-4 h-4 text-primary-800 flex-shrink-0" />
                    <span>Executive Inspection Summary</span>
                  </div>
                  <p className="text-slate-700 leading-relaxed break-words">
                    {executiveSummary}
                  </p>
                </div>
              )}

              {/* Compliance Report Detailed Workbench */}
              <ComplianceReportView
                compliance={record.compliance}
                onSelectEvidence={handleSelectEvidence}
                onRunCompliance={handleRunCompliance}
                isEvaluating={isEvaluatingCompliance}
              />
            </div>
          )}

          {/* TAB 2: TECHNICAL DATA FLOW */}
          {activeTab === 'technical' && (
            <div className="space-y-3 bg-white p-3 sm:p-4 rounded-2xl border border-slate-200 shadow-subtle w-full min-w-0">
              {/* Technical Sub-tabs */}
              <div className="flex items-center gap-1 pb-2 border-b border-slate-100 text-xs overflow-x-auto w-full">
                <button
                  type="button"
                  onClick={() => setTechnicalSubTab('structured')}
                  className={clsx(
                    'px-2.5 py-1.5 rounded-md font-medium transition-colors whitespace-nowrap min-h-[34px]',
                    technicalSubTab === 'structured'
                      ? 'bg-slate-900 text-white font-semibold'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  )}
                >
                  Structured Data
                </button>

                <button
                  type="button"
                  onClick={() => setTechnicalSubTab('tokens')}
                  className={clsx(
                    'px-2.5 py-1.5 rounded-md font-medium transition-colors whitespace-nowrap min-h-[34px]',
                    technicalSubTab === 'tokens'
                      ? 'bg-slate-900 text-white font-semibold'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  )}
                >
                  OCR Tokens ({regions.length})
                </button>

                <button
                  type="button"
                  onClick={() => setTechnicalSubTab('json')}
                  className={clsx(
                    'px-2.5 py-1.5 rounded-md font-medium transition-colors whitespace-nowrap min-h-[34px]',
                    technicalSubTab === 'json'
                      ? 'bg-slate-900 text-white font-semibold'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  )}
                >
                  Raw JSON
                </button>
              </div>

              {/* Technical Sub-tab Content */}
              {technicalSubTab === 'structured' && (
                <StructuredDataView
                  data={record.normalized}
                  onSelectEvidence={handleSelectEvidence}
                />
              )}

              {technicalSubTab === 'tokens' && (
                <OCRRegionList
                  regions={regions}
                  selectedRegionId={selectedOcrId}
                  hoveredRegionId={hoveredOcrId}
                  onSelectRegion={onSelectOcrId}
                  onHoverRegion={onHoverOcrId}
                />
              )}

              {technicalSubTab === 'json' && (
                <div className="bg-slate-950 text-slate-200 rounded-xl p-3 font-mono text-xs overflow-auto max-h-[480px] border border-slate-800 space-y-2.5 w-full">
                  <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-800 flex-wrap">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-slate-400">View:</span>
                      <select
                        value={jsonViewType}
                        onChange={(e) => setJsonViewType(e.target.value as any)}
                        className="bg-slate-900 text-slate-200 border border-slate-700 rounded px-2 py-1 text-xs focus:outline-none"
                      >
                        <option value="all">Full Record Bundle</option>
                        <option value="compliance">Compliance Report (Phase 3)</option>
                        <option value="normalized">Structured Product JSON (Phase 2)</option>
                        <option value="raw_ocr">Raw RapidOCR JSON</option>
                      </select>
                    </div>

                    <button
                      type="button"
                      onClick={handleCopyJson}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-[11px] font-sans font-medium transition-colors min-h-[30px]"
                    >
                      Copy JSON
                    </button>
                  </div>

                  <pre className="text-[11px] leading-relaxed text-emerald-400/90 whitespace-pre-wrap break-all">
                    {JSON.stringify(getActiveJsonPayload(), null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
