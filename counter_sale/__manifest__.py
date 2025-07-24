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
        "stock_picking_flow",
        "sale_order_ticket",
    ],
    "data": [
        "security/counter_sale_security.xml",
        "views/sale_order_inherit.xml",
        "views/stock_picking_inherit.xml",
        "wizards/sale_order_cancel_wizard_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "counter_sale/static/src/js/confirm_btn_controller.js",
            "counter_sale/static/src/js/print_ticket.js",
        ],
    },
    "demo": [],
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "license": "LGPL-3",
}
