from odoo import models, fields, api
from odoo.http import request

class PrintLabelWizard(models.TransientModel):
    _name = 'print.label.wizard'
    _description = 'Wizard for printing Zebra labels'

    print_barcode = fields.Boolean(
        string='Print barcode',
        default=True
    )
    print_supplier_barcode = fields.Boolean(
        string='Print supplier barcode',
        default=True
    )

    @api.onchange("print_barcode", "print_supplier_barcode")
    def _onchange_print_options(self):
        if self.print_barcode:
            self.print_supplier_barcode = False
        elif self.print_supplier_barcode:
            self.print_barcode = False

    def action_print_labels(self):
        picking_id = self.env.context.get('active_id')
        picking = self.env['stock.picking'].browse(picking_id)
        
        return picking.action_print_test_label(
            self.print_barcode,
            self.print_supplier_barcode
        )