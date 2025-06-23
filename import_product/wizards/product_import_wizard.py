import base64
import csv
import io

from openpyxl import load_workbook

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


class ImportProductWizard(models.TransientModel):
    _name = "import.product.wizard"
    _description = "Import Product Wizard"

    file = fields.Binary(string="Archivo", required=False)

    def action_test(self):
        if not self.file:
            raise UserError(_("Debe subir un archivo."))

        file_data = base64.b64decode(self.file)
        file_format = self._get_file_format(file_data)
        data = self._parse_file(file_data, file_format)

        errores = []
        actualizables = 0
        creables = 0

        categorias_dict = {
            c.name.strip(): c.id for c in self.env["product.category"].search([])
        }
        productos_dict = {
            p.default_code.strip(): p for p in self.env["product.template"].search([]) if p.default_code
        }

        for i, row in enumerate(data[1:], start=2):  # comienza desde la fila 2
            try:
                if not row or len(row) < 16:
                    continue

                codigo = row[0].strip()
                categoria_nombre = row[15].strip()

                if not codigo:
                    errores.append(f"Fila {i+1}: Código vacío")
                    continue

                if categoria_nombre not in categorias_dict:
                    errores.append(f"Fila {i+1}: Categoría '{categoria_nombre}' no encontrada")
                    continue

                if codigo in productos_dict:
                    actualizables += 1
                else:
                    creables += 1

            except Exception as e:
                errores.append(f"Fila {i+1}: Error inesperado: {str(e)}")

        if errores:
            raise ValidationError("\n".join(errores))
        else:
            mensaje = f"Archivo válido.\n\n✅ Líneas que se actualizarían: {actualizables}\n🔁 Líneas que se crearían: {creables}"
            return {
                "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Simulación de importación",
                    "message": mensaje,
                    "type": "success",
                    "sticky": False,
                },
            }

    def _get_file_format(self, file_data):
        """Detecta el tipo de archivo según su contenido"""
        if file_data[:4] == b"PK\x03\x04":  # Este es el encabezado de archivos XLSX
            return "xlsx"
        elif file_data[:3] == b"\xef\xbb\xbf":  # BOM de archivos CSV (UTF-8 con BOM)
            return "csv"

        return ""

    def action_export_template(self):

        import xlsxwriter

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # Hoja principal
        worksheet = workbook.add_worksheet("Plantilla Lista de Precios")

        header_format = workbook.add_format(
            {
                "bold": True,
                "text_wrap": True,
                "valign": "vcenter",
                "align": "center",
                "border": 1,
                "bg_color": "#D9E1F2",
            }
        )

        sample_format_text = workbook.add_format(
            {
                "text_wrap": True,
                "valign": "top",
                "align": "left",
                "border": 1,
                "bg_color": "#FFF2CC",
            }
        )

        sample_format_number = workbook.add_format(
            {
                "valign": "top",
                "align": "right",
                "border": 1,
                "bg_color": "#FFF2CC",
                "num_format": "#,##0.00",
            }
        )

        headers = [
            "Nombre",
            "Codigo Producto",
            "Producto",
            "Cantidad Minima",
            "Precio",
            "Fecha Inicio",
            "Fecha Finalizacion",
        ]

        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)
        worksheet.set_column(0, len(headers) - 1, 30)

        # Fila de ejemplo
        example_row = [
            "Mayor",
            "GDBT0539A",
            "Capot Aluminio Peugeot 3008 2021/",
            0,
            555,
            "",
            "",
        ]
        for col_num, value in enumerate(example_row):
            if col_num in [3, 4]:  # Cantidad Minima, Precio
                worksheet.write_number(1, col_num, value, sample_format_number)
            else:
                worksheet.write(1, col_num, value, sample_format_text)

        # Hoja de observaciones
        worksheet2 = workbook.add_worksheet("Observaciones")
        header_observations_format = workbook.add_format(
            {
                "bold": True,
                "text_wrap": True,
                "valign": "vcenter",
                "align": "center",
                "border": 1,
                "bg_color": "#4CAF50",
                "color": "white",
            }
        )

        observations_format = workbook.add_format(
            {
                "bold": False,
                "text_wrap": True,
                "valign": "top",
                "align": "left",
                "border": 1,
                "bg_color": "#F9F9F9",
            }
        )

        worksheet2.write("A1", "Observaciones", header_observations_format)

        observaciones = [
            "Nombre: Nombre exacto de la lista de precios (case sensitive).",
            "Código Producto: Código interno del producto (default_code).",
            "Producto: Nombre del producto (referencial, no se utiliza para vincular).",
            "Cantidad Minima: Número entero o decimal. No debe dejarse vacío.",
            "Precio: Precio fijo a aplicar (decimal).",
            "Fecha Inicio: Formato YYYY-MM-DD.",
            "Fecha Finalizacion: Formato YYYY-MM-DD.",
        ]

        for row, obs in enumerate(observaciones, start=1):
            worksheet2.write(row, 0, obs, observations_format)

        worksheet2.set_column("A:A", 90)

        workbook.close()
        file_data = base64.b64encode(output.getvalue())
        output.close()

        attachment = self.env["ir.attachment"].create(
            {
                "name": "plantilla_lista_precios.xlsx",
                "type": "binary",
                "datas": file_data,
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def action_import(self):
        if not self.file:
            raise UserError(_("Debe subir un archivo."))

        file_data = base64.b64decode(self.file)
        file_format = self._get_file_format(file_data)
        data = self._parse_file(file_data, file_format)

        errores = []
        creados = 0
        actualizados = 0

        # Cache de categorías
        categorias_dict = {
            c.name.strip(): c.id for c in self.env["product.category"].search([])
        }

        productos_dict = {
            p.default_code.strip(): p for p in self.env["product.template"].search([]) if p.default_code
        }

        for i, row in enumerate(data[1:], start=2):  # saltar cabecera
            try:
                if len(row) < 29:
                    errores.append(f"Fila {i}: No tiene todas las columnas necesarias.")
                    continue

                codigo = row[0].strip()
                articulo = row[1].strip()
                marca = row[2].strip()
                modelo = row[3].strip()
                anio = row[4].strip()
                procedencia = row[5].strip()
                adicional_1 = row[6].strip() if row[6] else ""
                adicional_2 = row[7].strip() if row[7] else ""
                adicional_3 = row[8].strip() if row[8] else ""
                adicional_4 = row[9].strip() if row[9] else ""
                adicional_5 = row[10].strip() if row[10] else ""
                adicional_6 = row[11].strip() if row[11] else ""
                lado = row[12].strip() if row[12] else ""
                unidad_venta = row[13].strip()
                unidad_compra = row[14].strip()
                categoria = row[15].strip()
                costo = float(row[16]or 0.0) 
                pvp = float(row[17] or 0.0)
                minorista = float(row[18] or 0.0)
                mayorista = float(row[19] or 0.0)
                especial = float(row[20] or 0.0)
                nombre = row[21].strip()
                vender = row[22].strip().lower() in ["1", "true", "sí", "si"] if row[22] else False
                comprar = row[23].strip().lower() in ["1", "true", "sí", "si"] if row[23] else False
                importar = row[24].strip().lower() in ["1", "true", "sí", "si"] if row[24] else False
                tipo_producto = row[25].strip()
                categoria_importacion = row[26].strip() if row[26] else ""
                politica_control = row[27].strip()
                politica_facturacion = row[28].strip()

                categoria_id = categorias_dict.get(categoria)
                if not categoria_id:
                    errores.append(f"Fila {i}: Categoría '{categoria}' no encontrada.")
                    continue
                
                if tipo_producto == "Producto almacenable":
                    tipo_producto = "product"
                elif tipo_producto == "Consumible":
                    tipo_producto = "consu"
                elif tipo_producto == "Servicio":
                    tipo_producto = "service"

                vals = {
                    "default_code": codigo,
                    "articulo": articulo,
                    "name": nombre,
                    "categ_id": categoria_id,
                    "list_price": pvp,
                    "standard_price": costo,
                    "sale_ok": vender,
                    "purchase_ok": comprar,
                    "type": tipo_producto or "product",
                    "uom_id": self.env["uom.uom"].search([("name", "=ilike", unidad_venta)], limit=1).id,
                    "uom_po_id": self.env["uom.uom"].search([("name", "=ilike", unidad_compra)], limit=1).id,
                    "marca": marca,
                    "modelo": modelo,
                    "anio": anio,
                    "procedencia": procedencia,
                    "adicional_1": adicional_1,
                    "adicional_2": adicional_2,
                    "adicional_3": adicional_3,
                    "adicional_4": adicional_4,
                    "adicional_5": adicional_5,
                    "adicional_6": adicional_6,
                    "lado": lado,
                    "importar": importar,
                    "categoria_importacion": categoria_importacion,
                    "politica_control": politica_control,
                    "politica_facturacion": politica_facturacion,
                }

                producto = productos_dict.get(codigo)
                if producto:
                    producto.write(vals)
                    actualizados += 1
                else:
                    self.env["product.template"].create(vals)
                    creados += 1

            except Exception as e:
                errores.append(f"Fila {i}: Error inesperado: {str(e)}")

        mensaje = f"Importación completada.\n\nProductos actualizados: {actualizados}\nProductos creados: {creados}"
        if errores:
            mensaje += f"\n\nErrores detectados:\n- " + "\n- ".join(errores[:10])

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Resultado de importación",
                "message": mensaje,
                "type": "warning" if errores else "success",
                "sticky": False,
            },
        }


    def _parse_file(self, file_data, file_format):
        if file_format == "csv":
            lines = file_data.decode("utf-8").splitlines()
            reader = csv.reader(lines)
            next(reader)
            return list(reader)
        elif file_format == "xlsx":
            workbook = load_workbook(io.BytesIO(file_data))
            sheet = workbook.active
            return [row for row in sheet.iter_rows(min_row=2, values_only=True)]
        else:
            raise UserError(
                _("Formato de archivo no válido. Solo se permiten archivos CSV o XLSX.")
            )
