# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

_interval = {
    '15': lambda count: relativedelta(days=count*15),
    '30': lambda count: relativedelta(days=count*30),
    '90': lambda count: relativedelta(days=count*90),
    '180': lambda count: relativedelta(days=count*180),
    '365': lambda count: relativedelta(days=count*365)
}

NUMBER_INTERVALS = 6

class SVLAgeReport(models.TransientModel):
    _inherit = 'l10n.ro.svl.age.report'

    def _run_aged_inventory(self, products, locations):
        self = self.sudo()

        def _to_str(date):
            return fields.Date.to_string(date)

        date_ref = date_ref_next = fields.Date.from_string(self.date_ref)
        svl_date_from = _to_str(date_ref)
        svl_date_to = _to_str(date_ref - relativedelta(days=(NUMBER_INTERVALS-1)*int(self.interval_days)))
        domain = ['&',
                        ('product_id', 'in', products.ids),
                        '&',
                            ('create_date', '<=', svl_date_from),
                            '|',
                                ('l10n_ro_location_dest_id', 'in', locations),
                                ('l10n_ro_location_id', "in", locations),
                   ]
        products = self.env['stock.valuation.layer'].search(domain).mapped('product_id')

        dict1 = {}
        age_list = []
        if len(products.ids) == 1:

            self.env.cr.execute('''
            select product_id as product_id, sum(quantity) as quantity, sum(value) as value
                from stock_valuation_layer
                where product_id = %s and create_date::date<='%s' and ( l10n_ro_location_dest_id in %s or l10n_ro_location_id in %s)
                group by product_id''' % (products.id, svl_date_to, tuple(locations), tuple(locations)))
        else:
            self.env.cr.execute('''
            select product_id as product_id, sum(quantity) as quantity, sum(value) as value
                from stock_valuation_layer
                where product_id in %s and create_date::date<='%s' and ( l10n_ro_location_dest_id in %s or l10n_ro_location_id in %s)
                group by product_id''' % (tuple(products.ids), svl_date_to, tuple(locations), tuple(locations)))
        product_dicts = self.env.cr.dictfetchall()
        product_dicts = dict((item['product_id'], item) for item in product_dicts)
        
        for product in products:
            days = 0
            age_list = []
            for i in range(NUMBER_INTERVALS):
                date = date_ref - _interval[self.interval_days](i)
                age_list.append({
                    'date': date,
                    'quantity': 0,
                    'value': 0,
                })

                days_next = (date_ref - (date_ref - _interval[self.interval_days](i + 1))).days
                name = f'{days} - {days_next}'
                if i == NUMBER_INTERVALS - 1:
                    name += '+'
                age_list[i]['name'] = f'[{i+1}] {name} ' + _('days')
                days = days_next
            product_dict = product_dicts.setdefault(product.id, {'product_id': product.id, 'quantity': 0, 'value': 0})
            if product_dict['quantity']:
                quantity_svl = round(product_dict['quantity'], 2)
                value_svl = round(product_dict['value'], 2)
                age_list[NUMBER_INTERVALS - 1]['quantity'] = max(0, quantity_svl)
                age_list[NUMBER_INTERVALS - 1]['value'] = max(0, value_svl)
            if product.l10n_ro_property_stock_valuation_account_id:
                account_id = product.l10n_ro_property_stock_valuation_account_id.id
            else:
                account_id = product.categ_id.property_stock_valuation_account_id.id
            dict1[product] = {'age_list': age_list,
                              'account_id': account_id,
                              'product_id': product.id}

        # for interval_nb in [4, 3, 2, 1, 0]
        for interval_nb in reversed(range(NUMBER_INTERVALS - 1)):
            period_date_from = age_list[interval_nb]['date']
            period_date_to = age_list[interval_nb + 1]['date']
            domain_in = [
                       ('product_id', 'in', products.ids),
                       ('create_date', '<=', period_date_from),
                       ('create_date', '>', period_date_to),
                       ('l10n_ro_location_dest_id', 'in', locations),
                       ('quantity', '>=', 0.000),
                       ('l10n_ro_valued_type', "!=", 'internal_transfer'),
                       ]

            domain_out = [
                       ('product_id', 'in', products.ids),
                       ('create_date', '<=', period_date_from),
                       ('create_date', '>', period_date_to),
                       ('l10n_ro_location_id', "in", locations),
                       ('quantity', '<', 0.000),
                       ('l10n_ro_valued_type', "!=", 'internal_transfer'),
                       ]
            svls_in = self.env['stock.valuation.layer'].\
                read_group(domain=domain_in,
                           fields=['quantity:sum',
                                   'value:sum'],
                           groupby=['product_id'],
                           lazy=False)
            svls_out = self.env['stock.valuation.layer'].\
                read_group(domain=domain_out,
                           fields=['quantity:sum',
                                   'value:sum'],
                           groupby=['product_id'],
                           lazy=False)
            if svls_in:
                for svl_in in svls_in:
                    product = self.env['product.product'].browse(svl_in.get('product_id')[0])
                    dict1[product]['age_list'][interval_nb]['quantity'] = svl_in.get('quantity')
                    dict1[product]['age_list'][interval_nb]['value'] = svl_in.get('value')
                    remaining_qty_initial = sum([item['quantity'] for item in dict1[product]['age_list'][interval_nb:]])
                    if remaining_qty_initial == 0:
                        for item in dict1[product]['age_list'][interval_nb:]:
                            item['quantity'] = 0
                            item['value'] = 0
            if svls_out:
                for svl_out in svls_out:
                    product = self.env['product.product'].browse(svl_out.get('product_id')[0])
                    remaining_qty_initial = sum([item['quantity'] for item in dict1[product]['age_list'][interval_nb:]])
                    remaining_value_initial = sum([item['value'] for item in dict1[product]['age_list'][interval_nb:]])
                    remaining_qty = remaining_qty_initial - abs(svl_out.get('quantity'))
                    remaining_value = remaining_value_initial - abs(svl_out.get('value'))
                    if remaining_qty_initial == 0:
                        for item in dict1[product]['age_list'][interval_nb:]:
                            item['quantity'] = 0
                            item['value'] = 0
                    elif remaining_qty < 0:
                        dict1[product]['age_list'][interval_nb]['quantity'] = remaining_qty
                        dict1[product]['age_list'][interval_nb]['value'] = remaining_value
                        for item in dict1[product]['age_list'][interval_nb+1:]:
                            item['quantity'] = 0
                            item['value'] = 0
                    else:
                        for item in dict1[product]['age_list'][interval_nb:]:
                            if remaining_qty == 0:
                                item['quantity'] = 0
                                item['value'] = 0
                                continue
                            if item['quantity'] > remaining_qty:
                                item['quantity'] = remaining_qty
                                item['value'] = remaining_value
                                remaining_qty = 0
                                remaining_value = 0
                            else:
                                remaining_qty -= item['quantity']
                                remaining_value -= item['value']
        svl_date_to = self.date_ref
        # create report lines
        print('\n\ndict1', dict1)
        for product_dict in dict1:
            query = '''INSERT INTO l10n_ro_svl_age_report_line
            (report_id, name, date, date_in, product_id, account_id, quantity, value)
                VALUES '''
            for index, age_list in enumerate(dict1[product_dict]['age_list']):
                date_in = self.date_ref
                lista = {}
                if index == 0:
                    days = int(self.interval_days)
                    svl_date_from = date_in
                    svl_date_to = date_in - timedelta(days=days)
                if index == 1:
                    days = int(self.interval_days)*2
                    svl_date_from = date_in - timedelta(days=int(self.interval_days)-1)
                    svl_date_to = date_in - timedelta(days=days)
                if index == 2:
                    days = int(self.interval_days)*3
                    svl_date_from = date_in - timedelta(days=int(self.interval_days)*2-1)
                    svl_date_to = date_in - timedelta(days=days)
                if index == 3:
                    days = int(self.interval_days)*4
                    svl_date_from = date_in - timedelta(days=int(self.interval_days)*3-1)
                    svl_date_to = date_in - timedelta(days=days)
                if index == 4:
                    days = int(self.interval_days)*5
                    svl_date_from = date_in - timedelta(days=int(self.interval_days)*4-1)
                    svl_date_to = date_in - timedelta(days=days)
                if index == 5:
                    svl_date_to = date_in - timedelta(days=int(self.interval_days)*5+1)
                if age_list['quantity'] != 0  and index != 5:
                    self.env.cr.execute('''
                    select product_id as product_id, create_date::date as date_in, sum(remaining_qty) as quantity, sum(remaining_value) as value
                        from stock_valuation_layer
                        where product_id = %s and create_date::date between '%s' and '%s' and ( l10n_ro_location_dest_id in %s or l10n_ro_location_id in %s) and remaining_qty>0
                        group by product_id, date_in''' % (dict1[product_dict]['product_id'], svl_date_to, svl_date_from, tuple(locations), tuple(locations)))
                    lista = self.env.cr.dictfetchall()
                if age_list['quantity'] != 0 and index == 5:
                    self.env.cr.execute('''
                    select product_id as product_id, create_date::date as date_in, sum(remaining_qty) as quantity, sum(remaining_value) as value
                        from stock_valuation_layer
                        where product_id = %s and create_date::date <='%s' and ( l10n_ro_location_dest_id in %s or l10n_ro_location_id in %s) and remaining_qty>0
                        group by product_id, date_in''' % (dict1[product_dict]['product_id'], svl_date_to, tuple(locations), tuple(locations)))
                    lista = self.env.cr.dictfetchall()
                if dict1[product_dict]['account_id']:
                    if lista:
                        for idx, product in enumerate(lista):
                            query += f"({self.id}, '{age_list['name']}', '{_to_str(age_list['date'])}', '{product['date_in']}', {dict1[product_dict]['product_id']}," \
                                    f" {dict1[product_dict]['account_id']}, {product['quantity']}, {0 if product['quantity'] == 0 else product['value']})"
                            if idx != len(lista) - 1:
                                query += ','
                    else:
                        query += f"({self.id}, '{age_list['name']}', '{_to_str(age_list['date'])}', '{date_in}', {dict1[product_dict]['product_id']}," \
                           f" {dict1[product_dict]['account_id']}, {0}, { 0 })"
                else:
                    if lista:
                        for idx, product in enumerate(lista):
                            query += f"({self.id}, '{age_list['name']}', '{_to_str(age_list['date'])}', '{product['date_in']}', {dict1[product_dict]['product_id']}," \
                                f" NULL, {product['quantity']}, { 0 if product['quantity'] == 0 else product['value']})"
                            if idx != len(lista) - 1:
                                query += ','
                    else:
                        query += f"({self.id}, '{age_list['name']}', '{_to_str(age_list['date'])}', '{date_in}', {dict1[product_dict]['product_id']}," \
                            f" NULL, {0}, { 0 })"
                if index == NUMBER_INTERVALS-1:
                    query += ';'
                else:
                    query += ','
            self.env.cr.execute(query)

class SVLAgeReportLine(models.TransientModel):
    _inherit = 'l10n.ro.svl.age.report.line'

    date_in = fields.Date(readonly=True)
