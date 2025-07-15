from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    payment_state = fields.Selection(
        [
            ("not_paid", "Not Paid"),
            ("paid", "Paid"),
            ("credit", "Credit"),
        ],
        string="Payment Status",
        default="not_paid",
    )
