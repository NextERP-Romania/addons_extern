# Copyright (C) 2022 NextERP Romania SRL
# License OPL-1.0 or later

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def write(self, vals):
        res = super(AccountMoveLine, self).write(vals)
        if 'analytic_account_id' in vals or 'analytic_tag_ids' in vals:
            for record in self:
                if record.parent_state == 'posted' and record.analytic_line_ids:
                    record.analytic_line_ids = [(5, 0, 0)]
            self.create_analytic_lines()
        return res

    @api.depends('product_id', 'account_id', 'partner_id', 'date')
    def _compute_analytic_account_id(self):
        self.analytic_account_id = False
        return super()._compute_analytic_account_id()
