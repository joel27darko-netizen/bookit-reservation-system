"""
Report generation: streams CSV for tabular exports and renders PDFs
(via ReportLab) for polished summary documents. Handles three report
kinds: bookings summary, occupancy report, revenue report.
"""
import csv
import io
from datetime import datetime
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from sqlalchemy.orm import Session

from app.repositories.booking_repo import BookingRepository, ACTIVE_STATUSES
from app.repositories.resource_repo import ResourceRepository


class ReportService:
    def __init__(self, db: Session):
        self.booking_repo = BookingRepository(db)
        self.resource_repo = ResourceRepository(db)

    # ---------- Data gathering ----------

    def _bookings_rows(self, date_from: Optional[datetime], date_to: Optional[datetime]) -> List[dict]:
        bookings = self.booking_repo.list_by_filters(date_from=date_from, date_to=date_to)
        rows = []
        for b in bookings:
            rows.append({
                "reference": b.reference,
                "resource": b.resource.name,
                "customer": b.customer.full_name,
                "start_time": b.start_time.strftime("%Y-%m-%d %H:%M"),
                "end_time": b.end_time.strftime("%Y-%m-%d %H:%M"),
                "status": b.status.value,
                "party_size": b.party_size,
                "total_price": b.total_price,
            })
        return rows

    def _occupancy_rows(self, date_from: Optional[datetime], date_to: Optional[datetime]) -> List[dict]:
        resources = self.resource_repo.list_all(only_active=False)
        rows = []
        for r in resources:
            bookings = self.booking_repo.list_by_filters(resource_id=r.id, date_from=date_from, date_to=date_to)
            active = [b for b in bookings if b.status in ACTIVE_STATUSES]
            booked_hours = sum((b.end_time - b.start_time).total_seconds() / 3600 for b in active)
            rows.append({
                "resource": r.name,
                "type": r.type.value,
                "total_bookings": len(active),
                "booked_hours": round(booked_hours, 2),
            })
        return rows

    def _revenue_rows(self, date_from: Optional[datetime], date_to: Optional[datetime]) -> List[dict]:
        resources = self.resource_repo.list_all(only_active=False)
        rows = []
        for r in resources:
            bookings = self.booking_repo.list_by_filters(resource_id=r.id, date_from=date_from, date_to=date_to)
            active = [b for b in bookings if b.status in ACTIVE_STATUSES]
            revenue = sum(b.total_price for b in active)
            rows.append({"resource": r.name, "bookings": len(active), "revenue": round(revenue, 2)})
        return rows

    def get_rows(self, report_type: str, date_from=None, date_to=None) -> List[dict]:
        if report_type == "bookings":
            return self._bookings_rows(date_from, date_to)
        elif report_type == "occupancy":
            return self._occupancy_rows(date_from, date_to)
        elif report_type == "revenue":
            return self._revenue_rows(date_from, date_to)
        raise ValueError(f"Unknown report type: {report_type}")

    # ---------- CSV ----------

    def to_csv(self, report_type: str, date_from=None, date_to=None) -> io.StringIO:
        rows = self.get_rows(report_type, date_from, date_to)
        buffer = io.StringIO()
        if rows:
            writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            buffer.write("No data available for the selected range\n")
        buffer.seek(0)
        return buffer

    # ---------- PDF ----------

    def to_pdf(self, report_type: str, date_from=None, date_to=None) -> io.BytesIO:
        rows = self.get_rows(report_type, date_from, date_to)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        title_map = {
            "bookings": "Bookings Summary Report",
            "occupancy": "Occupancy Report",
            "revenue": "Revenue Report",
        }
        elements.append(Paragraph(title_map.get(report_type, "Report"), styles["Title"]))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        elements.append(Spacer(1, 16))

        if rows:
            headers = list(rows[0].keys())
            data = [[h.replace("_", " ").title() for h in headers]]
            for row in rows:
                data.append([str(row[h]) for h in headers])

            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("No data available for the selected range.", styles["Normal"]))

        doc.build(elements)
        buffer.seek(0)
        return buffer
