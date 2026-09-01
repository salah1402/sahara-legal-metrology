import type { Evidence } from './normalized';

export type CheckStatus = 'PASS' | 'FAIL' | 'NEEDS_REVIEW' | 'NOT_APPLICABLE' | 'EXEMPT';
export type OverallStatus = 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW';

export interface LegalSource {
  instrument: string;
  notification?: string;
  effective_from: string;
  source_url?: string;
  source_type: string;
}

export interface ExemptionAuditInfo {
  exemption_rule: string;
  exemption_clause: string;
  reason: string;
  factual_conditions_checked: string[];
  evidence: Evidence[];
}

export interface ApplicabilityFacts {
  is_prepackaged_commodity: boolean;
  intended_for_retail_sale: boolean;
  package_category: string;
  commodity_type: string;
  is_imported: boolean;
  is_electronic_product: boolean;
  is_medical_device: boolean;
  is_garment_or_hosiery: boolean;
  is_wholesale_package: boolean;
  is_export_package: boolean;
  is_group_package: boolean;
  is_combination_package: boolean;
  is_multi_piece_package: boolean;
  is_exempt_under_rule_26: boolean;
  rule_26_clause?: string;
  exemption_reason?: string;
  exemption_conditions?: string[];
  is_fast_food_restaurant_packed?: boolean;
  is_institutional_or_industrial?: boolean;
  is_price_revision_scenario: boolean;
  applicability_confidence: number;
}

export interface RuleApplicabilityDecision {
  status: 'APPLICABLE' | 'NOT_APPLICABLE' | 'NEEDS_REVIEW' | 'EXEMPT';
  reason: string;
}

export interface RuleCheckResult {
  rule_id: string;
  rule_number: string;
  title: string;
  status: CheckStatus;
  applicability: RuleApplicabilityDecision;
  observed_value?: string;
  required_value?: string;
  reason: string;
  evidence: Evidence[];
  legal_source: LegalSource;
  exemption?: ExemptionAuditInfo;
}

export interface ComplianceSummary {
  total_checks: number;
  passed: number;
  failed: number;
  needs_review: number;
  not_applicable: number;
  exempt: number;
}

export interface LegalFrameworkInfo {
  name: string;
  registry_version: string;
  effective_as_of: string;
}

export interface ComplianceResult {
  schema_version: string;
  inspection_id: string;
  inspection_date: string;
  overall_status: OverallStatus;
  legal_framework: LegalFrameworkInfo;
  applicability: ApplicabilityFacts;
  summary: ComplianceSummary;
  checks: RuleCheckResult[];
  evaluator_version: string;
}
