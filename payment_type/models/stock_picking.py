from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )

    invoice_number = fields.Char()

    def action_cancel(self):
        res = super().action_cancel()
        order = self.sale_id
        order.state = "cancel"
        return res
