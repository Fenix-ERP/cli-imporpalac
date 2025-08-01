{
    "name": "Sale Order Payment",
    "version": "17.0.1.0.0",
    "depends": ["sale_management", "payment_type", "account_card_settlement"],
    "category": "Sales",
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_payment_views.xml",
        "security/sale_order_payment_security.xml",
        "views/sale_order_inherit.xml",
        "views/stock_picking.xml",
        "wizards/sale_order_payment_method_wizard.xml",
    ],
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "installable": True,
    "license": "LGPL-3",
}
