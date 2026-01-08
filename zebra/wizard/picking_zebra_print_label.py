from odoo import _, fields, models


class PrintLabelWizard(models.TransientModel):
    _name = "print.label.wizard"
    _description = "Wizard for printing Zebra labels"

    barcode_type = fields.Selection(
        [("internal", _("Internal Barcode")), ("supplier", _("Supplier Barcode"))],
        string="Select barcode to print",
        default="internal",
        required=True,
    )

    def action_print_labels(self):
        self.ensure_one()
        picking_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model", "stock.picking")
        print_barcode = self.barcode_type == "internal"
        print_supplier_barcode = self.barcode_type == "supplier"

        if active_model == "stock.picking":
            picking = self.env["stock.picking"].browse(picking_id)
            picking.action_print_test_label(print_barcode, print_supplier_barcode)
        elif active_model == "product.template":
            product = self.env["product.template"].browse(picking_id)
            product.action_print_product_label(print_barcode, print_supplier_barcode)

        return {"type": "ir.actions.act_window_close"}
