import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path
from io import BytesIO


def export_to_excel(rows, filename):
    """Backwards-compatible: save rows (iterable) to an Excel file path."""
    df = pd.DataFrame(rows)
    df.to_excel(filename, index=False)
    return filename


def export_report_pdf(summary_text, filename):
    """Backwards-compatible: save summary text to PDF file path."""
    c = canvas.Canvas(str(filename), pagesize=A4)
    w, h = A4
    y = h - 50
    for line in summary_text.splitlines():
        c.drawString(40, y, line[:120])
        y -= 14
        if y < 60:
            c.showPage()
            y = h - 50
    c.save()
    return filename


def dataframe_to_excel_bytes(df: pd.DataFrame) -> BytesIO:
    """Return an in-memory Excel (.xlsx) file for a DataFrame."""
    buf = BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return buf


def dataframe_to_pdf_bytes(df: pd.DataFrame) -> BytesIO:
    """Return an in-memory PDF representing the DataFrame (simple table as text)."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 40
    header = " | ".join(df.columns.astype(str))
    c.setFont("Helvetica", 10)
    c.drawString(30, y, header)
    y -= 16
    for _, row in df.iterrows():
        line = " | ".join(str(row[col])[:60] for col in df.columns)
        c.drawString(30, y, line)
        y -= 14
        if y < 60:
            c.showPage()
            y = h - 40
    c.save()
    buf.seek(0)
    return buf