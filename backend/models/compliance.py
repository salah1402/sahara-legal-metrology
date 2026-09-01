from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from backend.models.schemas import Evidence

CheckStatus = Literal["PASS", "FAIL", "NEEDS_REVIEW", "NOT_APPLICABLE", "EXEMPT"]
OverallStatus = Literal["COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW"]


class LegalSource(BaseModel):
    instrument: str = Field(..., description="Legal act or rules instrument name")
    notification: Optional[str] = Field(None, description="Official Gazette notification number")
    effective_from: str = Field(..., description="ISO date when provision became legally effective")
    source_url: Optional[str] = Field(None, description="Official Department of Consumer Affairs or Gazette URL")
    source_type: str = Field("official_gazette", description="Source classification")


class ExemptionAuditInfo(BaseModel):
    exemption_rule: str = Field("PCR-2011-R26", description="Statutory rule granting exemption")
    exemption_clause: str = Field(..., description="Specific statutory clause e.g. 26(a), 26(b), 26(c)")
    reason: str = Field(..., description="Detailed legal explanation of why exemption conditions are satisfied")
    factual_conditions_checked: List[str] = Field(default_factory=list, description="Factual prerequisites verified")
    evidence: List[Evidence] = Field(default_factory=list, description="Direct supporting OCR evidence")


class ApplicabilityFacts(BaseModel):
    is_prepackaged_commodity: bool = True
    intended_for_retail_sale: bool = True
    package_category: str = "retail"
    commodity_type: str = "general"
    is_imported: bool = False
    is_electronic_product: bool = False
    is_medical_device: bool = False
    is_garment_or_hosiery: bool = False
    is_wholesale_package: bool = False
    is_export_package: bool = False
    is_group_package: bool = False
    is_combination_package: bool = False
    is_multi_piece_package: bool = False
    is_exempt_under_rule_26: bool = False
    rule_26_clause: Optional[str] = None
    exemption_reason: Optional[str] = None
    exemption_conditions: List[str] = Field(default_factory=list)
    is_fast_food_restaurant_packed: bool = False
    is_institutional_or_industrial: bool = False
    is_price_revision_scenario: bool = False
    applicability_confidence: float = 1.0


class RuleApplicabilityDecision(BaseModel):
    status: Literal["APPLICABLE", "NOT_APPLICABLE", "NEEDS_REVIEW", "EXEMPT"] = "APPLICABLE"
    reason: str = "Rule is applicable to packaged commodity category."


class RuleCheckResult(BaseModel):
    rule_id: str
    rule_number: str
    title: str
    status: CheckStatus
    applicability: RuleApplicabilityDecision
    observed_value: Optional[str] = None
    required_value: Optional[str] = None
    reason: str
    evidence: List[Evidence] = Field(default_factory=list)
    legal_source: LegalSource
    exemption: Optional[ExemptionAuditInfo] = None


class ComplianceSummary(BaseModel):
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    needs_review: int = 0
    not_applicable: int = 0
    exempt: int = 0


class LegalFrameworkInfo(BaseModel):
    name: str = "Legal Metrology (Packaged Commodities) Rules, 2011"
    registry_version: str = "PCR-2011-CURRENT"
    effective_as_of: str


class ComplianceResult(BaseModel):
    schema_version: str = "1.0"
    inspection_id: str
    inspection_date: str
    overall_status: OverallStatus
    legal_framework: LegalFrameworkInfo
    applicability: ApplicabilityFacts
    summary: ComplianceSummary
    checks: List[RuleCheckResult]
    evaluator_version: str = "2.1.0"
