import type { InspectionRecord } from '../types/inspection';

/**
 * High-quality SVG Label generator for sample commodities
 */
function createSvgDataUri(title: string, details: string[], color: string, width = 600, height = 750): string {
  const lines = details.map((line, idx) => 
    `<text x="40" y="${220 + idx * 45}" font-family="Arial, sans-serif" font-size="19" font-weight="500" fill="#1E293B">${line}</text>`
  ).join('');

  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#FFFFFF;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#F8FAFC;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="${width}" height="${height}" rx="16" fill="url(#grad)" stroke="#CBD5E1" stroke-width="2"/>
  <rect x="20" y="20" width="${width - 40}" height="120" rx="10" fill="${color}" opacity="0.1"/>
  <rect x="20" y="20" width="${width - 40}" height="120" rx="10" fill="none" stroke="${color}" stroke-width="1.5" stroke-dasharray="4 4"/>
  <text x="40" y="70" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="${color}">${title}</text>
  <text x="40" y="105" font-family="Arial, sans-serif" font-size="15" font-weight="600" fill="#64748B">LEGAL METROLOGY (PACKAGED COMMODITIES) RULES 2011 DECLARATION</text>
  <line x1="40" y1="160" x2="${width - 40}" y2="160" stroke="#E2E8F0" stroke-width="2"/>
  ${lines}
  <rect x="40" y="${height - 110}" width="${width - 80}" height="70" rx="8" fill="#F1F5F9" stroke="#E2E8F0" stroke-width="1"/>
  <text x="60" y="${height - 78}" font-family="Arial, sans-serif" font-size="15" font-weight="600" fill="#334155">FOR CONSUMER COMPLAINTS / FEEDBACK:</text>
  <text x="60" y="${height - 54}" font-family="Arial, sans-serif" font-size="14" fill="#475569">Email: care@packageconsumer.in | Toll Free: 1800-209-1234</text>
</svg>`;

  return `data:image/svg+xml;utf8,${encodeURIComponent(svg.trim())}`;
}

export const SAMPLE_INSPECTIONS: InspectionRecord[] = [
  {
    id: "INSP-2026-0830-001",
    metadata: {
      inspection_id: "INSP-2026-0830-001",
      created_at: "2026-08-30T10:15:00Z",
      updated_at: "2026-08-30T10:16:30Z",
      product_name: "Amul Gold Full Cream Milk 1000ml",
      brand_name: "Amul",
      category: "Dairy & Beverage",
      declared_mrp: "₹66.00 (Incl. of all taxes)",
      declared_quantity: "1000 ml (1 L)",
      image_count: 1,
      status: "Compliant",
      notes: "Mandatory declarations compliant with Rule 6(1) of PCR 2011.",
      inspector_name: "Inspector Rajesh Kumar (Zone-4)",
    },
    instructionPrompt: "Check this package for mandatory declarations under Legal Metrology Rules, including MRP, net volume, manufacturing date, and customer care details.",
    structuredInstruction: {
      task: "verify_mandatory_declarations",
      fields: ["mrp", "net_quantity", "manufacturer", "mfg_date", "expiry_date", "consumer_care", "unit_sale_price"],
      rules: ["Rule 6(1)(a) PCR 2011", "Rule 6(1)(b)", "Rule 6(1)(c)", "Rule 6(1)(e)", "Rule 6(1)(f)"],
      language: "en",
      extracted_keywords: ["mandatory declarations", "MRP", "net volume", "manufacturer"],
      parsed_at: "2026-08-30T10:15:05Z",
    },
    images: [
      {
        id: "img_001",
        name: "amul_gold_front_label.jpg",
        size: 245820,
        type: "image/jpeg",
        previewUrl: createSvgDataUri(
          "AMUL GOLD FULL CREAM MILK",
          [
            "Product Name: Pasteurised Homogenised Milk",
            "Net Volume: 1000 ml (1 L)",
            "MRP: Rs. 66.00 (Inclusive of all taxes)",
            "Unit Sale Price: Rs. 0.066 / ml",
            "Mfg & Packed by: Kaira District Co-op Milk Producers Union Ltd, Anand 388001",
            "Batch No: B4498 / Packed on: 28/08/2026",
            "Use by: 31/08/2026",
            "FSSAI Lic. No. 10014021000085",
            "Country of Origin: INDIA"
          ],
          "#1E3A8A",
          600,
          750
        ),
        width: 600,
        height: 750,
        uploadedAt: "2026-08-30T10:15:00Z"
      }
    ],
    ocrResult: {
      inspection_id: "INSP-2026-0830-001",
      engine: "RapidOCR ONNX (Server Engine)",
      processing_time_ms: 642,
      images: [
        {
          image_id: "img_001",
          dimensions: { width: 600, height: 750 },
          ocr: [
            {
              id: "ocr_01",
              text: "AMUL GOLD FULL CREAM MILK",
              confidence: 0.99,
              bbox: [35, 45, 520, 95],
              fieldCategory: "generic_name"
            },
            {
              id: "ocr_02",
              text: "Product Name: Pasteurised Homogenised Milk",
              confidence: 0.98,
              bbox: [35, 195, 460, 235],
              fieldCategory: "generic_name"
            },
            {
              id: "ocr_03",
              text: "Net Volume: 1000 ml (1 L)",
              confidence: 0.99,
              bbox: [35, 240, 320, 280],
              fieldCategory: "net_quantity"
            },
            {
              id: "ocr_04",
              text: "MRP: Rs. 66.00 (Inclusive of all taxes)",
              confidence: 0.98,
              bbox: [35, 285, 430, 325],
              fieldCategory: "mrp"
            },
            {
              id: "ocr_05",
              text: "Unit Sale Price: Rs. 0.066 / ml",
              confidence: 0.96,
              bbox: [35, 330, 350, 370],
              fieldCategory: "mrp"
            },
            {
              id: "ocr_06",
              text: "Mfg & Packed by: Kaira District Co-op Milk Producers Union Ltd, Anand 388001",
              confidence: 0.97,
              bbox: [35, 375, 560, 415],
              fieldCategory: "manufacturer"
            },
            {
              id: "ocr_07",
              text: "Batch No: B4498 / Packed on: 28/08/2026",
              confidence: 0.95,
              bbox: [35, 420, 420, 460],
              fieldCategory: "mfg_date"
            },
            {
              id: "ocr_08",
              text: "Use by: 31/08/2026",
              confidence: 0.98,
              bbox: [35, 465, 220, 505],
              fieldCategory: "expiry_date"
            },
            {
              id: "ocr_09",
              text: "FSSAI Lic. No. 10014021000085",
              confidence: 0.96,
              bbox: [35, 510, 360, 550],
              fieldCategory: "fssai_lic"
            },
            {
              id: "ocr_10",
              text: "Country of Origin: INDIA",
              confidence: 0.99,
              bbox: [35, 555, 300, 595],
              fieldCategory: "country_of_origin"
            },
            {
              id: "ocr_11",
              text: "Email: care@packageconsumer.in | Toll Free: 1800-209-1234",
              confidence: 0.97,
              bbox: [50, 675, 540, 715],
              fieldCategory: "consumer_care"
            }
          ]
        }
      ]
    },
    ruleChecks: [
      {
        rule_id: "RULE_01",
        rule_name: "Name and Address of Manufacturer / Packer",
        regulation_ref: "Rule 6(1)(a) PCR 2011",
        description: "Complete postal address and registered manufacturer name must be clearly stated.",
        status: "satisfied",
        detected_text: "Mfg & Packed by: Kaira District Co-op Milk Producers Union Ltd, Anand 388001",
        evidence_region_id: "ocr_06"
      },
      {
        rule_id: "RULE_02",
        rule_name: "Country of Origin (Imported/Indigenous)",
        regulation_ref: "Rule 6(1)(aa) PCR 2011",
        description: "Country of origin must be declared on the principal display panel.",
        status: "satisfied",
        detected_text: "Country of Origin: INDIA",
        evidence_region_id: "ocr_10"
      },
      {
        rule_id: "RULE_03",
        rule_name: "Net Quantity with Standard Metric Units",
        regulation_ref: "Rule 6(1)(b) & Rule 12 PCR 2011",
        description: "Net quantity in standard SI units (g, kg, ml, l) with prescribed minimum font height.",
        status: "satisfied",
        detected_text: "Net Volume: 1000 ml (1 L)",
        evidence_region_id: "ocr_03"
      },
      {
        rule_id: "RULE_04",
        rule_name: "Month & Year of Manufacture / Packing",
        regulation_ref: "Rule 6(1)(d) PCR 2011",
        description: "Clear declaration of month and year in which commodity is manufactured or packed.",
        status: "satisfied",
        detected_text: "Packed on: 28/08/2026",
        evidence_region_id: "ocr_07"
      },
      {
        rule_id: "RULE_05",
        rule_name: "Maximum Retail Price (MRP) & Unit Sale Price",
        regulation_ref: "Rule 6(1)(e) & Rule 6(1)(m) PCR 2011",
        description: "MRP formatted with 'inclusive of all taxes' and mandatory Unit Sale Price for commodities.",
        status: "satisfied",
        detected_text: "MRP: Rs. 66.00 (Inclusive of all taxes) / USP: Rs. 0.066 / ml",
        evidence_region_id: "ocr_04"
      },
      {
        rule_id: "RULE_06",
        rule_name: "Consumer Care Contact Details",
        regulation_ref: "Rule 6(1)(f) PCR 2011",
        description: "Name, address, telephone number and email address for consumer grievances.",
        status: "satisfied",
        detected_text: "Email: care@packageconsumer.in | Toll Free: 1800-209-1234",
        evidence_region_id: "ocr_11"
      }
    ]
  },
  {
    id: "INSP-2026-0830-002",
    metadata: {
      inspection_id: "INSP-2026-0830-002",
      created_at: "2026-08-30T09:40:00Z",
      updated_at: "2026-08-30T09:42:15Z",
      product_name: "Haldiram's Bhujia Sev 400g",
      brand_name: "Haldiram's",
      category: "Packaged Snack Foods",
      declared_mrp: "₹110.00",
      declared_quantity: "400 g",
      image_count: 1,
      status: "Needs Review",
      notes: "Unit sale price font size requires verification under Rule 7.",
      inspector_name: "Inspector Rajesh Kumar (Zone-4)",
    },
    instructionPrompt: "Extract the MRP, net quantity and manufacturer details and verify against Legal Metrology guidelines.",
    structuredInstruction: {
      task: "extract_and_verify",
      fields: ["mrp", "net_quantity", "manufacturer", "unit_sale_price"],
      rules: ["Rule 6(1)(a)", "Rule 6(1)(e)", "Rule 6(1)(m)"],
      language: "en",
      extracted_keywords: ["MRP", "net quantity", "manufacturer"],
      parsed_at: "2026-08-30T09:40:05Z",
    },
    images: [
      {
        id: "img_002",
        name: "haldiram_bhujia_back.jpg",
        size: 310500,
        type: "image/jpeg",
        previewUrl: createSvgDataUri(
          "HALDIRAM BHUJIA SEV 400g",
          [
            "Generic Name: Spiced Moth Bean Flour Savoury",
            "Net Weight: 400 g",
            "Max Retail Price: Rs. 110.00 (Incl. of taxes)",
            "Unit Sale Price: Rs. 0.275 / g",
            "Manufactured by: Haldiram Snacks Pvt Ltd, Noida (UP) 201307",
            "Mfg Date: 15/07/2026 / Best Before 6 Months",
            "Batch No: HLB-902",
            "Customer Care: feedback@haldiram.com"
          ],
          "#D97706",
          600,
          750
        ),
        width: 600,
        height: 750,
        uploadedAt: "2026-08-30T09:40:00Z"
      }
    ],
    ocrResult: {
      inspection_id: "INSP-2026-0830-002",
      engine: "RapidOCR ONNX (Server Engine)",
      processing_time_ms: 710,
      images: [
        {
          image_id: "img_002",
          dimensions: { width: 600, height: 750 },
          ocr: [
            {
              id: "ocr_201",
              text: "HALDIRAM BHUJIA SEV 400g",
              confidence: 0.99,
              bbox: [35, 45, 500, 95],
              fieldCategory: "generic_name"
            },
            {
              id: "ocr_202",
              text: "Generic Name: Spiced Moth Bean Flour Savoury",
              confidence: 0.97,
              bbox: [35, 195, 490, 235],
              fieldCategory: "generic_name"
            },
            {
              id: "ocr_203",
              text: "Net Weight: 400 g",
              confidence: 0.99,
              bbox: [35, 240, 240, 280],
              fieldCategory: "net_quantity"
            },
            {
              id: "ocr_204",
              text: "Max Retail Price: Rs. 110.00 (Incl. of taxes)",
              confidence: 0.98,
              bbox: [35, 285, 460, 325],
              fieldCategory: "mrp"
            },
            {
              id: "ocr_205",
              text: "Unit Sale Price: Rs. 0.275 / g",
              confidence: 0.94,
              bbox: [35, 330, 340, 370],
              fieldCategory: "mrp"
            },
            {
              id: "ocr_206",
              text: "Manufactured by: Haldiram Snacks Pvt Ltd, Noida (UP) 201307",
              confidence: 0.96,
              bbox: [35, 375, 560, 415],
              fieldCategory: "manufacturer"
            },
            {
              id: "ocr_207",
              text: "Mfg Date: 15/07/2026 / Best Before 6 Months",
              confidence: 0.97,
              bbox: [35, 420, 480, 460],
              fieldCategory: "mfg_date"
            }
          ]
        }
      ]
    },
    ruleChecks: [
      {
        rule_id: "RULE_01",
        rule_name: "Name and Address of Manufacturer",
        regulation_ref: "Rule 6(1)(a) PCR 2011",
        description: "Complete manufacturer name and address required.",
        status: "satisfied",
        detected_text: "Haldiram Snacks Pvt Ltd, Noida (UP) 201307",
        evidence_region_id: "ocr_206"
      },
      {
        rule_id: "RULE_02",
        rule_name: "Net Weight & Metric Unit",
        regulation_ref: "Rule 6(1)(b) PCR 2011",
        description: "Net quantity declaration in grams.",
        status: "satisfied",
        detected_text: "Net Weight: 400 g",
        evidence_region_id: "ocr_203"
      },
      {
        rule_id: "RULE_03",
        rule_name: "Unit Sale Price Font Size Verification",
        regulation_ref: "Rule 6(1)(m) PCR 2011",
        description: "Unit sale price must be displayed clearly with standard unit ratio.",
        status: "violation",
        detected_text: "Unit Sale Price: Rs. 0.275 / g",
        evidence_region_id: "ocr_205",
        notes: "Potential violation: Unit sale price font height is smaller than 50% of the MRP font height."
      }
    ]
  }
];
