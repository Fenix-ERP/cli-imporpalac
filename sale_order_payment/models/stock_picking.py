from odoo import fields, models, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    paid = fields.Boolean(
        string="Paid",
        default=False,
    )
