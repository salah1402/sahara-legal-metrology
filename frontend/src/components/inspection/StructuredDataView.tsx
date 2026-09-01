import React from 'react';
import type {
  StructuredProductData,
  Evidence,
  FieldStatus,
  ImageType,
} from '../../types/normalized';
import {
  Tag,
  Scale,
  Building2,
  Calendar,
  PhoneCall,
  Globe2,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  ExternalLink,
  Info,
  Layers,
  Sparkles,
  AlertTriangle
} from 'lucide-react';

export interface StructuredDataViewProps {
  data?: StructuredProductData;
  onSelectEvidence?: (evidence: Evidence) => void;
}

function StatusBadge({ status }: { status: FieldStatus }) {
  switch (status) {
    case 'extracted':
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
          Extracted
        </span>
      );
    case 'ambiguous':
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
          <HelpCircle className="w-3 h-3 text-amber-600" />
          Ambiguous
        </span>
      );
    case 'conflicting':
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
          <AlertCircle className="w-3 h-3 text-rose-600" />
          Conflicting
        </span>
      );
    case 'unreadable':
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
          Unreadable
        </span>
      );
    case 'not_observed':
    default:
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-200">
          Not observed in supplied images
        </span>
      );
  }
}

function formatImageType(type: ImageType): string {
  switch (type) {
    case 'nutrition_panel': return 'Nutrition Panel';
    case 'front_panel': return 'Front Display Panel';
    case 'back_panel': return 'Back Panel';
    case 'side_panel': return 'Side Panel';
    case 'ingredients_panel': return 'Ingredients Panel';
    case 'mrp_panel': return 'MRP & Pricing Panel';
    case 'manufacturer_panel': return 'Manufacturer Panel';
    case 'importer_panel': return 'Importer Panel';
    case 'barcode_panel': return 'Barcode & Statutory Panel';
    case 'mixed_panel': return 'Mixed Panel';
    case 'unknown':
    default:
      return 'General Package Surface';
  }
}

