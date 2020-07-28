from odoo import fields, models
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    def _prepare_picking(self):
        "put in picking also the puchase_id"
        res_dict = super()._prepare_picking()
        res_dict['purchase_id'] = self.id
        return res_dict