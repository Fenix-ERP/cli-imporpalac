from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    line_pricelist_id = fields.Many2one(
        "product.pricelist", string="Lista de precios por línea"
    )

    @api.onchange("product_id")
    def _onchange_product_id_set_pricelist(self):
        for line in self:
            if not line.line_pricelist_id and line.order_id:
                line.line_pricelist_id = line.order_id.pricelist_id

    @api.onchange(
        "product_id", "line_pricelist_id", "order_id.pricelist_id", "product_uom_qty"
    )
    def _onchange_line_pricelist_id(self):
        for line in self:
            if line.product_id.type != "product":
                continue
            pricelist = line.line_pricelist_id or line.order_id.pricelist_id
            if line.product_id and pricelist:
                self.env.cr.execute(
                    """
                    SELECT applied_on
                    FROM product_pricelist_item
                    WHERE pricelist_id = %s
                    AND (
                        applied_on = '3_global'
                        OR applied_on = '2_product_category' AND categ_id = %s
                        OR applied_on = '1_product' AND product_tmpl_id = %s
                        OR applied_on = '0_product_variant' AND product_id = %s
                    )
                    LIMIT 1
                """,
                    (
                        pricelist.id,
                        line.product_id.categ_id.id,
                        line.product_id.product_tmpl_id.id,
                        line.product_id.id,
                    ),
                )
                exists_rule = self.env.cr.fetchone()

                if exists_rule:
                    price = pricelist._get_product_price(
                        line.product_id, line.product_uom_qty or 1.0
                    )
                    line.price_unit = price
                else:
                    raise UserError(
                        _(
                            "El producto %(product)s no tiene precio en la lista %(pricelist)s."
                        )
                        % {
                            "product": line.product_id.display_name,
                            "pricelist": pricelist.display_name,
                        }
                    )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange("pricelist_id")
    def _onchange_pricelist_id(self):
        for order in self:
            no_price_products = []
            for line in order.order_line:
                line.line_pricelist_id = order.pricelist_id

                if line.product_id and order.pricelist_id:
                    self.env.cr.execute(
                        """
                        SELECT applied_on
                        FROM product_pricelist_item
                        WHERE pricelist_id = %s
                        AND (
                            applied_on = '3_global'
                            OR applied_on = '2_product_category' AND categ_id = %s
                            OR applied_on = '1_product' AND product_tmpl_id = %s
                            OR applied_on = '0_product_variant' AND product_id = %s
                        )
                        LIMIT 1
                    """,
                        (
                            order.pricelist_id.id,
                            line.product_id.categ_id.id,
                            line.product_id.product_tmpl_id.id,
                            line.product_id.id,
                        ),
                    )
                    exists_rule = self.env.cr.fetchone()
                    if exists_rule:
                        line.price_unit = order.pricelist_id._get_product_price(
                            line.product_id, line.product_uom_qty or 1.0
                        )
                    else:
                        no_price_products.append(line.product_id.display_name)

            if no_price_products:
                raise UserError(
                    _(
                        "Los siguientes productos no tienen precio definido en la lista %(pricelist)s:\n%(products)s"
                    )
                    % {
                        "pricelist": order.pricelist_id.display_name,
                        "products": ", ".join(no_price_products),
                    }
                )
