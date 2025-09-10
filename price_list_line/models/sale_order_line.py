from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    line_pricelist_id = fields.Many2one(
        "product.pricelist", string="Lista de Precios por Línea"
    )

    @api.onchange("product_id", "order_id.pricelist_id", "product_uom_qty")
    def _onchange_product_id_set_line_pricelist(self):
        for line in self:
            if line.product_id:
                if not line.line_pricelist_id:
                    line.line_pricelist_id = line.order_id.pricelist_id

                pricelist = line.line_pricelist_id or line.order_id.pricelist_id
                line.price_unit = pricelist._get_product_price(
                    line.product_id,
                    line.product_uom_qty or 1.0,
                    line.order_id.partner_id,
                )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange("pricelist_id")
    def _onchange_pricelist_id(self):
        for order in self:
            for line in order.order_line:
                line.line_pricelist_id = order.pricelist_id
                line.price_unit = order.pricelist_id._get_product_price(
                    line.product_id, line.product_uom_qty or 1.0, order.partner_id
                )
