from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    limit_discount_enabled = fields.Boolean(string="Limitar descuento máximo")
    max_discount_percent = fields.Float(string="Descuento máximo (%)", default=0.0)
    max_discount_fixed = fields.Float(string="Descuento máximo fijo", default=0.0)

    @api.onchange("limit_discount_enabled")
    def _onchange_limit_discount_enabled(self):
        if not self.limit_discount_enabled:
            self.max_discount_percent = 0.0
            self.max_discount_fixed = 0.0

    @api.onchange("max_discount_percent")
    def _onchange_max_discount_percent(self):
        if self.max_discount_percent < 0.0:
            self.max_discount_percent = 0.0
        if self.max_discount_percent > 0.0:
            self.max_discount_fixed = 0.0

    @api.onchange("max_discount_fixed")
    def _onchange_max_discount_fixed(self):
        if self.max_discount_fixed < 0.0:
            self.max_discount_fixed = 0.0
        if self.max_discount_fixed > 0.0:
            self.max_discount_percent = 0.0
