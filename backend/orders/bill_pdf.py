"""Builds the premium bill PDF from the saved order, so old bills never change."""
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GREEN = colors.HexColor("#3DA535")
GREEN_DARK = colors.HexColor("#2E8B2A")
GREEN_SOFT = colors.HexColor("#E8F5E6")
NAVY = colors.HexColor("#2B2F77")
INK = colors.HexColor("#1B1F3B")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#E5E7EB")
ZEBRA = colors.HexColor("#F7F9F7")

SHOP_NAME = "Vetri Technology Solutions"
SHOP_TAGLINE = "Fresh stock, safe dates"
ASSETS = settings.BASE_DIR / "assets"
LOGO_PATH = ASSETS / "logo.png"

# DejaVu has the rupee sign; the built-in PDF fonts do not.
pdfmetrics.registerFont(TTFont("Body", str(ASSETS / "fonts" / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("Body-Bold", str(ASSETS / "fonts" / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body", boldItalic="Body-Bold")

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def _rs(value):
    return f"₹{Decimal(value):,.2f}"


def _qr(text, size):
    widget = QrCodeWidget(text)
    x0, y0, x1, y1 = widget.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(widget)
    return d


def _decorate(bill):
    """Page furniture: navy header band with logo and the footer line."""

    def on_page(canvas, doc):
        canvas.saveState()
        band_h = 34 * mm
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - band_h, PAGE_W, band_h, stroke=0, fill=1)
        canvas.setFillColor(GREEN)
        canvas.rect(0, PAGE_H - band_h - 2.2 * mm, PAGE_W, 2.2 * mm, stroke=0, fill=1)

        x = MARGIN
        if LOGO_PATH.exists():
            canvas.setFillColor(colors.white)
            canvas.circle(x + 11 * mm, PAGE_H - band_h / 2, 12 * mm, stroke=0, fill=1)
            canvas.drawImage(str(LOGO_PATH), x + 1 * mm, PAGE_H - band_h / 2 - 10 * mm, 20 * mm, 20 * mm,
                             preserveAspectRatio=True, mask="auto")
            x += 28 * mm
        canvas.setFillColor(colors.white)
        canvas.setFont("Body-Bold", 20)
        canvas.drawString(x, PAGE_H - 15 * mm, "Vetri Bills")
        canvas.setFont("Body", 8.5)
        canvas.setFillColor(colors.HexColor("#C9CCF0"))
        canvas.drawString(x, PAGE_H - 21 * mm, SHOP_NAME)
        canvas.drawString(x, PAGE_H - 25.5 * mm, SHOP_TAGLINE)

        canvas.setFillColor(colors.white)
        canvas.setFont("Body-Bold", 15)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 15 * mm, "TAX INVOICE")
        canvas.setFont("Body", 8.5)
        canvas.setFillColor(colors.HexColor("#C9CCF0"))
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 21 * mm, bill.bill_no)

        # footer
        canvas.setStrokeColor(LINE)
        canvas.line(MARGIN, 14 * mm, PAGE_W - MARGIN, 14 * mm)
        canvas.setFont("Body", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 9.5 * mm, f"{SHOP_NAME}  ·  This is a computer generated invoice and needs no signature.")
        canvas.drawRightString(PAGE_W - MARGIN, 9.5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return on_page


def build_bill_pdf(bill):
    order = bill.order
    user = order.user
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=46 * mm, bottomMargin=20 * mm,
        title=f"Invoice {bill.bill_no}", author=SHOP_NAME,
    )

    st = lambda name, **kw: ParagraphStyle(name, fontName=kw.pop("fontName", "Body"), **kw)  # noqa: E731
    label = st("label", fontSize=7.5, leading=10, textColor=MUTED, fontName="Body-Bold")
    text = st("text", fontSize=9, leading=12.5, textColor=INK)
    bold = st("bold", fontSize=10.5, leading=14, textColor=INK, fontName="Body-Bold")
    cell = st("cell", fontSize=9, leading=11.5, textColor=INK)
    cell_r = st("cell_r", parent=None, fontSize=9, leading=11.5, textColor=INK, alignment=2)
    head = st("head", fontSize=8, leading=10, textColor=colors.white, fontName="Body-Bold")
    head_r = st("head_r", fontSize=8, leading=10, textColor=colors.white, fontName="Body-Bold", alignment=2)
    note = st("note", fontSize=8, leading=11.5, textColor=MUTED)

    # --- Billed to / Invoice details cards
    name = user.get_full_name() or user.username
    bill_lines = [Paragraph("BILLED TO", label), Paragraph(name, bold), Paragraph(user.email, text)]
    if user.phone:
        bill_lines.append(Paragraph(user.phone, text))
    if order.shipping_address:
        bill_lines.append(Paragraph(order.shipping_address.replace("\n", "<br/>"), text))

    payment = order.payments.filter(status="paid").first()
    when = timezone.localtime(order.created_at)
    detail_rows = [
        [Paragraph("INVOICE NO", label), Paragraph(bill.bill_no, text)],
        [Paragraph("DATE", label), Paragraph(f"{when:%d %b %Y, %I:%M %p}", text)],
        [Paragraph("ORDER", label), Paragraph(f"#{order.pk}", text)],
        [Paragraph("PAYMENT", label), Paragraph("Razorpay (test mode)" if payment and "mock" in str(payment.provider_payment_id) else "Razorpay", text)],
    ]
    if payment and payment.provider_payment_id:
        detail_rows.append([Paragraph("REFERENCE", label), Paragraph(str(payment.provider_payment_id), text)])
    details = Table(detail_rows, colWidths=[24 * mm, 50 * mm])
    details.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))

    cards = Table([[bill_lines, details]], colWidths=[CONTENT_W / 2 - 2 * mm, CONTENT_W / 2 + 2 * mm])
    cards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), ZEBRA), ("BACKGROUND", (1, 0), (1, 0), ZEBRA),
        ("BOX", (0, 0), (0, 0), 0.6, LINE), ("BOX", (1, 0), (1, 0), 0.6, LINE),
        ("LINEBEFORE", (0, 0), (0, 0), 3, GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    # a thin gap between the two cards
    cards._argW = [CONTENT_W / 2 - 3 * mm, CONTENT_W / 2 + 3 * mm]

    # --- Items
    rows = [[Paragraph("#", head), Paragraph("ITEM", head), Paragraph("QTY", head_r), Paragraph("RATE", head_r),
             Paragraph("TAX", head_r), Paragraph("AMOUNT", head_r)]]
    for n, item in enumerate(order.items.all(), start=1):
        rows.append([
            Paragraph(str(n), cell), Paragraph(f"<b>{item.product_name}</b>", cell), Paragraph(str(item.quantity), cell_r),
            Paragraph(_rs(item.unit_price), cell_r), Paragraph(f"{item.tax_percent.normalize():f}%", cell_r),
            Paragraph(f"<b>{_rs(item.line_total)}</b>", cell_r),
        ])
    items = Table(rows, colWidths=[9 * mm, 66 * mm, 15 * mm, 29 * mm, 15 * mm, 40 * mm], repeatRows=1)
    items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE), ("LINEBELOW", (0, -1), (-1, -1), 1, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    # --- Totals: Subtotal + tax (split CGST/SGST) = Total
    half = (order.tax_total / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    other_half = order.tax_total - half
    tot_rows = [
        ["Subtotal (before tax)", _rs(order.subtotal)],
        ["CGST", _rs(half)],
        ["SGST", _rs(other_half)],
    ]
    totals = Table(tot_rows, colWidths=[46 * mm, 34 * mm])
    totals.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Body"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (-1, -1), MUTED),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    grand = Table([["TOTAL PAID", _rs(order.total)]], colWidths=[40 * mm, 40 * mm])
    grand.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN), ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Body-Bold"), ("FONTSIZE", (0, 0), (0, 0), 9), ("FONTSIZE", (1, 0), (1, 0), 13),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    right_block = Table([[totals], [grand]], colWidths=[80 * mm])
    right_block.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                     ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))

    # --- PAID badge + QR on the left of the totals
    badge = Table([["PAID"]], colWidths=[28 * mm], rowHeights=[10 * mm])
    badge.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.4, GREEN_DARK), ("TEXTCOLOR", (0, 0), (-1, -1), GREEN_DARK),
        ("BACKGROUND", (0, 0), (-1, -1), GREEN_SOFT), ("FONTNAME", (0, 0), (-1, -1), "Body-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 13), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    qr_text = f"VETRI-BILLS|{bill.bill_no}|ORDER {order.pk}|TOTAL {order.total}"
    left_block = Table(
        [[badge], [Spacer(1, 3 * mm)], [_qr(qr_text, 24 * mm)], [Paragraph("Scan to verify this invoice", note)]],
        colWidths=[85 * mm], hAlign="LEFT",
    )
    left_block.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    summary = Table([[left_block, right_block]], colWidths=[CONTENT_W - 80 * mm, 80 * mm])
    summary.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))

    thanks = Table(
        [[Paragraph("<b>Thank you for shopping with Vetri Bills!</b>", st("t", fontSize=10, leading=14, textColor=NAVY, fontName="Body-Bold")),
          Paragraph("Tax is added to the subtotal. Please check each product's expiry date before use. Keep this invoice for returns.", note)]],
        colWidths=[CONTENT_W * 0.38, CONTENT_W * 0.62],
    )
    thanks.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN_SOFT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                                ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))

    story = [cards, Spacer(1, 7 * mm), items, Spacer(1, 6 * mm), KeepTogether([summary, Spacer(1, 8 * mm), thanks])]
    on_page = _decorate(bill)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()
