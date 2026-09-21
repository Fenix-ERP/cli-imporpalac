import base64
import io

import xlsxwriter

from odoo import _, fields, models
from odoo.exceptions import UserError


class FnxInventoryAdjustmentReportWizard(models.TransientModel):
    _name = "fnx.inventory.adjustment.report.wizard"
    _description = "FnxInventoryAdjustmentReportWizard"

    date_from = fields.Date(
        default=lambda self: fields.Date.context_today(self),
        required=True,
    )

    date_to = fields.Date(
        default=lambda self: fields.Date.context_today(self),
        required=True,
    )

    def _get_warehouse(self, location):
        return self.env["stock.warehouse"].search(
            [
                ("lot_stock_id", "parent_of", location.id),
                ("company_id", "=", location.company_id.id),
            ],
            limit=1,
        )

    def action_export_xlsx(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("The start date must be before the end date."))

        adjustments = self.env["fnx.inventory.adjustment"].search(
            [
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ],
            order="date, id",
        )
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Inventory Adjustments")
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
        text_format = workbook.add_format({"border": 1, "valign": "top"})
        number_format = workbook.add_format(
            {"border": 1, "num_format": "#,##0.00", "valign": "top"}
        )
        headers = [
            _("Date"),
            _("Time"),
            _("Product Code"),
            _("Description"),
            _("Quantity"),
            _("Cost"),
            _("Warehouse"),
            _("Operation Type"),
            _("Reason"),
            _("User"),
            _("Accounting Entry"),
            _("Terms and Conditions"),
        ]

        num_cols = len(headers)
        title_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 12,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
            }
        )
        label_format = workbook.add_format(
            {"bold": True, "border": 1, "valign": "vcenter"}
        )
        value_format = workbook.add_format({"border": 1, "valign": "vcenter"})
        signature_format = workbook.add_format({"bold": True, "valign": "bottom"})
        signature_line_format = workbook.add_format({"bottom": 1})

        # Row 0: merged title. Rows 2-3: report period. Row 5: table header.
        worksheet.set_row(0, 24)
        worksheet.merge_range(
            0, 0, 0, num_cols - 1, _("Inventory Adjustments"), title_format
        )
        worksheet.write(2, 0, _("Date From:"), label_format)
        worksheet.write(2, 1, fields.Date.to_string(self.date_from), value_format)
        worksheet.write(3, 0, _("Date To:"), label_format)
        worksheet.write(3, 1, fields.Date.to_string(self.date_to), value_format)

        header_row = 5
        for column, header in enumerate(headers):
            worksheet.write(header_row, column, header, header_format)

        operation_types = dict(
            self.env["fnx.inventory.adjustment"]
            ._fields["adjustment_type"]
            ._description_selection(self.env)
        )
        row = header_row + 1
        for adjustment in adjustments:
            warehouse = self._get_warehouse(adjustment.origin_location_id)
            time_value = ""
            if adjustment.create_date:
                time_value = fields.Datetime.context_timestamp(
                    self, adjustment.create_date
                ).strftime("%H:%M:%S")
            for line in adjustment.line_ids:
                account_entry = ", ".join(
                    line.mapped("account_move_ids").mapped("name")
                )
                values = [
                    fields.Date.to_string(adjustment.date),
                    time_value,
                    line.product_id.default_code or "",
                    line.product_id.name or "SN",
                    line.new_qty,
                    line.real_cost,
                    warehouse.name or "",
                    operation_types.get(adjustment.adjustment_type, ""),
                    adjustment.reason_id.name or "",
                    adjustment.user_id.name or "",
                    account_entry,
                    adjustment.terms_and_conditions or "",
                ]
                for column, value in enumerate(values):
                    format_ = number_format if column in (4, 5) else text_format
                    worksheet.write(row, column, value, format_)
                row += 1

        # Signature footer
        last_data_row = max(row - 1, header_row)
        signature_row = row + 2
        worksheet.write(signature_row, 0, _("Prepared By"), signature_format)
        worksheet.write(signature_row + 1, 0, "", signature_line_format)
        worksheet.merge_range(
            signature_row + 1, 1, signature_row + 1, 3, "", signature_line_format
        )
        worksheet.write(signature_row, 5, _("Reviewed By"), signature_format)
        worksheet.merge_range(
            signature_row + 1, 5, signature_row + 1, 7, "", signature_line_format
        )
        worksheet.write(signature_row, 9, _("Approved By"), signature_format)
        worksheet.merge_range(
            signature_row + 1, 9, signature_row + 1, 11, "", signature_line_format
        )

        worksheet.freeze_panes(header_row + 1, 0)
        worksheet.autofilter(header_row, 0, last_data_row, num_cols - 1)
        worksheet.set_column(0, 1, 14)
        worksheet.set_column(2, 2, 18)
        worksheet.set_column(3, 4, 14)
        worksheet.set_column(5, 9, 24)
        worksheet.set_column(10, 10, 45)
        workbook.close()

        attachment = self.env["ir.attachment"].create(
            {
                "name": "reporte_ajustes_inventario.xlsx",
                "type": "binary",
                "datas": base64.b64encode(output.getvalue()),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
