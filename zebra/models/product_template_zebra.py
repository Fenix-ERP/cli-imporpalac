from odoo import _, models
from odoo.exceptions import UserError


class ProductTemplateZebra(models.Model):
    _inherit = "product.template"

    def action_open_print_wizard(self):
        return {
            "name": "Print Zebra labels",
            "type": "ir.actions.act_window",
            "res_model": "print.label.wizard",
            "view_mode": "form",
            "view_id": self.env.ref("zebra.view_print_label_wizard_form").id,
            "target": "new",
            "context": dict(
                self.env.context,
                active_id=self.id,
                active_model="product.template",
            ),
        }

    def action_print_product_label(
        self, print_barcode=True, print_supplier_barcode=False
    ):
        product = self

        zpl_template = (
            self.env["ir.config_parameter"].sudo().get_param("zebra.zpl.template")
        )
        if not zpl_template:
            raise UserError(
                _(
                    "The Zebra ZPL template does not exist or is corrupted."
                    " Please configure it in the system parameters."
                )
            )

        if print_barcode and print_supplier_barcode:
            raise UserError(
                _("You can only select one option: Product code or supplier code.")
            )

        barcode = ""
        if print_barcode:
            if not product.barcode:
                raise UserError(
                    _("The product %s does not have a configured product barcode")
                    % product.name
                )
            barcode = product.barcode
        elif print_supplier_barcode:
            if hasattr(product, "barcode_supp") and product.barcode_supp:
                barcode = product.barcode_supp
            else:
                raise UserError(
                    _("The product %s does not have a configured supplier barcode")
                    % product.name
                )

        product_lines = self._split_text_into_lines(product.name)
        product_code = product.default_code or ""
        unit = product.uom_id.name or ""

        try:
            zpl_code = zpl_template.format(
                product_name=product_lines,
                barcode=barcode,
                product_code=product_code,
                unit=unit,
                ubication="",
            )
        except Exception as error:
            raise UserError(
                _(
                    "The Zebra ZPL template does not exist or is corrupted. "
                    "Please configure it in the system parameters."
                )
            ) from error

        return {
            "type": "ir.actions.client",
            "tag": "zebra_print_action",
            "params": {"zpl_code": zpl_code},
        }

    def _split_text_into_lines(self, text, max_chars_per_line=120):
        if not text:
            return ""

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars_per_line:
                current_line += " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return "\\&".join(lines)
