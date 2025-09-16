import base64
import io

import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
        "lines_ride.product_id", "lines_ride.product_id.type", "vendor_id.category_id"
    )
    def _compute_product_type_selection(self):
        for record in self:
            try:
                if not record.lines_ride or record.document_type not in [
                    "factura",
                    "notasdecredito",
                ]:
                    record.product_type_selection = "none"
                    continue

                vendor_categories = []
                if record.vendor_id and record.vendor_id.category_id:
                    vendor_categories = record.vendor_id.category_id.mapped("name")
                almacenable_tags = ["EXTERIOR", "LOCAL INVENTARIO"]
                servicio_tags = ["LOCAL SERVICIOS", "LOCAL GASTOS"]

                has_almacenable_tag = any(
                    tag in vendor_categories for tag in almacenable_tags
                )
                has_servicio_tag = any(
                    tag in vendor_categories for tag in servicio_tags
                )

                if has_almacenable_tag and has_servicio_tag:
                    vendor_forced_type = "product"
                elif has_almacenable_tag:
                    vendor_forced_type = "product"
                elif has_servicio_tag:
                    vendor_forced_type = "service"
                else:
                    vendor_forced_type = None

                service_found = False
                product_found = False

                for line in record.lines_ride:
                    if line.product_id and line.product_id.id:
                        if line.product_id.type == "service":
                            service_found = True
                        elif line.product_id.type == "product":
                            product_found = True

                if vendor_forced_type:
                    record.product_type_selection = vendor_forced_type
                elif service_found and product_found:
                    record.product_type_selection = "service"
                elif service_found:
                    record.product_type_selection = "service"
                elif product_found:
                    record.product_type_selection = "product"
                else:
                    record.product_type_selection = "none"

            except Exception:
                record.product_type_selection = "none"

    def update_costs_action(self):
        """Update costs in the linked purchase order after validations"""
        self.ensure_one()

        if not self.purchase_order_id:
            raise UserError(_("This e-voucher is not linked to any purchase order."))

        if self.vendor_id != self.purchase_order_id.partner_id:
            raise UserError(
                _(
                    "The vendor %(vendor_name)s doesn't match the purchase order's vendor %(po_vendor_name)s."
                )
                % {
                    "vendor_name": self.vendor_id.name,
                    "po_vendor_name": self.purchase_order_id.partner_id.name,
                }
            )

        if self.purchase_order_id.picking_ids.filtered(lambda p: p.state == "done"):
            raise UserError(
                _("You have already validated the receipt of a purchase order.")
            )

        non_homologated_products = []
        for line in self.lines_ride:
            if not line.product_id:
                product_name = line.description or line.code or "Unknown product"
                non_homologated_products.append(product_name)

        if non_homologated_products:
            products_list = "\n- ".join(non_homologated_products)
            raise UserError(
                _(
                    "The following products are not approved in the system:\n- %s\n"
                    "Please homologate products before updating costs."
                )
                % products_list
            )

        updated_lines = 0
        for ride_line in self.lines_ride:
            if ride_line.product_id:
                po_line = self.purchase_order_id.order_line.filtered(
                    lambda line: line.product_id == ride_line.product_id
                )
                if po_line:
                    po_line.write(
                        {
                            "price_unit": ride_line.price_unit,
                            "discount": ride_line.discount,
                            "product_qty": ride_line.quantity,
                        }
                    )
                    updated_lines += 1

        if not updated_lines:
            raise UserError(
                _("No matching products found in the purchase order to update.")
            )

        return {
            "effect": {
                "fadeout": "slow",
                "message": _("Costs updated successfully!"),
                "type": "rainbow_man",
            }
        }

    def action_export_template(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        header_format = workbook.add_format(
            {
                "bold": True,
                "text_wrap": True,
                "valign": "vcenter",
                "align": "center",
                "border": 1,
                "bg_color": "#D9E1F2",
            }
        )
        example_format = workbook.add_format(
            {"font_color": "#0070C0", "valign": "vcenter", "align": "left", "border": 1}
        )

        headers = [
            "Codigo",
            "Descripcion",
            "Cantidad",
            "Precio Unitario",
            "Categoria",
            "Descuento",
            "Impuestos",
            "Total",
        ]

        sheet = workbook.add_worksheet("Plantilla Contacto")
        sheet.set_column(0, len(headers) - 1, 25)
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        column = 0
        row = 1
        for line in self.lines_ride:
            sheet.write(row, column, line.code, example_format)
            sheet.write(row, column + 1, line.description, example_format)
            sheet.write(row, column + 2, line.quantity, example_format)
            sheet.write(row, column + 3, line.price_unit, example_format)
            sheet.write(row, column + 4, line.categ_id.name, example_format)
            sheet.write(row, column + 5, line.discount, example_format)
            sheet.write(row, column + 6, line.vat.display_name, example_format)
            sheet.write(row, column + 7, line.price_total, example_format)
            row += 1

        workbook.close()
        file_data = base64.b64encode(output.getvalue())
        output.close()

        attachment = self.env["ir.attachment"].create(
            {
                "name": "contact_template.xlsx",
                "type": "binary",
                "datas": file_data,
                "res_model": "account.evoucher",
                "res_id": self.id,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
