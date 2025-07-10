{
    "name": "Counter Sale Imporpalac",
    "category": "Sales/Sales",
    "version": "17.0.1.0.0",
    "author": "Santiago Illapa / FenixERP",
    "summary": "This module is used for the sales flow at the counter",
    "depends": [
        "sale_management",
        "account",
        "stock",
        "payment_type",
        "sale_order_payment",
    ],
    "data": [
        "security/counter_sale_security.xml",
        "views/sale_order_inherit.xml",
        "views/stock_picking_inherit.xml",
        "wizards/sale_order_cancel_wizard_view.xml",
    ],
    "demo": [],
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "license": "LGPL-3",
}
