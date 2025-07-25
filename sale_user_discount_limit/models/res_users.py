from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    limit_discount_enabled = fields.Boolean(string="Limitar descuento máximo")
    max_discount_percent = fields.Float(string="Descuento máximo (%)", default=0.0)
