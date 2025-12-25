from odoo import _, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_open_print_wizard(self):
        return {
            "name": "Imprimir etiquetas Zebra",
            "type": "ir.actions.act_window",
            "res_model": "print.label.wizard",
            "view_mode": "form",
            "view_id": self.env.ref("zebra.view_print_label_wizard_form").id,
            "target": "new",
            "context": dict(
                self.env.context,
                active_id=self.id,
            ),
        }

    def action_print_test_label(self, print_barcode=True, print_supplier_barcode=True):
        """Generar etiquetas ZPL para los movimientos de productos (agrupados de 2 en 2)"""
        moves = self.move_ids
        if not moves:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sin movimientos",
                    "message": "No hay movimientos de productos para imprimir",
                    "type": "warning",
                },
            }

        # Generar ZPL para cada par de movimientos
        zpl_codes = []
        for move in moves:
            product = move.product_id
            zpl_code = self._generate_zpl_for_products(
                product, print_barcode, print_supplier_barcode
            )
            zpl_codes.append(zpl_code)

        # Unir todos los códigos ZPL
        full_zpl = "".join(zpl_codes)

        return {
            "type": "ir.actions.client",
            "tag": "zebra_print_action",
            "params": {"zpl_code": full_zpl},
        }

    def _split_text_into_lines(self, text, max_chars_per_line=120):
        """Dividir texto en líneas según máximo de caracteres"""
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

        # Unir con \n para saltos de línea en ZPL
        return "\\&".join(lines)

    def _get_barcode_to_print(self, product, print_barcode, print_supplier_barcode):
        """Obtener el código de barras según las opciones seleccionadas"""
        if not product:
            return ""

        # Validar que solo se seleccione una opción
        if print_barcode and print_supplier_barcode:
            raise UserError(
                _("You can only select one option: Product code or supplier code.")
            )

        if print_barcode:
            if not product.barcode:
                raise UserError(
                    _("The product %s does not have a configured product barcode")
                    % product.name
                )
            return product.barcode

        elif print_supplier_barcode:
            # Usar el campo barcode_supp del proveedor
            if hasattr(product, "barcode_supp") and product.barcode_supp:
                return product.barcode_supp
            else:
                raise UserError(
                    _("The product %s does not have a configured supplier barcode")
                    % product.name
                )

        else:
            return ""

    def _get_zpl_template(self):
        zpl_template = (
            self.env["ir.config_parameter"].sudo().get_param("zebra.zpl.template")
        )
        return zpl_template

    def _generate_zpl_for_products(
        self,
        product=None,
        print_barcode=True,
        print_supplier_barcode=False,
    ):
        """Generar código ZPL para un producto específico"""
        product_lines = self._split_text_into_lines(product.name) if product else ""

        product_code = product.default_code if product and product.default_code else ""

        barcode = self._get_barcode_to_print(
            product, print_barcode, print_supplier_barcode
        )
        unit = product.uom_id.name or ""
        ubication = self.location_dest_id.complete_name or ""

        zpl_template = self._get_zpl_template()

        try:

            zpl_code = zpl_template.format(
                product_name=product_lines,
                barcode=barcode,
                product_code=product_code,
                unit=unit,
                ubication=ubication,
            )
        except Exception:
            raise UserError(
                _(
                    "The Zebra ZPL template does not exist or is corrupted. Please configure it in the system parameters."
                )
            )
        return zpl_code
