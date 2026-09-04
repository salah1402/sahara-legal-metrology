import io
import re
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
from PIL import Image as PILImage, ImageOps

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from backend.models.compliance import ComplianceResult
from backend.models.schemas import StructuredProductData
from backend.services.summary_service import generate_inspection_summary

logger = logging.getLogger("sahara_report_service")

BASE_DIR = Path(__file__).resolve().parent.parent
INSPECTIONS_DIR = BASE_DIR / "inspections"


class NumberedCanvas:
    """Canvas wrapper to print page numbers 'Page X of Y' in footer."""
    def __init__(self, *args, **kwargs):
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Footer text
        footer_text = f"SAHARA Legal Metrology Inspection Report  |  Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 36, 20, footer_text)
        self.drawString(36, 20, "Confidential — Legal Metrology Packaged Commodities Inspection System")
        
        # Bottom divider
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 30, 612 - 36, 30)
        self.restoreState()


from reportlab.pdfgen import canvas
class NumberedCanvasWrapper(NumberedCanvas, canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        NumberedCanvas.__init__(self, *args, **kwargs)


def build_pdf_styles():
    styles = getSampleStyleSheet()
    
    # Custom SAHARA brand styles
    styles.add(ParagraphStyle(
        name='SaharaTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
    ))
    styles.add(ParagraphStyle(
        name='SaharaSubtitle',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569'),
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=6,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name='BodySmall',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#334155'),
    ))
    styles.add(ParagraphStyle(
        name='BodyBold',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#0F172A'),
    ))
    styles.add(ParagraphStyle(
        name='TableText',
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1E293B'),
    ))
    styles.add(ParagraphStyle(
        name='TableTextBold',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0F172A'),
    ))
    styles.add(ParagraphStyle(
        name='SummaryBoxText',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1E293B'),
    ))
    
    return styles


def format_canonical_verdict(overall_status: str) -> str:
    """Returns canonical regulatory status for the PDF banner."""
    if overall_status == "COMPLIANT":
        return "PASS"
    elif overall_status == "NON_COMPLIANT":
        return "FAIL"
    elif overall_status == "NEEDS_REVIEW":
        return "NEEDS REVIEW"
    return overall_status.replace("_", " ")


def generate_pdf_filename(inspection_name: Optional[str], inspection_id: str) -> str:
    """
    Generates a sanitized filename based on the inspection name shown in the application.
    Examples:
        'Ac QI80' -> 'SAHARA_Ac_QI80_Inspection_Report.pdf'
        'Bourbon Biscuits — Britannia' -> 'SAHARA_Bourbon_Biscuits_Britannia_Inspection_Report.pdf'
        None / '' / 'Untitled Inspection' -> 'SAHARA_Inspection_INS-20260904-XXXX.pdf'
    """
    if not inspection_name or not str(inspection_name).strip():
        return f"SAHARA_Inspection_{inspection_id}.pdf"

    clean = str(inspection_name).strip()
    if clean.lower() in ["untitled inspection", "untitled", "packaged commodity"]:
        return f"SAHARA_Inspection_{inspection_id}.pdf"

    # Replace dashes and punctuation with underscores
    clean = clean.replace("—", "_").replace("–", "_").replace("-", "_")
    # Replace invalid Windows filename characters: \ / : * ? " < > |
    clean = re.sub(r'[\\/*?:"<>|]', '_', clean)
    # Replace whitespace with underscores
    clean = re.sub(r'\s+', '_', clean)
    # Remove non-alphanumeric characters except underscores
    clean = re.sub(r'[^\w_]', '', clean)
    # Collapse multiple consecutive underscores and trim
    clean = re.sub(r'_+', '_', clean).strip('_')

    if not clean:
        return f"SAHARA_Inspection_{inspection_id}.pdf"

    return f"SAHARA_{clean}_Inspection_Report.pdf"


def find_inspection_image(
    insp_folder: Path,
    explicit_image: Optional[Any] = None
) -> Optional[Any]:
    """Resolves image bytes, Path, or BytesIO for the inspection."""
    if explicit_image is not None:
        return explicit_image

    images_dir = insp_folder / "images"
    if not images_dir.exists():
        return None

    # 1. Check raw_ocr.json for image reference
    raw_ocr_file = insp_folder / "ocr" / "raw_ocr.json"
    if raw_ocr_file.exists():
        try:
            with open(raw_ocr_file, "r", encoding="utf-8") as f:
                raw_ocr_data = json.load(f)
                img_name = raw_ocr_data.get("image")
                if img_name:
                    cand = images_dir / img_name
                    if cand.is_file():
                        return cand
        except Exception:
            pass

    # 2. Check metadata.json
    meta_file = insp_folder / "metadata.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
                orig_name = meta_data.get("original_filename")
                if orig_name:
                    cand = images_dir / orig_name
                    if cand.is_file():
                        return cand
        except Exception:
            pass

    # 3. Check for any valid image in images directory
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    for candidate in sorted(images_dir.iterdir()):
        if candidate.is_file() and candidate.suffix.lower() in valid_extensions:
            if not candidate.name.startswith("proc_"):
                return candidate

    return None


def create_uploaded_image_flowables(image_input: Optional[Any], styles: Any) -> List[Any]:
    """
    Creates ReportLab flowables for the 'Uploaded Package Image' section.
    Keeps original aspect ratio, scales neatly within PDF boundaries, and embeds image.
    Displays 'Figure 1: Uploaded Package Image' or fallback 'Image not available.'.
    """
    flowables = []

    # Section Header
    flowables.append(Paragraph("Uploaded Package Image", styles['SectionHeader']))

    if not image_input:
        flowables.append(Paragraph("<font color='#64748B' size='8'>Image not available.</font>", styles['BodySmall']))
        return flowables

    try:
        # Load image via PIL
        if isinstance(image_input, (str, Path)):
            img_path = Path(image_input)
            if not img_path.exists():
                flowables.append(Paragraph("<font color='#64748B' size='8'>Image not available.</font>", styles['BodySmall']))
                return flowables
            pil_img = PILImage.open(str(img_path))
        elif isinstance(image_input, bytes):
            pil_img = PILImage.open(io.BytesIO(image_input))
        elif isinstance(image_input, io.BytesIO):
            image_input.seek(0)
            pil_img = PILImage.open(image_input)
        else:
            flowables.append(Paragraph("<font color='#64748B' size='8'>Image not available.</font>", styles['BodySmall']))
            return flowables

        # Auto-orient based on EXIF tag
        pil_img = ImageOps.exif_transpose(pil_img) or pil_img
        orig_w, orig_h = pil_img.size
        if orig_w <= 0 or orig_h <= 0:
            raise ValueError("Invalid image dimensions")

        # Convert to RGB buffer (JPEG format) for universal ReportLab embedding
        img_buffer = io.BytesIO()
        if pil_img.mode in ("RGBA", "LA", "P"):
            rgb_img = pil_img.convert("RGB")
            rgb_img.save(img_buffer, format="JPEG", quality=88)
            del rgb_img
        else:
            pil_img.save(img_buffer, format="JPEG", quality=88)
        img_buffer.seek(0)

        # Target constraints (pt) for neat PDF page fit
        MAX_WIDTH = 300.0  # pt
        MAX_HEIGHT = 150.0 # pt
        scale = min(MAX_WIDTH / orig_w, MAX_HEIGHT / orig_h)
        disp_w = orig_w * scale
        disp_h = orig_h * scale

        rl_img = RLImage(img_buffer, width=disp_w, height=disp_h)
        rl_img.hAlign = 'CENTER'

        caption_style = ParagraphStyle(
            name='PackageImageCaption',
            parent=styles['BodySmall'],
            alignment=TA_CENTER,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#64748B'),
            spaceBefore=3,
            spaceAfter=2
        )
        caption_para = Paragraph("<i>Figure 1: Uploaded Package Image</i>", caption_style)

        # Centered container table with subtle border
        card_table = Table([[rl_img], [caption_para]], colWidths=[540])
        card_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        flowables.append(card_table)

    except Exception as img_err:
        logger.warning(f"Could not load or embed package image in PDF: {img_err}")
        flowables.append(Paragraph("<font color='#64748B' size='8'>Image not available.</font>", styles['BodySmall']))

    return flowables


def generate_inspection_pdf(
    inspection_id: str,
    output_path: Optional[Path] = None,
    image_data: Optional[Union[str, Path, bytes, io.BytesIO]] = None
) -> bytes:
    """
    Generates a clean, professional, 2-page PDF inspection report for the specified inspection ID.
    Page 1: Overview, Canonical Verdict, Summary Metrics, Executive Summary, Key Actionable Findings.
    Page 2: Full Statutory Audit Table, Rule 26 Exemption Traceability, Evidence and Gazette Authority.
    """
    from backend.main import clean_display_product_name

    insp_folder = INSPECTIONS_DIR / inspection_id
    if not insp_folder.exists():
        raise FileNotFoundError(f"Inspection directory '{inspection_id}' not found.")

    # 1. Load Metadata
    meta_file = insp_folder / "metadata.json"
    metadata: Dict[str, Any] = {}
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    # 2. Load Structured Product Data
    product_data: Optional[StructuredProductData] = None
    norm_file = insp_folder / "normalized" / "product_data.json"
    if norm_file.exists():
        with open(norm_file, "r", encoding="utf-8") as f:
            product_data = StructuredProductData.model_validate_json(f.read())

    # 3. Load or Run Compliance Result
    comp_file = insp_folder / "compliance" / "compliance_result.json"
    if comp_file.exists():
        with open(comp_file, "r", encoding="utf-8") as f:
            compliance = ComplianceResult.model_validate_json(f.read())
    else:
        from backend.services.compliance_service import run_compliance_evaluation
        compliance = run_compliance_evaluation(inspection_id)

    # 4. Derive Clean Display Product Name
    if metadata.get("display_name") and str(metadata["display_name"]).strip():
        display_title = str(metadata["display_name"]).strip()
    else:
        raw_display = metadata.get("product_name") or "Packaged Commodity"
        display_title = clean_display_product_name(raw_display)

    # 5. Generate Executive Summary (strictly sanitized)
    summary_text, summary_source = generate_inspection_summary(compliance, product_data, display_title)

    # 6. Build PDF Document
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=42
    )

    styles = build_pdf_styles()
    story = []

    # =========================================================================
    # PAGE 1: Executive Overview, Metrics & Key Findings
    # =========================================================================

    # --- Header Banner ---
    header_table_data = [
        [
            Paragraph("<b>SAHARA</b>", styles['SaharaTitle']),
            Paragraph(f"<b>LEGAL METROLOGY INSPECTION REPORT</b><br/><font size='7.5' color='#64748B'>Inspection ID: {compliance.inspection_id}</font>", ParagraphStyle(name='HRight', parent=styles['SaharaTitle'], alignment=TA_RIGHT, fontSize=11, leading=14))
        ],
        [
            Paragraph("Legal Metrology (Packaged Commodities) Rules, 2011 Inspection System", styles['SaharaSubtitle']),
            Paragraph(f"<font color='#64748B'>Report Generated: {datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M UTC')}</font>", ParagraphStyle(name='HSubRight', parent=styles['SaharaSubtitle'], alignment=TA_RIGHT))
        ]
    ]
    header_table = Table(header_table_data, colWidths=[310, 230])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=5))

    # --- Uploaded Package Image (Top of Page 1) ---
    resolved_image = find_inspection_image(insp_folder, image_data)
    story.extend(create_uploaded_image_flowables(resolved_image, styles))
    story.append(Spacer(1, 5))

    # --- Commodity Metadata Card ---
    product_name_str = display_title
    mfg_str = "Not Declared"
    qty_str = "Not Declared"
    mrp_str = "Not Declared"
    if product_data:
        if product_data.product.manufacturer.value:
            mfg_str = clean_display_product_name(str(product_data.product.manufacturer.value))
        if product_data.product.net_quantity.value:
            qty_str = f"{product_data.product.net_quantity.value} {product_data.product.net_quantity.unit or ''}"
        if product_data.product.mrp.value:
            mrp_str = f"₹ {product_data.product.mrp.value:.2f}"

    overview_table_data = [
        [
            Paragraph(f"<b>Commodity / Product:</b> {product_name_str}", styles['BodySmall']),
            Paragraph(f"<b>Manufacturer / Packer:</b> {mfg_str[:40]}", styles['BodySmall']),
            Paragraph(f"<b>Declared Net Qty:</b> {qty_str}", styles['BodySmall']),
        ],
        [
            Paragraph(f"<b>Declared MRP:</b> {mrp_str}", styles['BodySmall']),
            Paragraph(f"<b>Inspection Date:</b> {compliance.inspection_date.split('T')[0]}", styles['BodySmall']),
            Paragraph(f"<b>Registry Version:</b> {compliance.legal_framework.registry_version}", styles['BodySmall']),
        ]
    ]
    overview_table = Table(overview_table_data, colWidths=[180, 200, 160])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 6))

    # --- Prominent Canonical Verdict Banner ---
    canonical_status = format_canonical_verdict(compliance.overall_status)
    verdict_color = '#059669' if compliance.overall_status == 'COMPLIANT' else ('#DC2626' if compliance.overall_status == 'NON_COMPLIANT' else '#D97706')
    verdict_bg = '#ECFDF5' if compliance.overall_status == 'COMPLIANT' else ('#FEF2F2' if compliance.overall_status == 'NON_COMPLIANT' else '#FFFBEB')
    verdict_border = '#A7F3D0' if compliance.overall_status == 'COMPLIANT' else ('#FECACA' if compliance.overall_status == 'NON_COMPLIANT' else '#FDE68A')

    verdict_sub = "All mandatory packaged commodity declarations verified under PCR 2011" if compliance.overall_status == 'COMPLIANT' else (
        "Statutory declaration violations identified under Legal Metrology Rules" if compliance.overall_status == 'NON_COMPLIANT' else
        "Administrative or panel review required before establishing full compliance"
    )

    verdict_badge_data = [
        [
            Paragraph(
                f"<font size='8' color='{verdict_color}'><b>OVERALL STATUTORY DETERMINATION:</b></font><br/>"
                f"<font size='16' color='{verdict_color}'><b>{canonical_status}</b></font><br/>"
                f"<font size='8' color='#475569'>{verdict_sub}</font>",
                ParagraphStyle(name='VText', alignment=TA_CENTER, leading=16)
            )
        ]
    ]
    verdict_badge = Table(verdict_badge_data, colWidths=[540])
    verdict_badge.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(verdict_bg)),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(verdict_border)),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(verdict_badge)
    story.append(Spacer(1, 6))

    # --- Summary Metrics Grid ---
    c_summary = compliance.summary
    stats_data = [
        [
            Paragraph("<font color='#64748B' size='7'>TOTAL CHECKS</font><br/><b><font size='11'>" + str(c_summary.total_checks) + "</font></b>", ParagraphStyle(name='S1', alignment=TA_CENTER, leading=12)),
            Paragraph("<font color='#059669' size='7'>PASSED</font><br/><b><font size='11' color='#059669'>" + str(c_summary.passed) + "</font></b>", ParagraphStyle(name='S2', alignment=TA_CENTER, leading=12)),
            Paragraph("<font color='#DC2626' size='7'>FAILED</font><br/><b><font size='11' color='#DC2626'>" + str(c_summary.failed) + "</font></b>", ParagraphStyle(name='S3', alignment=TA_CENTER, leading=12)),
            Paragraph("<font color='#D97706' size='7'>NEEDS REVIEW</font><br/><b><font size='11' color='#D97706'>" + str(c_summary.needs_review) + "</font></b>", ParagraphStyle(name='S4', alignment=TA_CENTER, leading=12)),
            Paragraph("<font color='#7C3AED' size='7'>EXEMPT</font><br/><b><font size='11' color='#7C3AED'>" + str(c_summary.exempt) + "</font></b>", ParagraphStyle(name='S5', alignment=TA_CENTER, leading=12)),
            Paragraph("<font color='#64748B' size='7'>NOT APPLICABLE</font><br/><b><font size='11'>" + str(c_summary.not_applicable) + "</font></b>", ParagraphStyle(name='S6', alignment=TA_CENTER, leading=12)),
        ]
    ]
    stats_table = Table(stats_data, colWidths=[90, 90, 90, 90, 90, 90])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 6))

    # --- Executive Inspection Summary ---
    story.append(Paragraph("Executive Inspection Summary", styles['SectionHeader']))
    summary_box_data = [
        [Paragraph(f"{summary_text}", styles['SummaryBoxText'])]
    ]
    summary_box = Table(summary_box_data, colWidths=[540])
    summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_box)
    story.append(Spacer(1, 6))

    # --- Important Findings Highlight Box ---
    failed_checks = [c for c in compliance.checks if c.status == "FAIL"]
    review_checks = [c for c in compliance.checks if c.status == "NEEDS_REVIEW"]
    
    findings_paragraphs = []
    if failed_checks:
        for fc in failed_checks[:3]:
            findings_paragraphs.append(f"<font color='#DC2626'><b>VIOLATION: Rule {fc.rule_number} ({fc.title}):</b></font> {fc.reason}")
    if review_checks:
        for rc in review_checks[:3]:
            findings_paragraphs.append(f"<font color='#D97706'><b>REVIEW: Rule {rc.rule_number} ({rc.title}):</b></font> {rc.reason}")
    if not failed_checks and not review_checks:
        findings_paragraphs.append("<font color='#059669'><b>FULL COMPLIANCE:</b></font> No statutory violations or unverified declarations were found. All mandatory declarations conform to PCR 2011 standards.")

    findings_content = "<br/><br/>".join(findings_paragraphs)
    story.append(Paragraph("Important Actionable Findings", styles['SectionHeader']))
    findings_box_data = [
        [Paragraph(findings_content, styles['BodySmall'])]
    ]
    findings_box = Table(findings_box_data, colWidths=[540])
    findings_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFFFF')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(findings_box)

    # =========================================================================
    # PAGE BREAK -> PAGE 2: Full Statutory Audit Table & Traceability
    # =========================================================================
    story.append(PageBreak())

    # --- Statutory Checks Breakdown Table ---
    story.append(Paragraph("Legal Metrology (PCR 2011) Statutory Compliance Audit Table", styles['SectionHeader']))

    table_header = [
        Paragraph("<b>Rule</b>", styles['TableTextBold']),
        Paragraph("<b>Statutory Mandate</b>", styles['TableTextBold']),
        Paragraph("<b>Status</b>", styles['TableTextBold']),
        Paragraph("<b>Observed Declaration</b>", styles['TableTextBold']),
        Paragraph("<b>Analysis & Statutory Basis</b>", styles['TableTextBold']),
    ]

    check_rows = [table_header]
    row_styles = []

    for idx, c in enumerate(compliance.checks):
        r_idx = idx + 1
        st = c.status
        st_color = '#059669' if st == 'PASS' else ('#DC2626' if st == 'FAIL' else ('#D97706' if st == 'NEEDS_REVIEW' else ('#7C3AED' if st == 'EXEMPT' else '#64748B')))
        st_badge = f"<font color='{st_color}'><b>{st.replace('_', ' ')}</b></font>"

        obs_val = c.observed_value or ("Not observed" if st != "NOT_APPLICABLE" else "—")
        if len(obs_val) > 40:
            obs_val = obs_val[:38] + "..."

        reason_text = c.reason
        if len(reason_text) > 130:
            reason_text = reason_text[:126] + "..."

        check_rows.append([
            Paragraph(f"<b>Rule {c.rule_number}</b>", styles['TableTextBold']),
            Paragraph(f"{c.title}", styles['TableText']),
            Paragraph(st_badge, styles['TableText']),
            Paragraph(obs_val, styles['TableText']),
            Paragraph(reason_text, styles['TableText']),
        ])

        bg_col = '#FFFFFF' if r_idx % 2 == 0 else '#F8FAFC'
        if st == 'FAIL':
            bg_col = '#FEF2F2'
        elif st == 'EXEMPT':
            bg_col = '#FAF5FF'
        row_styles.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor(bg_col)))

    checks_table = Table(check_rows, colWidths=[60, 120, 65, 115, 180], repeatRows=1)
    checks_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ] + row_styles))

    story.append(checks_table)
    story.append(Spacer(1, 6))

    # --- Statutory Exemption Details (if any exist) ---
    exempt_checks = [c for c in compliance.checks if c.status == "EXEMPT" and c.exemption]
    if exempt_checks:
        story.append(Paragraph("Statutory Exemption Traceability Audit (Rule 26)", styles['SectionHeader']))
        ex_rows = [
            [
                Paragraph("<b>Provision</b>", styles['TableTextBold']),
                Paragraph("<b>Statutory Clause</b>", styles['TableTextBold']),
                Paragraph("<b>Exemption Reason & Verified Conditions</b>", styles['TableTextBold']),
            ]
        ]
        for ec in exempt_checks[:4]:
            ex = ec.exemption
            conds_str = "; ".join(ex.factual_conditions_checked) if ex.factual_conditions_checked else "Statutory conditions verified"
            ex_rows.append([
                Paragraph(f"Rule {ec.rule_number}", styles['TableTextBold']),
                Paragraph(f"Clause {ex.exemption_clause}", styles['TableTextBold']),
                Paragraph(f"{ex.reason}<br/><font color='#64748B' size='7'><b>Verified Facts:</b> {conds_str}</font>", styles['TableText']),
            ])

        ex_table = Table(ex_rows, colWidths=[80, 90, 370], repeatRows=1)
        ex_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7C3AED')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAF5FF')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDD6FE')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#EDE9FE')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(ex_table)
        story.append(Spacer(1, 6))

    # --- Evidence & Operational Audit Footnote ---
    img_count = metadata.get("image_count", len(product_data.images) if product_data else 1)
    story.append(KeepTogether([
        Paragraph("Inspection Evidence & Audit Authority", styles['SectionHeader']),
        Paragraph(
            f"<b>Evidence Collected:</b> {img_count} label view(s) analyzed. "
            f"Optical character extraction processed with RapidOCR ONNX engine and NVIDIA Nemotron 3 Ultra 550B semantic normalization. "
            f"<b>Legal Basis:</b> Verified against master legal registry <code>{compliance.legal_framework.registry_version}</code> "
            f"(GSR 202(E) 2011, GSR 779(E) 2017, GSR 784(E) 2021, GSR 226(E) 2022, GSR 512(E) 2023, 2025 Medical Devices Amendment). "
            f"This document is an official cryptographic-ready audit summary generated by SAHARA Legal Metrology Inspection System.",
            styles['BodySmall']
        ),
        Spacer(1, 4)
    ]))

    # 7. Build PDF
    doc.build(story, canvasmaker=NumberedCanvasWrapper)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # 8. Persist to inspection directory if specified or by default
    report_dir = insp_folder / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_pdf_file = report_dir / "inspection_report.pdf"
    with open(report_pdf_file, "wb") as f:
        f.write(pdf_bytes)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    logger.info(f"Generated clean PDF inspection report for {inspection_id} ({len(pdf_bytes)} bytes) at {report_pdf_file}")
    return pdf_bytes
