from odoo import fields, models


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
