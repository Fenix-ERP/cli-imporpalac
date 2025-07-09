from odoo import models, fields, api
from datetime import datetime

class SaleOrderPayment(models.Model):
    _name = "sale.order.payment"
    _description = "Sale Order Payment"

    name = fields.Char(string="Reference", default=lambda self: self.env['ir.sequence'].next_by_code('sale.order.payment'))

    order_ids = fields.Many2many('sale.order', string='Sales Orders')
    client_id = fields.Many2one(related='order_ids.partner_id', string='Client', store=True)
    date_order = fields.Date(string='Order Date')
    
    hour_register = fields.Datetime(string='Payment Register Time')
    hour_register_rectified = fields.Datetime(string='Rectified Payment Time')

    order_number = fields.Char(string='Order Number', compute='_compute_order_info')
    amount_total = fields.Monetary(string='Total Amount', compute='_compute_amount', currency_field='currency_id')

    rectified_order_number = fields.Char(string='Rectified Order Number')
    rectified_amount = fields.Monetary(string='Rectified Amount')
    
    difference = fields.Monetary(string='Difference', compute='_compute_difference')
    
    journal_id = fields.Many2one('account.journal', string='Payment Journal')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('draft', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft')

    payment_method = fields.Many2one(
        comodel_name="payment.type",
        string="Payment method",
        ondelete="cascade",
        readonly=True,
    )

    @api.depends('order_ids')
    def _compute_order_info(self):
        for rec in self:
            rec.order_number = ", ".join(rec.order_ids.mapped('name'))

    @api.depends('order_ids')
    def _compute_amount(self):
        for rec in self:
            rec.amount_total = sum(rec.order_ids.mapped('amount_total'))

    @api.depends('amount_total', 'rectified_amount', 'state')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.amount_total - rec.rectified_amount

    def action_open_payment_wizard(self):
        for payment in self:
            payment.state = 'paid'
            
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_ids = fields.Many2many('sale.order.payment', string='Payments Related', compute='_compute_payment_ids')

    payment_count = fields.Integer(string='Number of Payments', compute='_compute_payment_ids')

    def _compute_payment_ids(self):
        for order in self:
            payments = self.env['sale.order.payment'].search([('order_ids', 'in', order.id)])
            order.payment_ids = payments
            order.payment_count = len(payments)

    def action_open_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Payments',
            'res_model': 'sale.order.payment',
            'view_mode': 'tree',
            'domain': [('order_ids', 'in', self.id)],
            'context': {'default_order_ids': [self.id]},
        }

    def action_cancel_payment(self):
        res = super(SaleOrder, self).action_cancel_payment()
        for payment in self.payment_ids:
            if payment.state != 'paid':
                payment.state = 'cancelled'
        return res
    
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        create_payment = self.env['sale.order.payment'].create({
            'order_ids': [(6, 0, [self.id])],
            'client_id': self.partner_id.id,
            'date_order': self.date_order,
            'hour_register': datetime.now(),
            'amount_total': self.amount_total,
            'journal_id': self.warehouse_id.journal_payment_id.id,
            'payment_method': self.payment_method.id,
            'state': 'draft',
        })
        return res
