from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    line_pricelist_id = fields.Many2one(
        'product.pricelist',
        string="Lista de Precios por Línea"
    )

    @api.onchange('product_id', 'line_pricelist_id', 'order_id.pricelist_id', 'product_uom_qty')
    def _onchange_line_pricelist_id(self):
        for line in self:
            pricelist = line.line_pricelist_id or line.order_id.pricelist_id
            if line.product_id and pricelist:
                line.price_unit = pricelist._get_product_price(
                    line.product_id, line.product_uom_qty or 1.0, line.order_id.partner_id
                )

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        for order in self:
            for line in order.order_line:
                line.line_pricelist_id = order.pricelist_id
                line.price_unit = order.pricelist_id._get_product_price(
                    line.product_id, line.product_uom_qty or 1.0, order.partner_id
                )
