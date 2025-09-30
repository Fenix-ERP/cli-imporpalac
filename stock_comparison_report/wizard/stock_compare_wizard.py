from odoo import fields, models


class StockCompareWizard(models.TransientModel):
    _name = "stock.compare.wizard"
    _description = "Comparación de Stock entre ubicaciones"

    location_a_id = fields.Many2one(
        "stock.location", string="Ubicación A", required=True
    )
    location_b_id = fields.Many2one(
        "stock.location", string="Ubicación B", required=True
    )
    min_qty = fields.Float(string="Cantidad mínima", required=True, default=1)

    category_id = fields.Many2one("product.category", string="Categoría")

    def generate_report_data_stock(self):
        domain = [
            ("location_id", "in", [self.location_a_id.id, self.location_b_id.id]),
        ]
        if self.category_id:
            domain.append(("categ_id", "=", self.category_id.id))
        quants = self.env["stock.quant"].sudo().search(domain)

        data = {}
        for quant in quants:
            data.setdefault(
                quant.product_id.id,
                {
                    "product": quant.product_id.code,
                    "product_name": quant.product_id.name,
                    "a_qty": 0,
                    "b_qty": 0,
                    "min_qty": self.min_qty,
                },
            )
            if quant.location_id == self.location_a_id:
                data[quant.product_id.id]["a_qty"] += quant.quantity
            elif quant.location_id == self.location_b_id:
                data[quant.product_id.id]["b_qty"] += quant.quantity

        filtered = [vals for vals in data.values() if vals["b_qty"] < self.min_qty]

        return {
            "products": filtered,
            "location_a_name": self.location_a_id.display_name,
            "location_b_name": self.location_b_id.display_name,
        }

    def action_compare(self):
        data = self.generate_report_data_stock()
        return self.env.ref(
            "stock_comparison_report.action_report_stock_compare"
        ).report_action(self, data=data)

    def action_compare_xls(self):
        data = self.generate_report_data_stock()
        return self.env.ref(
            "stock_comparison_report.action_report_stock_compare_xls"
        ).report_action(self, data=data)
