from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"
    rectified_product_uom_qty = fields.Float(
        "Old Demand",
        digits="Product Unit of Measure",
        default=0,
        readonly=True,
    )
    rectified_quantity = fields.Float(
        "Old Quantity",
        digits="Product Unit of Measure",
        default=0,
        readonly=True,
    )
