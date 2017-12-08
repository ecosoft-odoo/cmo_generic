# -*- coding: utf-8 -*-
#
#    Author: Kitti Upariphutthiphong
#    Copyright 2014-2015 Ecosoft Co., Ltd.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

from openerp import fields, models, api


class AccountVoucher(models.Model):

    _inherit = "account.voucher"

    billing_id = fields.Many2one(
        'account.billing',
        string='Billing Ref',
        domain=[('state', '=', 'billed'), ('payment_id', '=', False)],
        readonly=True,
        states={'draft': [('readonly', False)]})

    @api.multi
    def proforma_voucher(self):
        # Write payment id back to Billing Document
        for rec in self:
            if rec.billing_id:
                billing = rec.billing_id
                billing.payment_id = rec.id
                billing.state = 'billed'
            return super(AccountVoucher, rec).proforma_voucher()

    @api.multi
    def cancel_voucher(self):
        # Set payment_id in Billing back to False
        for rec in self:
            if rec.billing_id:
                billing = rec.billing_id
                billing.payment_id = False
            return super(AccountVoucher, rec).cancel_voucher()

    @api.onchange('billing_id')
    def onchange_billing_id(self):
        partner_id = self.partner_id.id
        journal_id = self.journal_id.id
        amount = self.amount
        currency_id = self.currency_id.id
        ttype = self.type
        date = self.date
        if not partner_id or not journal_id:
            return {}
        billing_id = self.billing_id.id
        res = self.with_context(billing_id=billing_id).\
            recompute_voucher_lines(partner_id, journal_id, amount,
                                    currency_id, ttype, date)
        vals = self.with_context(billing_id=billing_id).\
            recompute_payment_rate(res, currency_id, date, ttype,
                                   journal_id, amount)
        for key in vals.keys():
            res[key].update(vals[key])
        if ttype == 'sale':
            del(res['value']['line_dr_ids'])
            del(res['value']['pre_line'])
            del(res['value']['payment_rate'])
        elif ttype == 'purchase':
            del(res['value']['line_cr_ids'])
            del(res['value']['pre_line'])
            del(res['value']['payment_rate'])
        self.line_dr_ids = res['value']['line_dr_ids']
        self.line_cr_ids = res['value']['line_cr_ids']

    @api.multi
    def recompute_voucher_lines(self, partner_id, journal_id,
                                price, currency_id, ttype, date):
        res = super(AccountVoucher, self).recompute_voucher_lines(
            partner_id, journal_id,
            price, currency_id, ttype, date)
        # Only scope down to selected invoices
        if self._context.get('billing_id', False):
            line_cr_ids = res['value']['line_cr_ids']
            line_dr_ids = res['value']['line_dr_ids']
            # Get Invoices from billing
            billing_id = self._context.get('billing_id', False)
            billing = self.env['account.billing'].browse(billing_id)
            move_line_ids = [self.env['account.move.line'].browse(
                line.move_line_id.id).id for line in billing.line_cr_ids]
            # invoice_ids = billing.invoice_ids.ids
            # move_line_ids = self.env['account.move.line'].\
            #     search([('invoice', 'in', invoice_ids)]).ids
            line_cr_ids = filter(lambda l: isinstance(l, dict) and
                                 l.get('move_line_id') in move_line_ids,
                                 line_cr_ids)
            line_dr_ids = filter(lambda l: isinstance(l, dict) and
                                 l.get('move_line_id') in move_line_ids,
                                 line_dr_ids)
            res['value']['line_cr_ids'] = line_cr_ids
            res['value']['line_dr_ids'] = line_dr_ids
        return res

class account_voucher_line(models.Model):

    _inherit = "account.voucher.line"

    reference = fields.Char(
        string='Invoice Reference',
        size=64,
        help="The partner reference of this invoice.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
