from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    detailed_type = fields.Selection(default="product")
