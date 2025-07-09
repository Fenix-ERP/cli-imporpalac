{
    "name": "Payment type Imporpalac",
    "category": "Sales/Sales",
    "version": "17.0.1.0.0",
    "author": "Jorge Armas",
    "summary": "This module allows to add the payment type in the quote",
    "depends": ["sale_management", "account", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_type.xml",
        "views/accout_move_inherit.xml",
        "views/sale_order_inherit.xml",
        "data/payment_type_data.xml",
        "views/res_partner_inherit.xml",
        "views/stock_picking.xml",
        "views/stock_warehouse_inherit.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "payment_type/static/src/scss/image_hover.scss",
            "payment_type/static/src/js/image_zoom.js",
            "payment_type/static/src/xml/image_modal.xml",
        ],
    },
    "demo": [],
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "license": "LGPL-3",
}
