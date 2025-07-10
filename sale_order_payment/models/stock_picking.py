from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    paid = fields.Boolean(
        default=False,
    )
