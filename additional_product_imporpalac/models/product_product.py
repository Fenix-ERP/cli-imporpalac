from datetime import datetime

from odoo import api, models


class ProductProduct(models.Model):
    """This class extends the 'product.product' model to enhance its functionality."""

    _inherit = "product.product"

    @api.depends("product_tmpl_id.write_date")
    def _compute_write_date(self):
        for record in self:
            record_write_date = record.write_date or self.env.cr.now()
            tmpl_write_date = record.product_tmpl_id.write_date or datetime.min
            record.write_date = max(record_write_date, tmpl_write_date)
