# pylint: skip-file
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ElectronicVoucherUpdate(models.Model):
    _inherit = "account.evoucher"
    _description = "Electronic Voucher"

    product_type_selection = fields.Selection(
        selection=[
            ("service", "Servicio"),
            ("product", "Almacenable"),
            ("none", "Ninguno"),
        ],
        compute="_compute_product_type_selection",
        store=True,
        readonly=True,
    )

    @api.depends(
        "lines_ride.product_id", "lines_ride.product_id.type", "ident_supplier"
    )
    def _compute_product_type_selection(self):
        total_records = len(self)

        for i, record in enumerate(self, 1):
            try:
                if record.product_type_selection in ["product", "service"]:
                    continue

                if not record.lines_ride or record.document_type not in [
                    "factura",
                    "notasdecredito",
                ]:
                    record.product_type_selection = "none"
                    continue
                vendor_categories = []
                partner = self.env["res.partner"].search(
                    [("vat", "=", record.ident_supplier)], limit=1
                )
                if partner.category_id:
                    vendor_categories = partner.category_id.mapped("name")
                    _logger.info("📋 Categorías del partner: %s", vendor_categories)

                almacenable_tags = ["EXTERIOR", "LOCAL INVENTARIOS"]
                servicio_tags = ["LOCAL SERVICIOS", "LOCAL GASTOS"]

                has_almacenable_tag = any(
                    tag in vendor_categories for tag in almacenable_tags
                )
                has_servicio_tag = any(
                    tag in vendor_categories for tag in servicio_tags
                )

                if has_almacenable_tag and has_servicio_tag:
                    record.product_type_selection = "product"
                    continue
                elif has_almacenable_tag:
                    record.product_type_selection = "product"
                    continue
                elif has_servicio_tag:
                    record.product_type_selection = "service"
                    continue

                # SEGUNDO: Solo si el vendedor NO tiene etiquetas, consultar los productos
                service_found = False
                product_found = False

                for line in record.lines_ride:
                    if line.product_id and line.product_id.id:
                        if line.product_id.type == "service":
                            service_found = True
                        elif line.product_id.type == "product":
                            product_found = True

                if service_found and product_found:
                    record.product_type_selection = "product"
                elif service_found:
                    record.product_type_selection = "service"
                elif product_found:
                    record.product_type_selection = "product"
                else:
                    record.product_type_selection = "none"

            except Exception:
                record.product_type_selection = "none"

        _logger.info(
            "✅ Finalizado _compute_product_type_selection para %s registros",
            total_records,
        )
