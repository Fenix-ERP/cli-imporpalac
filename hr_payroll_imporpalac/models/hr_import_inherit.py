from odoo import fields, models


class PayrollImportLine(models.TransientModel):
    _inherit = "hr.payroll.import.line"

    multa = fields.Float()
    otros_egresos = fields.Float()
    prestamo_emp = fields.Float()
    vales_caja = fields.Float()
    convenios_empresa = fields.Float()
