from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_line_restriction = fields.Boolean(string="Restricción de líneas en ventas")
    sale_line_max_count = fields.Integer(string="Máximo número de líneas", config_parameter='sale_line_limit.max_lines')

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param('sale_line_limit.restriction', self.sale_line_restriction)

    def get_values(self):
        res = super().get_values()
        res.update({
            'sale_line_restriction': self.env['ir.config_parameter'].sudo().get_param('sale_line_limit.restriction') == 'True',
        })
        return res
