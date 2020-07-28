from odoo import models, fields, api, _


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    delegate_id = fields.Many2one('res.partner', string='Delegate')
    mean_transp = fields.Char(string='Mean transport')
# if the model stock_picking_repot_valued is is installed after this module will not work as intended
# in this module we overwrite the field valued = fields.Boolean(related="partner_id.valued_picking", readonly=True) not to be partner related
# we didn't put dependency on this module because that module is dependent on stock_account that is maybe not used
    valued = fields.Boolean('Show stock values', default=True, readonly=False, help="show stock values only if is installed stock_picking_report_valued; and if is installed must be installed before this module")
    installed_stock_picking_report_valued = fields.Boolean(compute="_compute_installed_stock_picking_report_valued", compute_sudo=True)

    show_shop_price = fields.Boolean(compute="_compute_installed_stock_picking_report_valued", compute_sudo=True)
    
    def _compute_installed_stock_picking_report_valued(self):
        stock_piging_report_valued = self.env['ir.module.module'].search([('name','=','stock_picking_report_valued')])
        if stock_piging_report_valued.filtered(lambda r: r.state == 'installed'):
            self.installed_stock_picking_report_valued = True
            for record in self:
                if record.purchase_id and record.location_dest_id.merchandise_type=='shop' :
                    record.show_shop_price = True
                else:
                    record.show_shop_price = False
                
        else:
            self.installed_stock_picking_report_valued = False
            self.show_shop_price = False

    @api.onchange('delegate_id')
    def on_change_delegate_id(self):
        if self.delegate_id :
            self.mean_transp = self.delegate_id.mean_transp

    def write(self, vals):
        "if modified the mean_transp will write into delegate"
        mean_transp = vals.get('mean_transp',False)
        delegate_id = vals.get('delegate_id',False)
        if mean_transp and delegate_id:
            self.env['res.partner'].sudo().browse(delegate_id).write({'mean_transp':mean_transp})
        return super().write(vals)



