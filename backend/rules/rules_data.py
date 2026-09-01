"""
Legal Metrology (Packaged Commodities) Rules, 2011 - Structured Rule Database
Maintained by Department of Consumer Affairs, Government of India
Includes Base PCR 2011 Rules and subsequent GSR amendments (e.g. GSR 779(E) USP Amendment).
"""

from typing import List, Dict, Any

LEGAL_METROLOGY_RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "PCR2011-R6-1-A",
        "rule_number": "Rule 6(1)(a)",
        "source": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_reference": "PCR 2011 Rule 6(1)(a) & DCA Notifications",
        "requirement": "Name and complete postal address of the manufacturer, packer, or importer must be clearly declared.",
        "field": "manufacturer",
        "category": "mandatory_identity",
        "default_applicability": "APPLICABLE",
        "effective_from": "2011-04-01",
        "validation_type": "name_and_address_check"
    },
    {
        "rule_id": "PCR2011-R6-1-AA",
        "rule_number": "Rule 6(1)(aa)",
        "source": "Legal Metrology (Packaged Commodities) Rules, 2011 (as amended)",
        "source_reference": "PCR 2011 Rule 6(1)(aa) / GSR 629(E)",
        "requirement": "Country of origin or manufacture/assembly must be mentioned on the package.",
        "field": "country_of_origin",
        "category": "mandatory_origin",
        "default_applicability": "APPLICABLE",
        "effective_from": "2017-06-23",
        "validation_type": "country_of_origin_check"
    },
    {
        "rule_id": "PCR2011-R6-1-B",
        "rule_number": "Rule 6(1)(b)",
        "source": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_reference": "PCR 2011 Rule 6(1)(b) read with Rule 12 & Second Schedule",
        "requirement": "Net quantity in terms of the standard unit of weight or measure (g, kg, ml, l, m, cm, pieces) or number of commodities.",
        "field": "net_quantity",
        "category": "mandatory_quantity",
        "default_applicability": "APPLICABLE",
        "effective_from": "2011-04-01",
        "validation_type": "net_quantity_standard_unit_check"
    },
    {
        "rule_id": "PCR2011-R6-1-D",
        "rule_number": "Rule 6(1)(d)",
        "source": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_reference": "PCR 2011 Rule 6(1)(d)",
        "requirement": "The month and year in which the commodity is manufactured or pre-packed or imported.",
        "field": "date_information",
        "category": "mandatory_date",
        "default_applicability": "APPLICABLE",
        "effective_from": "2011-04-01",
        "validation_type": "mfg_packing_date_check"
    },
    {
        "rule_id": "PCR2011-R6-1-E",
        "rule_number": "Rule 6(1)(e)",
        "source": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_reference": "PCR 2011 Rule 6(1)(e)",
        "requirement": "Maximum Retail Price (MRP) clearly stated in INR with 'Inclusive of all taxes' or 'Incl. of all taxes'.",
        "field": "mrp",
        "category": "mandatory_price",
        "default_applicability": "APPLICABLE",
        "effective_from": "2011-04-01",
        "validation_type": "mrp_declaration_check"
    },
    {
        "rule_id": "PCR2011-R6-1-M",
        "rule_number": "Rule 6(1)(m)",
        "source": "Legal Metrology (Packaged Commodities) Amendment Rules, 2021",
        "source_reference": "GSR 779(E) dated 02.11.2021 & GSR 226(E) dated 28.03.2022",
        "requirement": "Unit Sale Price (USP) in Rs/paise per g/kg/ml/l/number where MRP is declared on packages containing more than standard quantities.",
        "field": "mrp",
        "category": "mandatory_price",
        "default_applicability": "APPLICABLE",
        "effective_from": "2022-04-01",
        "validation_type": "unit_sale_price_check"
    },
    {
        "rule_id": "PCR2011-R6-1-F",
        "rule_number": "Rule 6(1)(f)",
        "source": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_reference": "PCR 2011 Rule 6(1)(f)",
        "requirement": "Name, complete address, telephone number, and e-mail address of the person/office to contact for consumer complaints.",
        "field": "consumer_care",
        "category": "mandatory_consumer_redressal",
        "default_applicability": "APPLICABLE",
        "effective_from": "2011-04-01",
        "validation_type": "consumer_care_check"
    },
    {
        "rule_id": "PCR2011-R6-1-N",
        "rule_number": "Rule 6(1)(n)",
        "source": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_reference": "PCR 2011 Rule 6(1)(n) read with Food Safety & Standards Regulations",
        "requirement": "Best before or use by date declaration for commodities susceptible to spoilage or fitness expiration.",
        "field": "date_information",
        "category": "conditional_date",
        "default_applicability": "APPLICABLE",
        "effective_from": "2011-04-01",
        "validation_type": "best_before_expiry_check"
    },
    {
        "rule_id": "PCR2011-R4-COMMODITY",
        "rule_number": "Rule 6(1)(b)",
        "source": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_reference": "PCR 2011 Rule 6(1)(b)",
        "requirement": "Generic or common name of the commodity contained in the package.",
        "field": "product",
        "category": "mandatory_identity",
        "default_applicability": "APPLICABLE",
        "effective_from": "2011-04-01",
        "validation_type": "commodity_name_check"
    }
]
