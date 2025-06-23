# quick_sale/models/sale_order.py

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm_quick(self):
        for order in self:
            if order.state not in ("sale", "done"):
                order.action_confirm()

            invoice = order._create_invoices()
            invoice.payment_method = order.payment_method
        return True
