{
    "name": "Invoice Services Product Evoucher",
    "version": "17.0.0.0.1",
    "category": "stock",
    "summary": "Determine if an e-voucher contains services or storable products based on vendor tags and product types.",
    "author": "Anthony Simbaña / FenixERP",
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "depends": ["stock", "l10n_ec_purchase_reception", "account"],
    "data": [
        "views/account_evoucher_update_view.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "OPL-1",
}
