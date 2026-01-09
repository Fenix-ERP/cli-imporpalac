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
        model = self.env[active_model].browse(picking_id)
        return model.action_print_test_label(print_barcode, print_supplier_barcode)
