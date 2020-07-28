# Copyright 2020 NextERP Romania SRL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Romania - Stock Picking Comment Template",
    "category": "Localization",
    "description":"""
# if the model stock_picking_repot_valued is is installed after this module will not work as intended
# in this module we overwrite the field valued = fields.Boolean(related="partner_id.valued_picking", readonly=True) not to be partner related
# we didn't put dependency on this module because that module is dependent on stock_account that is maybe not used
    
    """,
    "depends": ["stock", 
                "purchase_stock", 
                "stock_picking_comment_template",
                "l10n_ro_stock_account", # normaly is not neccesary, but without it is giving error at stock_location_view.xml import  
                ],
    "data": ["data/l10n_ro_stock_picking_comment_template.xml",
             "views/stock_location_view.xml",
             "views/stock_picking_view.xml",
             "report/stock_picking_report_valued_for_purchase_inShop.xml"
             ],
    "license": "AGPL-3",
    "version": "13.0.1.0.0",
    "author": "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
}
