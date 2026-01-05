from odoo import api, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    journal_id = fields.Many2one("account.journal", string="Diario Contable")
    payment_method_ids = fields.One2many(
        "stock.warehouse.payment.method",
        "warehouse_id",
        string="Payment Methods",
        copy=True,
    )
    current_payment_type_ids_domain = fields.Char(
        compute="_compute_current_payment_type_domain",
        store=False,
    )

    @api.depends("payment_method_ids")
    def _compute_current_payment_type_domain(self):
        for record in self:
            payment_type_ids = record.payment_method_ids.mapped("payment_type_id.id")
            self.current_payment_type_ids_domain = (
                f"[('id', 'not in', {payment_type_ids})]"
            )


class StockWarehousePaymentMethod(models.Model):
    _name = "stock.warehouse.payment.method"
    _description = "Stock Warehouse Payment Method"

    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        required=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
        copy=True,
    )
    current_payment_type_ids_domain = fields.Char(
        related="warehouse_id.current_payment_type_ids_domain",
    )
    payment_type_id = fields.Many2one(
        "payment.type", string="Payment Type", required=True
    )
    journal_payment_ids = fields.Many2many(
        "account.journal",
        string="Payment Journals",
    )
