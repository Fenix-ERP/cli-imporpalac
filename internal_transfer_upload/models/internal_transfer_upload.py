from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _description = "Internal Transfer Upload Imporpalac"

    def action_internal_transfer_upload(self):
        return {
            "name": "Importar Productos a Transferencia Interna",
            "type": "ir.actions.act_window",
            "res_model": "import.transfer.product.wizard",
            "view_mode": "form",
            "view_id": self.env.ref(
                "internal_transfer_upload.view_import_transfer_product_wizard_form"
            ).id,
            "target": "new",
        }
