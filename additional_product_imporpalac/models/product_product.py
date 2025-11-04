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


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends("product_variant_ids.barcode_supp")
    def _compute_barcodes(self):
        res = super()._compute_barcodes()
        for template in self:
            barcodes = []
            for product in template.product_variant_ids:
                if product.barcode_supp:
                    barcodes.append(product.barcode_supp)
            template.barcodes.extend(barcodes)
        return res
