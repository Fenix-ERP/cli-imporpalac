import base64

from odoo import models
from odoo.tools.misc import file_path


class ReportTicketCash(models.AbstractModel):
    _name = "report.sale_order_ticket.report_ticket_cash"
    _description = "Quotation Cash Ticket Report"

    def _get_logo(self):
        """Cargar logo fijo desde el módulo y convertir a base64"""
        path = file_path("sale_order_ticket/static/src/img/logo.png")
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return False

    def _get_report_values(self, docids, data=None):
        docs = self.env["sale.order"].browse(docids)
        return {
            "docs": docs,
            "logo_custom": self._get_logo(),  # aquí pasa el logo al QWeb
        }
