from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ["done", "cancel"]
            )
            for picking in pickings:
                picking.payment_method = order.payment_method
        return res
