# Copyright (C) Softhealer Technologies.
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    barcodes = fields.Json(compute="_compute_barcodes", store=True, readonly=True)

    @api.depends(
        "default_code",
        "product_variant_ids.default_code",
        "barcode",
        "product_variant_ids.barcode",
    )
    def _compute_barcodes(self):
        for template in self:
            barcodes = []
            for product in template.product_variant_ids:
                if product.barcode:
                    barcodes.append(product.barcode)

                barcodes.append(product.default_code)
            template.barcodes = barcodes
