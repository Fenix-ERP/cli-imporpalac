from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_article = fields.Char()
    product_brand = fields.Char()
    product_model = fields.Char()
    product_year = fields.Char()
    product_side = fields.Char()

    product_origin = fields.Char()
    additional_1 = fields.Char()
    additional_2 = fields.Char()
    additional_3 = fields.Char()
    additional_4 = fields.Char()
    additional_5 = fields.Char()
    additional_6 = fields.Char()

    categ_id = fields.Many2one(
        "product.category",
        "Product Category",
        change_default=True,
        group_expand="_read_group_categ_id",
    )

    @api.constrains("type", "categ_id")
    def _check_storable_product_category(self):
        for record in self:
            if record.type == "product" and record.categ_id.name.lower() == "all":
                raise ValidationError(
                    _("You cannot create a storable product with category 'All'.")
                )
