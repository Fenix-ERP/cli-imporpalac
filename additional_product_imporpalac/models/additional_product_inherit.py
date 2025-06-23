from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    articulo = fields.Char(string="Articulo")
    marca = fields.Char(string="Marca")
    modelo = fields.Char(string="Modelo")
    anio = fields.Char(string="Año")
    lado = fields.Char(string="Lado")

    procedencia = fields.Char(string="Procedencia")
    adicional_1 = fields.Char(string="Adicional 1")
    adicional_2 = fields.Char(string="Adicional 2")
    adicional_3 = fields.Char(string="Adicional 3")
    adicional_4 = fields.Char(string="Adicional 4")
    adicional_5 = fields.Char(string="Adicional 5")
    adicional_6 = fields.Char(string="Adicional 6")
