from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_cancel(self):
        res = super().button_cancel()
        for picking in self.picking_ids:
            picking.action_cancel()

        return res
