from odoo import api, fields, models
from odoo.tools.misc import get_lang


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pricelist_line_id = fields.Many2one(
        "product.pricelist",
        string="Pricelist Line",
        related="order_id.pricelist_id",
        readonly=True,
    )
    pricelist_line2_id = fields.Many2one(
        "product.pricelist",
        string="Pricelist Line",
    )

    """ Initial value to field taking the value of the reference field. """

    @api.onchange("pricelist_line_id")
    def _onchange_pricelist_line_id(self):
        for record in self:
            if not record.pricelist_line2_id:
                record.pricelist_line2_id = record.pricelist_line_id

    @api.onchange("pricelist_line2_id", "product_id")
    def _onchange_pricelist_line2_id(self):
        if not self.product_id or not self.pricelist_line2_id:
            return

        pricelist = self.pricelist_line2_id
        product = self.product_id
        partner = self.order_id.partner_id

        price = pricelist.with_context(
            partner_id=partner.id,
            quantity=self.product_uom_qty,
            uom=self.product_uom.id,
            date=self.order_id.date_order,
        )._get_product_price(product, self.product_uom_qty, partner)

        self.price_unit = price


    @api.onchange("product_uom", "product_uom_qty")
    def _compute_price_unit(self):
        values = super()._compute_price_unit()
        self._onchange_pricelist_line2_id()
        return values


class SaleOrder(models.Model):
    _inherit = "sale.order"

    """ when the main price list is changed each order line
    also takes the same value when updating prices is clicked. """

    def update_prices(self):
        for record in self:
            for line in record.order_line:
                line.pricelist_line2_id = record.pricelist_id
        values = super().update_prices()
        return values