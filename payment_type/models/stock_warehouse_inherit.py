from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    journal_id = fields.Many2one("account.journal", string="Diario Contable")