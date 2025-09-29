from odoo import _, api, exceptions, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange("order_line")
    def _check_max_sale_lines(self):
        restriction = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sale_line_limit.restriction")
        )
        max_lines = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sale_line_limit.max_lines")
            or 0
        )

        if restriction == "True" and len(self.order_line) > max_lines:
            raise exceptions.UserError(
                _("No puedes agregar más de %s líneas de venta a este pedido.")
                % max_lines
            )

    def action_confirm(self):
        if (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sale_line_limit.restriction")
            == "True"
        ):
            max_lines = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("sale_line_limit.max_lines")
                or 0
            )
            if len(self.order_line) > max_lines:
                raise exceptions.UserError(
                    _("No puedes agregar más de %s líneas de venta a este pedido.")
                    % max_lines
                )
        return super().action_confirm()
