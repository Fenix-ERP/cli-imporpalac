from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PrintLabelWizard(models.TransientModel):
    _name = "print.label.wizard"
    _description = "Wizard for printing Zebra labels"

    show_count = fields.Boolean(
        default=True,
    )

    barcode_type = fields.Selection(
        [("internal", _("Internal Barcode")), ("supplier", _("Supplier Barcode"))],
        string="Select barcode to print",
        default="internal",
        required=True,
    )

    count = fields.Integer(
        string="Number of copies",
        default=1,
        required=False,
    )

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        active_model = self.env.context.get("active_model", "stock.picking")
        result["show_count"] = active_model in ("product.product", "product.template")
        return result

    @api.constrains("count")
    def _validate_count(self):
        for record in self:
            if record.count and record.count < 1:
                raise ValidationError(_("Negative or zero values are not allowed."))

    def action_print_labels(self):
        self.ensure_one()
        picking_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model", "stock.picking")
        print_barcode = self.barcode_type == "internal"
        print_supplier_barcode = self.barcode_type == "supplier"
        model = self.env[active_model].browse(picking_id)
        if active_model == "stock.picking":
            return model.action_print_test_label(print_barcode, print_supplier_barcode)
        else:
            count = self.count or 1
            return model.action_print_test_label(
                print_barcode, print_supplier_barcode, count
            )
