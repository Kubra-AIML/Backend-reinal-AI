from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..schemas.report import ReportData


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def render_pdf(report: ReportData) -> bytes:
    """Renders the PDF from the report object only. No other data source is used."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"RetinaGuide XAI report {report.case_ref}",
        author="RetinaGuide XAI",
    )
    ss = getSampleStyleSheet()
    body = ss["BodyText"]
    bold = ParagraphStyle("bold", parent=body, fontName="Helvetica-Bold")
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10)
    h1, h2 = ss["Title"], ss["Heading2"]

    def p(text, style=body):
        return Paragraph(escape(str(text)), style)

    def kv(rows):
        data = [[p(k, bold), p(v)] for k, v in rows]
        t = Table(data, colWidths=[48 * mm, 122 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f2f2")),
                ]
            )
        )
        return t

    r = report.result
    story = [p("RetinaGuide XAI: Screening Support Report", h1)]

    if r.engine in ("stub", "cache") and r.notice:
        banner = Table([[p(f"ENGINE: {r.engine.upper()}. {r.notice}", bold)]], colWidths=[170 * mm])
        banner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fde8e8")),
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#b00020")),
                ]
            )
        )
        story += [banner, Spacer(1, 4 * mm)]

    story += [
        p("Case", h2),
        kv(
            [
                ("Case reference", report.case_ref),
                ("Case created", _fmt_dt(report.created_at)),
                ("Image SHA-256", report.image_sha256),
                ("Result engine", r.engine),
                ("Report generated", _fmt_dt(report.generated_at)),
            ]
        ),
        p("Model and preprocessing versions", h2),
        kv(
            [
                ("Classifier", r.versions.classifier),
                ("Quality gate", r.versions.quality_gate),
                ("Preprocessing spec", r.versions.preprocess_spec),
            ]
        ),
        p("Image quality verdict", h2),
        kv(
            [
                ("Verdict", r.quality.verdict),
                ("Reasons", ", ".join(r.quality.reason_codes) or "none"),
                ("Measured metrics", ", ".join(f"{k}={v}" for k, v in r.quality.metrics.items()) or "none supplied"),
            ]
        ),
        p("Model output", h2),
    ]

    if r.prediction is None:
        story.append(p(f"No grade was produced because the quality verdict is '{r.quality.verdict}'."))
    else:
        pr = r.prediction
        story.append(
            kv(
                [
                    ("Predicted category", f"Grade {pr.grade} (model output, not a diagnosis)"),
                    (
                        "Referable (model output)",
                        f"{'Yes' if pr.referable else 'No'} (p_referable {pr.p_referable:.3f}, "
                        f"threshold {report.referable_threshold})",
                    ),
                    ("Confidence", "not supplied" if pr.confidence is None else f"{pr.confidence:.3f}"),
                    ("Calibration status", pr.calibration_status),
                    ("Class scores (grades 0 to 4)", ", ".join(f"{s:.3f}" for s in pr.class_scores)),
                ]
            )
        )
    story += [
        Spacer(1, 2 * mm),
        p(f"Uncertainty caveat: {report.confidence_policy}", small),
        Spacer(1, 2 * mm),
        p(f"Recommended action: {r.recommended_action}"),
        p("Review flags: " + (", ".join(r.review_flags) or "none")),
        p("Images", h2),
    ]

    if report.input_image_available:
        story.append(p(f"Submitted image: listed as '{r.artifacts.input_image}' (not embedded in this version of the report)."))
    else:
        story.append(p("Submitted image: not available (this backend does not store image bytes)."))
    if report.heatmap.available:
        story.append(p(f"Heatmap: listed as '{report.heatmap.filename}' (not embedded in this version of the report)."))
    else:
        story.append(p("Heatmap: not available."))
    story.append(p(report.heatmap.label, small))

    story.append(p("Reviewer records", h2))
    if report.reviews:
        story.append(p("Reviews are separate records. The original model result above is unchanged.", small))
        for rv in report.reviews:
            grade = "" if rv.corrected_grade is None else f", corrected grade {rv.corrected_grade}"
            note = f" Notes: {rv.notes}" if rv.notes else ""
            story.append(p(f"{_fmt_dt(rv.created_at)}: {rv.reviewer} chose '{rv.decision}'{grade}.{note}"))
    else:
        story.append(p("No reviews have been added."))

    story += [
        p("Benchmark and limitations", h2),
        p(report.benchmark_caveat, small),
        p(report.limitations_text, small),
        p(report.clinician_statement, bold),
        p("Clinician decision", h2),
    ]
    decision_rows = [[p(f, bold), ""] for f in report.clinician_decision_fields]
    decision = Table(decision_rows, colWidths=[48 * mm, 122 * mm], rowHeights=[12 * mm] * len(decision_rows))
    decision.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(decision)

    doc.build(story)
    return buf.getvalue()