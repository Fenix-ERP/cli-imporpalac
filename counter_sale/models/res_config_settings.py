# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class Company(models.Model):
    _inherit = "res.company"

    product_pricelist_ids_default = fields.One2many(
        "product.pricelist",
        "company_id",
        string="Default Price Lists",
        readonly=False,
    )


class AccountConfig(models.TransientModel):
    _inherit = "res.config.settings"

    product_pricelist_ids_default = fields.One2many(
        "product.pricelist",
        string="Default Price Lists",
        related="company_id.product_pricelist_ids_default",
        readonly=False,
    )

    @api.model
    def set_values(self):
        res = super(AccountConfig, self).set_values()
        company = self.env.user.company_id
        company.product_pricelist_ids_default = self.product_pricelist_ids_default
        return res

    @api.model
    def get_values(self):
        res = super(AccountConfig, self).get_values()
        company = self.env.user.company_id
        res.update(
            {
                "product_pricelist_ids_default": company.product_pricelist_ids_default,
            }
        )
        return res
