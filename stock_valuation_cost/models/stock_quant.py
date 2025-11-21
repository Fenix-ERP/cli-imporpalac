from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _validate_import_data(self, vals):
        for quant in vals:
            product = self.env["product.product"].browse(vals.get("product_id"))
            cost = product.standard_price or 0.0
            if cost <= 0:
                raise UserError(
                    _(
                        "The stock valuation cost for product %s cannot be zero or negative."
                    )
                    % (product.display_name)
                )
            return True

    @api.model_create_multi
    def create(self, vals_list):
        if self._validate_import_data(vals_list[0]):
            quants = super().create(vals_list)
        else:
            raise ValidationError(_("Stock valuation cost cannot be zero or negative."))
        return quants

    def action_apply_inventory(self):
        for quant in self:
            if quant._validate_import_data({"product_id": quant.product_id.id}):
                return super().action_apply_inventory()
            else:
                raise ValidationError(
                    _("Stock valuation cost cannot be zero or negative.")
                )
