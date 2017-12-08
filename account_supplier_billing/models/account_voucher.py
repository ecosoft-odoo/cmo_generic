# -*- coding: utf-8 -*-
from openerp import fields, models, api


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    supplier_billing_id = fields.Many2one(
        'supplier.billing',
        string='Billing Ref',
        domain="[('state', '=', 'billed'), ('partner_id', '=', partner_id)]",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id,
                            amount, currency_id, ttype, date, context=None):
        res = super(AccountVoucher, self).onchange_partner_id(
            cr, uid, ids, partner_id, journal_id, amount,
            currency_id, ttype, date, context=context)
        if 'value' in res:
            res['value']['supplier_billing_id'] = False
        return res

    @api.onchange('supplier_billing_id')
    def _onchange_supplier_billing_id(self):
        partner_id = self.partner_id.id
        journal_id = self.journal_id.id
        amount = self.amount
        currency_id = self.currency_id.id
        ttype = self.type
        date = self.date
        if not partner_id or not journal_id:
            return {}
        billing_id = self.supplier_billing_id.id
        self.date_value = self.supplier_billing_id.due_date
        res = self.with_context(supplier_billing_id=billing_id).\
            recompute_voucher_lines(partner_id, journal_id, amount,
                                    currency_id, ttype, date)
        vals = self.with_context(supplier_billing_id=billing_id).\
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
        # self.pre_line = res['value']['pre_line']
        # self.payment_rate = res['value']['payment_rate']

    @api.multi
    def recompute_voucher_lines(self, partner_id, journal_id,
                                price, currency_id, ttype, date):
        res = super(AccountVoucher, self).recompute_voucher_lines(
            partner_id, journal_id,
            price, currency_id, ttype, date)
        # Only scope down to selected invoices
        if self._context.get('supplier_billing_id', False):
            line_cr_ids = res['value']['line_cr_ids']
            line_dr_ids = res['value']['line_dr_ids']
            # Get Invoices from billing
            billing_id = self._context.get('supplier_billing_id', False)
            billing = self.env['supplier.billing'].browse(billing_id)
            invoice_ids = billing.invoice_ids.ids
            move_line_ids = self.env['account.move.line'].\
                search([('invoice', 'in', invoice_ids)]).ids
            line_cr_ids = filter(lambda l: isinstance(l, dict) and
                                 l.get('move_line_id') in move_line_ids,
                                 line_cr_ids)
            line_dr_ids = filter(lambda l: isinstance(l, dict) and
                                 l.get('move_line_id') in move_line_ids,
                                 line_dr_ids)
            res['value']['line_cr_ids'] = line_cr_ids
            res['value']['line_dr_ids'] = line_dr_ids
        return res
