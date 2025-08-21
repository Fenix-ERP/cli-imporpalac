from odoo import _, api, exceptions, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange("discount")
    def _check_discount_limit(self):
        user = self.env.user
        if (
            user.limit_discount_enabled
            and self.discount > user.max_discount_percent
            and user.max_discount_percent != 0
        ):
            raise exceptions.UserError(
                _("No puedes aplicar un descuento porcentaje mayor al %.2f%%.")
                % user.max_discount_percent
            )

    @api.onchange("discount_fixed")
    def _check_discount_limit_fixed(self):
        user = self.env.user
        if (
            user.limit_discount_enabled
            and self.discount_fixed > user.max_discount_fixed
            and user.max_discount_fixed != 0
        ):
            raise exceptions.UserError(
                _("No puedes aplicar un descuento fijo mayor al %.2f.")
                % user.max_discount_fixed
            )
