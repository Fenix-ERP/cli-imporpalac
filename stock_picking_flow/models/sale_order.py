from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        self.ensure_one()
        res = super(SaleOrder, self).action_confirm()
        related_pickings = self.picking_ids
        related_pickings.move_ids.sudo().write({"state": "waiting"})
        return res
