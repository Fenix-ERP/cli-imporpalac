from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        self.ensure_one()
        res = super(PurchaseOrder, self).button_confirm()
        related_pickings = self.picking_ids
        related_pickings.move_ids.sudo().write({"state": "waiting"})
        return res
