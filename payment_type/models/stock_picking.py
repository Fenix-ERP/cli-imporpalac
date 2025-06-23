from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )

    paid = fields.Boolean(
        string="Pagado",
        default=False,
    )