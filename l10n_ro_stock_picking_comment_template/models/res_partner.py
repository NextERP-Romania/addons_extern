from odoo import models, fields, api, _


class res_partner(models.Model):
    _inherit = 'res.partner'
    mean_transp = fields.Char(string='Mean transport', help="visible only in pickings, and can be modify only from there; is keeping all the time the last not null value")
