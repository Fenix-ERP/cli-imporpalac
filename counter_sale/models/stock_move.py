from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
    internal_location_id = fields.Many2one(
        "stock.location",
        string="Internal Location",
        related="sale_line_id.internal_location_id",
        readonly=True,
    )

    @api.constrains("quantity", "product_uom_qty")
    def _check_overdelivery_quantity(self):
        for move in self:
            if not move.picking_id:
                continue

            if move.quantity > move.product_uom_qty:
                raise ValidationError(
                    _(
                        "You cannot enter a quantity greater than the "
                        "requested amount for product %(product)s. "
                        "Requested: %(requested)s, Entered: %(entered)s"
                    )
                    % {
                        "product": move.product_id.display_name,
                        "requested": move.product_uom_qty,
                        "entered": move.quantity,
                    }
                )
