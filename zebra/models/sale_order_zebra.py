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
        # Usar tu código ZPL base y personalizarlo
        # zpl_template = "^XA^FO70,85^GFA,3154,3154,38,,::::::gP019C73E1E3E7E38783C7C1C,gP03BEF7F3F7F7F7CFE7EFE3C,gP03BCFM7E7CLE7C,gP03BFF77EI738FCIEFEE7C,gP03BFF7FE7FE38FDCFCFFCFC,gN08077FEFCEFFE39IDFCFFCFC01,gP077FEE0JE71FMDFC,gP077IE0JE73FDFKDFC,gP076IE0FDCE739FF9FB9F9C,,:::::::T0JFE1F8M07IF803IFC0FEI07IFC01IFE07E03IFC,S03JFE3F8L01JFC0KF0FE001JFE07JF07E0JFE,S07JFE3F8L03JFE1KF0FC003KF0KF8FE1KF,S07JFE3F8L07JFE3KF0FC003KF1KF8FE3KF,S07FJ03FM07F01FE3F807F1FC003F80FF1FC07F8FE3F80FF,S0FEJ03FM07E00FE3F807F1FC007F007E1F803F8FC3F007F,S0FEJ07FM0FE00FC3F007F1F8007F007E3F803F8FC7F007E,S0FCJ07FM0FE00FC7F007F1F8007E00FE3F8I01FC7F007E,S0FCJ07FM0FC00FC7F007E3F8007E00FE3FJ01FC7E00FE,R01FCIFC7EM0FC01FC7F7FFE3F800FE7FFE3FJ01FC7E00FE,R01FCIF87EM0FC01FC7E7FFE3F800FE7FFC3FJ01F8FE00FE,R01FCIF8FEL01FC03F87E7FFE3FI0FE7FFC7FJ01F8FE00FC,R01F9IF8FEL01FCIF8FE7FFE3FI0FCIFC7FJ03F8FE00FC,R01F8J0FCL01F9IF0FE00FC7FI0FC01FC7EJ03F8FC01FC,R03F8J0FCL01F9FFE0FE01FC7F001FC01FC7EJ03F8FC01FC,R03F8I01FCL03F9J0FC01FC7F001FC01F8FE00FE3F1FC01FC,R03F8I01FCL03F8J0FC01FC7F001FC01F8FE01FC7F1FC03F8,R03KF1IFCJ03F8I01FC01F87FFE1F803F8KFC7F1KF8,R03KF1IFCJ03FJ01FC01F87FFE1F803F8KFC7F1KF8,R03JFE1IFCJ03FJ01F803F87FFE3F803F0KF87E1KF,R01JFE0IF8J07FJ01F803F83FFE3F803F07JF07E0JFE,,::::::::I01P0201gO04K04L04L04,I01JFE1JFE3FM0JFE0JFE1JFC3JFC3JFC3JF0KF0FC3JF8,I01JFE1JFE3FL01JFE1JFE3JFC7JFC7JFC7JF8KF8FC7JF8,I01KF3JFE3FL03KF3JFE3JFE7JFC7JFCKF8KF8FC7JFC,I03F807F3F8I07FL03F80FE3F80FE7F00FC7FJ0FEJ0FE03F8FC03F9FCFE01F8,I03F007E7FJ07EL03F007E3F007E7E00FCFEJ0FEI01FC03F9FC03F1F8FC01F8,I03F007E7EJ07EL03F007E3F007E7E00FCFCJ0FCI01F803F1F803F1F8FC01F8,I03F007E7EJ07EL03F00FE7FJ07EJ0FCJ0FCI01F803F1F803F1F8FC01F8,I07F00FE7EJ07EL07F00FE7EJ0FEJ0FCJ0FEI01F803F1F80FF1F9FC03F8,I07F00FC7E7FFCFEL07E7FFC7EJ0FEJ0FCIF8JFE1F803F3F9FFE3F9F803F,I07E00FCFE7FF8FCL07E7FFC7EJ0FCI01FDIF0KF3F807F3F3FFC3F1F803F,I07E00FCFCIF8FCL07E7FFC7EJ0FCI01F9IF07JF3F007E3F3FFE3F1F803F,I07E00FCFCJ0FCL07E01FCFEJ0FCI01F8M07F3F007E3F00FE3F1F803F,I0FE01FCFCJ0FCL0FE01F8FCI01FCI01F8M07F3F007E3F00FE7F3F807E,I0FC01F9FCI01FCL0FC01F8FC01F9F803F3F8M07E3F00FE7F00FE7E3F007E,I0FC01F9FCI01FCL0FC01F8FC03F9F803F3F8M07E7F00FE7E00FC7E3F007E,I0FC03F9FEI01FCL0FC01F8FE07F9FC07F3FCM0FE7F81FC7E00FC7E3F80FE,I0FCIF9KF1IF8I01FC03F9KF1KF3JFE3JFE7JFC7E00FC7E3JFE,001FCIF1KF1IF8I01F803F0KF1JFE3JFE7JFC7JF87E01FCFE3JFC,001F9FFE0KF0IF8I01F803F0JFC0JFC1JFE7JF83JF0FE01FCFC1JF8,,::::::::^FO80,205^FB650,3,0,L,0^A0N,35,35^FD{product_name}^FS^FO385,120^FB280,1,0,C,0^A0N,35,35^FD{barcode}^FS^FO350,310^BY4,1,60^BEN,65,Y,N^FD{barcode}^FS^FO05,355^FB280,1,0,C,0^A0N,35,35^FD{ubication}^FS^FO,305^FB280,1,0,C,0^A0N,30,30^FD{unit}^FS^XZ"
        zpl_template = r"""
            ^XA
            ~TA000
            ~JSN
            ^LT0
            ^MNW
            ^MTT
            ^PON
            ^PMN
            ^LH0,0
            ^JMA
            ^PR4,4
            ~SD25
            ^JUS
            ^LRN
            ^CI27
            ^PA0,1,1,0
            ^XZ
            ^XA
            ^MMT
            ^PW831
            ^LL440
            ^LS0
            ^FO57,49^GFA,1853,4005,45,:Z64:eJztV0GL20YUHrtranRQ0oPoZUNMT8EH0dzSBIoW1j1rwfoNOYcctqWHDD4JHZw/0KTCJzEHnZdNyRZSupdC/0AgZnuI8GFMySGFDet+3xt5LWeXuGla6KEDT37zNPr05um9942VujA0x/J68fbaiKPdKN4dbm3hurVhrfr25fy3P84WDx++Oltc2YR8//jF6y9ePLh+5d7z1+9c3O121WI+XjyxXx6NTx/Pv9e0vGPs//r89bVftq9v7187vrbJjfniyN45u3Xn8eLo7M6mxXf3r391882t+0B+c/NyZ9M0LQpjTKHs4un49OnB4of5E7vQHkxFwbuXPdb6eX/b3//u6wePjr95/uDHd3vxkX154L96emt+ND8tTzf43Prp7ucfH2/fe/bpx78/erZpg5m54WVpMTLZKJtsWvz/+K+MNhKun1PrG0NpF7TllH5OW2N0kmQYRNSgtCCdWOEnhj0OoiRJmot9a6tyqvEKa+0IMq40bZRwirluLA4AlhAZcEmHEru3UXYwjxqLb6MgbvPp9qE5zCBeQc+N2CeYryHjSfGrE7cSJyqIO0NIHOwM1ZrPIZ4s+bRfKfhL0eHUm4W5V4WjmbJpY3GyQlZEZjSCCMhRJ04GbyH3gWqIDF+Nl4v083bR15BR4e6dI6t1nxn0AJOAdr6tiWzRNcQvv9J2PDU2nOoyNVWJHk3/130OkniJzMASORk42wVkhDSX7+8hHfoTSZR+ZgqjP+uZDD6ry5CDaIUcnCO31n0ubWXZif0T+DuzNszhK2zwVXxudulkaxfficgDoO4OBHlrhTxc85kpLQGfmEICPEJsPdmH4T4aa/lka4mMBG4xwAlCk9DOfTQWt60TJAkTW3sQZbU/tbo/QczdvYvIERNFIBPFfIO8jXzoBD7nkJF3gGQ4bPcnhwrZjD0c9hrIibrqYinJQGcZAQRcJUCOg3WfpfJSJnW3W6Z+Ze2J7YYnYuc+mj6jynaSZeoJciL+wt5iIcZNZOTGSJqDS2wPrWKC/pHTXqAY8+ZHIcIaciDI0kXYPKK1L2iMNgY+O/Fyz0h9oLjbBbgQaf1Pjl5jU38bJJWhyeHC4ykvOl2ND/fzXxz6Pax/cfQ+5OHLhl/aIiztRDK2tGUbc9h0WSKTS+vbcgSrzzUp2QTJmwwkY0lTjkkixy1Ud4RihLGQrIVkrXJpzeMWbGh3JiM51iozWxN5z7HTOVUNkxquoe4JcliVlS2KrNIsRYPGZjAvT2ZFMa7QtKnCeoJbmsyxNxQuwQXkQSZBxwCP1BQmZNVxjNXXHqoNfZk+ozjY6FB9k8L1EKcarkF5gjlWyLFi+7maqE84JzJLHI2/5sIy82dWuMSRIMhEoRtDVeEUzbkbZrSeVDcQZ5QyO3MnUjWhCJyqkdmWBkIz5z4j0OKzx8BOpFt7kzrGpBZahVe4XXweOWwgmsPA9VNRXVuCGovjZED4g/MFDxtjkEmp05FVKdWQDU+VUKsyEy5kTPfqY0xnR04dgrwjabLHGPM2cgdWduCD+oBER3HqYDeGWrTpM2iQ1tEBVgpyHVOSoGOReu5iLDFyjGVVOK5jqvxpm4SC3DbjqST7jEcPWsdV23ZdIM+RSSYS0xp5IGpr6LiwzUDWeYA0QF5oiWl9yJsssyUDF/ZaQ2H9t5BbK2ShwbhG5hnO2llpEehwOkbILUKM6rNLNZxmFddU2Pmy1qIaGfXoau9cpZVHx0bZ5ZInhWMX5kXu1EJ2wjW9FhmPB05BFjIZ1ofQPXcsjWmlEqE45EuBN2pkD3+vZM6iF1Xe1/4AXlnRRk9dpr4vr/BfYMp/fAU+YyHDaDfn0EVjqD8BYqc41A==:FF99
            ^BY4,2,45^FT343,341^BEN,,Y,N
            ^FD{barcode}^FS
            ^FO48,163^A0N,28,28^FB735,3,7,L^FH\^CI28^FD{product_name}^FS^CI27
            ^FPH,1^FT49,302^A0N,28,38^FH\^CI28^FD{unit}^FS^CI27
            ^FPH,1^FT0,111^A0N,28,38^FB787,1,7,R^FH\^CI28^FD{barcode}^FS^CI27
            ^FPH,1^FO49,324^A0N,28,28^FB198,2,7,L^FH\^CI28^FD{ubication}^FS^CI27
            ^PQ1,,,Y
            ^XZ

            """
        # zpl_template = "^XA^FO220,70^BY2,1,60^B3N,N,65,N,N^FD{barcode1}^FS^FO300,145^A0N,25,25^FD{barcode2}^FS^XZ"

        # Reemplazar valores dinámicos
        zpl_code = zpl_template.format(
            product_name=product_lines,
            barcode=barcode,
            product_code=product_code,
            unit=unit,
            ubication=ubication,
        )

        return zpl_code
