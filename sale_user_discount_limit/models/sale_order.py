from odoo import _, api, exceptions, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange("discount")
    def _check_discount_limit(self):
        user = self.env.user
        if user.limit_discount_enabled and self.discount > user.max_discount_percent:
            raise exceptions.UserError(
                _("No puedes aplicar un descuento mayor al %.2f%%.")
                % user.max_discount_percent
            )
