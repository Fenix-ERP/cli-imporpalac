{
    "name": "Imporpalac Print Label Zebra",
    "version": "17.0.1.0.0",
    "category": "Accounting",
    "summary": "Imporpalac Print Label Zebra",
    "author": "Anthony Simbaña / FenixERP",
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "depends": ["base", "sale"],
    "data": [
        "data/ir_config_parameter.xml",
        "security/ir.model.access.csv",
        "views/sale_order_zebra.xml",
        "wizard/picking_zebra_print_label_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "zebra/static/src/js/sale_order_zebra.js",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "OPL-1",
}
