from odoo import models


class StockCompareReportXLSX(models.AbstractModel):
    _name = "report.stock_comparison_report.stock_compare_report_xls"
    _inherit = "report.report_xlsx.abstract"
    _description = "Report for Stock Comparison Excel"

    def generate_xlsx_report(self, workbook, data, invoices):
        sheet = workbook.add_worksheet("Reporte de Comparación de Stock")
        bold = workbook.add_format({"bold": True})
        money = workbook.add_format({"num_format": "#,##0.00"})
        row = 2
        col = 0

        # Título y fechas
        sheet.write(0, 4, "Resumen de Stock", bold)

        # Encabezados
        sheet.write(row, col, "Código", bold)
        sheet.write(row, col + 1, "Nombre", bold)
        sheet.write(row, col + 2, data.get("location_a_name"), bold)
        sheet.write(row, col + 3, data.get("location_b_name"), bold)
        sheet.write(row, col + 4, "Minimo", bold)
        row += 1

        total_a_qty = 0.0
        total_b_qty = 0.0
        for product in data.get("products", []):
            sheet.write(row, col, product.get("product", ""))
            sheet.write(row, col + 1, product.get("product_name", ""))
            sheet.write(row, col + 2, product.get("a_qty", 0.0), money)
            sheet.write(row, col + 3, product.get("b_qty", 0.0), money)
            sheet.write(row, col + 4, product.get("min_qty", 0.0), money)
            row += 1
            total_a_qty += product.get("a_qty", 0.0)
            total_b_qty += product.get("b_qty", 0.0)

        sheet.write(row, col + 2, total_a_qty, money)
        sheet.write(row, col + 3, total_b_qty, money)
