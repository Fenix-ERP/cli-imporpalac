from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )

    def _create_delivery(self):
        res = super()._create_delivery()
        for order in self:
            pickings = order.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])
            for picking in pickings:
                picking.payment_method = order.payment_method
        return res