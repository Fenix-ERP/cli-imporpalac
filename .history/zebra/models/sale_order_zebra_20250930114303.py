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

        move_pairs = []
        for i in range(0, len(moves), 2):
            pair = moves[i : i + 2]
            move_pairs.append(pair)

        # Generar ZPL para cada par de movimientos
        zpl_codes = []
        for pair in move_pairs:
            product1 = pair[0].product_id if len(pair) >= 1 else None
            product2 = pair[1].product_id if len(pair) >= 2 else None

            zpl_code = self._generate_zpl_for_products(
                product1, product2, print_barcode, print_supplier_barcode
            )
            zpl_codes.append(zpl_code)

        # Unir todos los códigos ZPL
        full_zpl = "".join(zpl_codes)

        return {
            "type": "ir.actions.client",
            "tag": "zebra_print_action",
            "params": {"zpl_code": full_zpl},
        }

    def _split_text_into_lines(self, text, max_chars_per_line=30):
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

    def _generate_zpl_for_products(
        self,
        product1=None,
        product2=None,
        print_barcode=True,
        print_supplier_barcode=False,
    ):
        """Generar código ZPL para un producto específico"""
        product1_lines = self._split_text_into_lines(product1.name) if product1 else ""
        product2_lines = self._split_text_into_lines(product2.name) if product2 else ""

        product1_code = (
            product1.default_code if product1 and product1.default_code else ""
        )
        product2_code = (
            product2.default_code if product2 and product2.default_code else ""
        )

        barcode1 = self._get_barcode_to_print(
            product1, print_barcode, print_supplier_barcode
        )
        barcode2 = self._get_barcode_to_print(
            product2, print_barcode, print_supplier_barcode
        )
        # Usar tu código ZPL base y personalizarlo
        zpl_template = "^XA^FO220,70^BY2,1,60^B3N,N,65,N,N^FD{barcode1}^FS^FO300,145^A0N,25,25^FD{barcode2}^FS^XZ"

        # Reemplazar valores dinámicos
        zpl_code = zpl_template.format(
            product1_name=product1_lines,
            product2_name=product2_lines,
            barcode1=barcode1,
            barcode2=barcode2,
            product1_code=product1_code,
            product2_code=product2_code,
        )

        return zpl_code
