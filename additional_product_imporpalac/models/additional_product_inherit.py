from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    articulo = fields.Char()
    marca = fields.Char()
    modelo = fields.Char()
    anio = fields.Char(string="Año")
    lado = fields.Char()

    procedencia = fields.Char()
    adicional_1 = fields.Char()
    adicional_2 = fields.Char()
    adicional_3 = fields.Char()
    adicional_4 = fields.Char()
    adicional_5 = fields.Char()
    adicional_6 = fields.Char()

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
