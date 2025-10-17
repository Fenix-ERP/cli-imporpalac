import base64
import io

import xlrd

from odoo import _, models
from odoo.exceptions import ValidationError


class PayrollImportWizardExtension(models.TransientModel):
    _inherit = "hr.payroll.import.wizard"

    def import_excel(self):
        if not self.file:
            raise ValidationError(_("Por favor, carga un archivo antes de continuar."))

        data = base64.b64decode(self.file)
        workbook = xlrd.open_workbook(file_contents=data)
        sheet = workbook.sheet_by_index(0)

        # Validar encabezados del archivo
        headers = [
            sheet.cell(0, col_index).value.lower() for col_index in range(sheet.ncols)
        ]
        expected_headers = [
            "cédula",
            "nombre",
            "días",
            "horas 50",
            "horas 100",
            "anticipo",
            "multa",
            "otros egresos",
            "pres. quirografario",
            "pres. hipotecario",
            "pres. emp",
            "vales caja",
            "convenios empresa"
        ]
        if headers != expected_headers:
            raise ValidationError(
                f"El archivo debe tener las columnas: {', '.join(expected_headers)}."
            )

        # Crear líneas temporales con los nuevos campos
        lines = []
        for row_index in range(1, sheet.nrows):
            cedula = str(sheet.cell(row_index, 0).value).strip()

            if isinstance(sheet.cell(row_index, 0).value, float):
                cedula = "{:.0f}".format(sheet.cell(row_index, 0).value)

            cedula = str(cedula).strip()

            if len(cedula) == 9:
                cedula = "0" + cedula
            nombre = sheet.cell(row_index, 1).value
            days = sheet.cell(row_index, 2).value
            hours50 = sheet.cell(row_index, 3).value
            hours100 = sheet.cell(row_index, 4).value
            anticipo = sheet.cell(row_index, 5).value
            multa = sheet.cell(row_index, 6).value
            otros_egresos = sheet.cell(row_index, 7).value
            prestamo_q = sheet.cell(row_index, 8).value
            prestamo_h = sheet.cell(row_index, 9).value
            prestamo_emp = sheet.cell(row_index, 10).value
            vales_caja = sheet.cell(row_index, 11).value
            convenios_empresa = sheet.cell(row_index, 12).value

            # Crear las líneas y añadir los nuevos campos
            line = self.line_ids.create(
                {
                    "wizard_id": self.id,
                    "cedula": cedula,
                    "nombre": nombre,
                    "days": days,
                    "hours50": hours50,
                    "hours100": hours100,
                    "anticipo": anticipo,
                    "multa": multa,
                    "otros_egresos": otros_egresos,
                    "prestamo_q": prestamo_q,
                    "prestamo_h": prestamo_h,
                    "prestamo_emp": prestamo_emp,
                    "vales_caja": vales_caja,
                    "convenios_empresa": convenios_empresa,
                }
            )
            lines.append(line)

        # Abrir el formulario de la vista payroll.import.wizard.lines.form
        if lines:
            return {
                "type": "ir.actions.act_window",
                "name": "Revisión de Datos",
                "res_model": "hr.payroll.import.wizard",
                "view_mode": "form",
                "view_id": self.env.ref(
                    "hr_payroll_import.view_payroll_import_wizard_lines_form"
                ).id,  # Asegúrate de que la referencia a la vista sea correcta
                "res_id": self.id,  # Usamos el ID del wizard actual
                "target": "new",
            }
        else:
            raise ValidationError(_("No se importaron líneas."))

    def confirm_data(self):
        """
        Valida los datos y actualiza las nóminas en estado borrador.
        Continúa procesando aunque haya errores y muestra un resumen al final.
        """
        errores = []  # Lista para acumular errores

        for line in self.line_ids:
            try:
                # Buscar nómina en estado borrador
                payslip = self.env["hr.payslip"].search(
                    [
                        ("employee_id.identification_id", "=", line.cedula),
                        ("state", "=", "draft"),
                        ("date_from", ">=", self.date_start),
                        ("date_to", "<=", self.date_end),
                    ],
                    limit=1,
                )

                if not payslip:
                    raise ValidationError(
                        f"No se encontró una nómina en borrador asociada al empleado: {line.nombre} ({line.cedula})."
                    )

                for input_line in payslip.input_line_ids:
                    if input_line.code == "DY":
                        input_line.amount = line.days
                    if input_line.code == "OT50":
                        input_line.amount = line.hours50
                    if input_line.code == "OT100":
                        input_line.amount = line.hours100
                    if input_line.code == "SAR":
                        input_line.amount = line.anticipo
                    if input_line.code == "MU":
                        input_line.amount = line.multa
                    if input_line.code == "OE":
                        input_line.amount = line.otros_egresos
                    if input_line.code == "PQ":
                        input_line.amount = line.prestamo_q
                    if input_line.code == "ML":
                        input_line.amount = line.prestamo_h
                    if input_line.code == "LO":
                        input_line.amount = line.prestamo_emp
                    if input_line.code == "VA":
                        input_line.amount = line.vales_caja
                    if input_line.code == "CE":
                        input_line.amount = line.convenios_empresa
                payslip.compute_sheet()
                payslip.compute_sheet()

            except ValidationError as e:
                # Captura los errores específicos de validación y los guarda
                errores.append(str(e))
            except Exception as e:
                # Captura cualquier otro tipo de error y los guarda
                errores.append(
                    f"Error procesando línea con nombre {line.nombre} y cédula {line.cedula}: {str(e)}"
                )

        # Si hubo errores, mostrarlos al final del proceso
        if errores:
            error_message = "\n".join(errores)
            raise ValidationError(
                f"Se encontraron los siguientes problemas:\n{error_message}"
            )

        return {
            "type": "ir.actions.act_window_close",
        }

    def export_template(self):
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
            "Cédula",
            "Nombre",
            "Días",
            "Horas 50",
            "Horas 100",
            "Anticipo",
            "Multa",
            "Otros egresos",
            "Pres. quirografario",
            "Pres. hipotecario",
            "Pres. emp",
            "Vales caja",
            "Convenios empresa"
        ]

        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)
        worksheet.set_column(0, len(headers) - 1, 30)

        # Fila de ejemplo
        example_row = [
            "12345678",
            "Juan Pérez",
            30,
            10,
            20,
            50,
            100,
            200,
            300,
            400,
            500,
            600,
            700,
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
            "Cédula: Cédula exacta del empleado.",
            "Nombre: Nombre exacto del empleado.",
            "Días: Número entero o decimal. No debe dejarse vacío.",
            "Horas 50: Número entero o decimal. No debe dejarse vacío.",
            "Horas 100: Número entero o decimal. No debe dejarse vacío.",
            "Anticipo: Número entero o decimal. No debe dejarse vacío.",
            "Multa: Número entero o decimal. No debe dejarse vacío.",
            "Otros egresos: Número entero o decimal. No debe dejarse vacío.",
            "Pres. quirografario: Número entero o decimal. No debe dejarse vacío.",
            "Pres. hipotecario: Número entero o decimal. No debe dejarse vacío.",
            "Pres. emp: Número entero o decimal. No debe dejarse vacío.",
            "Vales caja: Número entero o decimal. No debe dejarse vacío.",
            "Convenios empresa: Número entero o decimal. No debe dejarse vacío.",
        ]

        for row, obs in enumerate(observaciones, start=1):
            worksheet2.write(row, 0, obs, observations_format)

        worksheet2.set_column("A:A", 90)

        workbook.close()
        file_data = base64.b64encode(output.getvalue())
        output.close()

        attachment = self.env["ir.attachment"].create(
            {
                "name": "plantilla_rol.xlsx",
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
