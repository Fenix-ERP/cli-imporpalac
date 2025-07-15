from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        self.ensure_one()
        res = super(SaleOrder, self).action_confirm()
        related_pickings = self.picking_ids
        for picking in related_pickings:
            picking.state = "waiting"
        return res