function EvidenceList({
  evidence,
  onSelectEvidence
}: {
  evidence: Evidence[];
  onSelectEvidence?: (evidence: Evidence) => void;
}) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="space-y-1 pt-1">
      {evidence.map((ev, idx) => (
        <div
          key={idx}
          className="flex items-center justify-between text-[11px] font-mono text-slate-600 bg-white p-1.5 px-2 rounded-lg border border-slate-200"
        >
          <div className="truncate min-w-0 flex-1 mr-2">
            <span className="text-[10px] font-sans font-bold text-slate-400 mr-1.5 uppercase flex-shrink-0">
              {ev.image_id}
            </span>
            <span>{ev.source_text}</span>
          </div>

          {onSelectEvidence && (
            <button
              type="button"
              onClick={() => onSelectEvidence(ev)}
              className="text-[10px] text-primary-800 hover:underline flex items-center gap-1 font-sans font-semibold flex-shrink-0 ml-2"
            >
              <span>{Math.round(ev.ocr_confidence * 100)}% conf</span>
              <ExternalLink className="w-2.5 h-2.5" />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

export const StructuredDataView: React.FC<StructuredDataViewProps> = ({
  data,
  onSelectEvidence,
}) => {
  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-white rounded-2xl border border-slate-200 text-center space-y-2">
        <Info className="w-8 h-8 text-slate-400" />
        <h4 className="text-sm font-semibold text-slate-700">No Structured Product Data</h4>
        <p className="text-xs text-slate-500 max-w-sm">
          Run the Nemotron semantic normalizer to transform raw OCR detections into structured product fields.
        </p>
      </div>
    );
  }

  const { images, product, other_detected_information, ambiguities, conflicts } = data;

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-subtle">
      {/* 1. Header & Image Coverage Classification */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/70 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary-800" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Nemotron Structured Product Data
            </h4>
          </div>
          <span className="text-[10px] font-mono text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
            Schema v{data.schema_version}
          </span>
        </div>

        {/* Image Coverage Badges */}
        {images && images.length > 0 && (
          <div className="p-2.5 bg-white rounded-xl border border-slate-200 space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[11px] font-semibold text-slate-700 flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-primary-800" />
                Image Coverage:
              </span>
              {images.map((img, idx) => (
                <span
                  key={idx}
                  className="text-[11px] font-semibold text-primary-900 bg-primary-50 px-2.5 py-0.5 rounded-md border border-primary-200"
                >
                  {img.image_id}: {formatImageType(img.image_type)} ({Math.round(img.visibility_confidence * 100)}%)
                </span>
              ))}
            </div>

            {/* Visible sections tags */}
            {images[0]?.visible_sections && images[0].visible_sections.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                <span className="text-[10px] text-slate-400 font-medium">Visible sections:</span>
                {images[0].visible_sections.map((sec, sidx) => (
                  <span
                    key={sidx}
                    className="text-[10px] font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded"
                  >
                    {sec.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 2. Structured Fields List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 max-h-[520px]">
        {/* Ambiguities / Conflicts Warnings if present */}
        {conflicts && conflicts.length > 0 && (
          <div className="p-3 rounded-xl border border-rose-200 bg-rose-50/60 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-rose-800">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              <span>Conflicting Observations Detected ({conflicts.length})</span>
            </div>
            {conflicts.map((conf, cidx) => (
              <div key={cidx} className="text-xs text-rose-900 pl-5">
                <p className="font-semibold">{conf.field}: {conf.description}</p>
                <div className="mt-1 space-y-1">
                  {conf.candidates.map((cand, candIdx) => (
                    <div key={candIdx} className="flex items-center justify-between text-[11px] font-mono bg-white p-1.5 rounded border border-rose-200">
                      <span>Value: {JSON.stringify(cand.value)} — "{cand.evidence.source_text}"</span>
                      {onSelectEvidence && (
                        <button
                          type="button"
                          onClick={() => onSelectEvidence(cand.evidence)}
                          className="text-[10px] text-primary-800 hover:underline flex items-center gap-0.5 font-sans font-semibold"
                        >
                          <span>Highlight</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {ambiguities && ambiguities.length > 0 && (
          <div className="p-3 rounded-xl border border-amber-200 bg-amber-50/60 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-amber-800">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>Ambiguous Values Preserved ({ambiguities.length})</span>
            </div>
            {ambiguities.map((amb, aidx) => (
              <p key={aidx} className="text-xs text-amber-900 pl-5 font-medium">
                <strong>{amb.field}:</strong> {amb.description}
              </p>
            ))}
          </div>
        )}

        {/* 1. Commodity Name */}
        <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/40 hover:bg-slate-50 transition-colors space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800">Commodity Name</span>
            <StatusBadge status={product.commodity_name.status} />
          </div>
          <p className="text-xs font-semibold text-slate-900">
            {product.commodity_name.value || 'Not observed in supplied images'}
          </p>
          <EvidenceList evidence={product.commodity_name.evidence} onSelectEvidence={onSelectEvidence} />
        </div>

        {/* 2. Maximum Retail Price (MRP) */}
        <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/40 hover:bg-slate-50 transition-colors space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Tag className="w-4 h-4 text-primary-800" />
              <span className="text-xs font-bold text-slate-800">Maximum Retail Price (MRP)</span>
            </div>
            <StatusBadge status={product.mrp.status} />
          </div>
          <p className="text-sm font-bold text-slate-900">
            {product.mrp.value != null ? `₹${product.mrp.value.toFixed(2)}` : 'Not observed in supplied images'}
          </p>
          <EvidenceList evidence={product.mrp.evidence} onSelectEvidence={onSelectEvidence} />
        </div>

        {/* 3. Net Quantity */}
        <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/40 hover:bg-slate-50 transition-colors space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-primary-800" />
              <span className="text-xs font-bold text-slate-800">Net Quantity</span>
            </div>
            <StatusBadge status={product.net_quantity.status} />
          </div>
          <p className="text-sm font-bold text-slate-900">
            {product.net_quantity.value != null
              ? `${product.net_quantity.value} ${product.net_quantity.unit || ''}`.trim()
              : 'Not observed in supplied images'}
          </p>
          <EvidenceList evidence={product.net_quantity.evidence} onSelectEvidence={onSelectEvidence} />
        </div>

        {/* 4. Manufacturer & Packer */}
        <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/40 hover:bg-slate-50 transition-colors space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-primary-800" />
              <span className="text-xs font-bold text-slate-800">Manufacturer / Packer Details</span>
            </div>
            <StatusBadge status={product.manufacturer.status !== 'not_observed' ? product.manufacturer.status : product.packer.status} />
          </div>
          <div className="text-xs text-slate-900 space-y-1">
            <p className="font-medium">
              {product.manufacturer.value || product.packer.value || 'Not observed in supplied images'}
            </p>
          </div>
          <EvidenceList
            evidence={[...product.manufacturer.evidence, ...product.packer.evidence]}
            onSelectEvidence={onSelectEvidence}
          />
        </div>

        {/* 5. Dates (Manufacturing / Packing / Expiry / Best Before) */}
        <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/40 hover:bg-slate-50 transition-colors space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-primary-800" />
              <span className="text-xs font-bold text-slate-800">Dates & Shelf Life</span>
            </div>
            <StatusBadge status={product.manufacturing_date.status !== 'not_observed' ? product.manufacturing_date.status : product.expiry_date.status} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-[11px] text-slate-500 block">Mfg / Packing Date</span>
              <span className="font-medium text-slate-900">
                {product.manufacturing_date.value || product.packing_date.value || 'Not observed'}
                {product.manufacturing_date.precision && (
                  <span className="text-[10px] font-mono text-slate-400 block">
                    (precision: {product.manufacturing_date.precision})
                  </span>
                )}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 block">Expiry / Best Before</span>
              <span className="font-medium text-slate-900">
                {product.expiry_date.value || product.best_before.value || 'Not observed'}
              </span>
            </div>
          </div>

          <EvidenceList
            evidence={[...product.manufacturing_date.evidence, ...product.expiry_date.evidence, ...product.best_before.evidence]}
            onSelectEvidence={onSelectEvidence}
          />
        </div>

        {/* 6. Consumer Care Helpline */}
        <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/40 hover:bg-slate-50 transition-colors space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <PhoneCall className="w-4 h-4 text-primary-800" />
              <span className="text-xs font-bold text-slate-800">Consumer Care Helpline</span>
            </div>
            <StatusBadge status={product.consumer_care.status !== 'not_observed' ? product.consumer_care.status : product.consumer_care_phone.status} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-[11px] text-slate-500 block">Phone / Toll Free</span>
              <span className="font-mono text-slate-900">
                {product.consumer_care_phone.value || 'Not observed'}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 block">Email</span>
              <span className="font-mono text-slate-900 truncate block">
                {product.consumer_care_email.value || 'Not observed'}
              </span>
            </div>
          </div>

          <EvidenceList
            evidence={[...product.consumer_care.evidence, ...product.consumer_care_phone.evidence, ...product.consumer_care_email.evidence]}
            onSelectEvidence={onSelectEvidence}
          />
        </div>

        {/* 7. Country of Origin */}
        <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/40 hover:bg-slate-50 transition-colors space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Globe2 className="w-4 h-4 text-primary-800" />
              <span className="text-xs font-bold text-slate-800">Country of Origin</span>
            </div>
            <StatusBadge status={product.country_of_origin.status} />
          </div>
          <p className="text-xs font-bold text-slate-900">
            {product.country_of_origin.value || 'Not observed in supplied images'}
          </p>
          <EvidenceList evidence={product.country_of_origin.evidence} onSelectEvidence={onSelectEvidence} />
        </div>

        {/* 8. Other Detected Information (Nutrition, Ingredients, Codes) */}
        {other_detected_information && other_detected_information.length > 0 && (
          <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/40 space-y-2">
            <span className="text-xs font-bold text-slate-800 block">
              Other Detected Information ({other_detected_information.length})
            </span>
            <div className="space-y-1.5">
              {other_detected_information.map((item, idx) => (
                <div key={idx} className="p-2 rounded bg-white border border-slate-200 text-xs flex items-center justify-between gap-2">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded mr-1.5">
                      {item.category}
                    </span>
                    <span className="font-semibold text-slate-800">{item.label}:</span>{' '}
                    <span className="text-slate-600">{item.value}</span>
                  </div>

                  {item.evidence?.[0] && onSelectEvidence && (
                    <button
                      type="button"
                      onClick={() => onSelectEvidence(item.evidence[0])}
                      className="text-[10px] text-primary-800 hover:underline flex items-center gap-0.5 font-sans font-semibold flex-shrink-0"
                    >
                      <span>Highlight</span>
                      <ExternalLink className="w-2.5 h-2.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
