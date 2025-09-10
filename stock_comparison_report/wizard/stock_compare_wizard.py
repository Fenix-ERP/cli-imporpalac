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

    def generate_report_data_stock(self):
        domain = [
            ("location_id", "in", [self.location_a_id.id, self.location_b_id.id]),
        ]
        quants = self.env["stock.quant"].search(domain)

        data = {}
        for quant in quants:
            data.setdefault(
                quant.product_id.id,
                {
                    "product": quant.product_id.display_name,
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

        return {"products": filtered}

    def action_compare(self):
        """Llama al reporte PDF pasando los datos correctamente"""
        data = self.generate_report_data_stock()
        # Pasamos self como docs y los datos en 'data'
        return self.env.ref(
            "stock_comparison_report.action_report_stock_compare"
        ).report_action(self, data=data)
