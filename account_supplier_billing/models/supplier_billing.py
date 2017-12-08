# -*- coding: utf-8 -*-

from openerp import fields, models, api
from openerp.exceptions import ValidationError
from openerp.tools.translate import _


class SupplierBilling(models.Model):
    _name = 'supplier.billing'
    _rec_name = 'number'
    _order = 'date desc, id desc'

    number = fields.Char(
        string='Number',
        size=32,
        readonly=True,
        copy=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        domain=[('supplier', '=', True), ],
        readonly=True,
        states={'draft': [('readonly', False)]},
        required=True,
    )
    date = fields.Date(
        string='Billing Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: fields.Date.context_today(self),
    )
    due_date = fields.Date(
        string='Due Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: fields.Date.context_today(self),
        required=True,
    )
    invoice_ids = fields.One2many(
        'account.invoice',
        'supplier_billing_id',
        readonly=True,
        states={'draft': [('readonly', False)]},
        strgin='Invoices',
    )
    invoice_related_count = fields.Integer(
        string='# of Invoice',
        compute='_compute_invoice_related_count',
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('billed', 'Billed'),
         ('cancel', 'Cancelled')
         ],
        string='Status',
        required=True,
        copy=False,
        default='draft',
    )

    @api.multi
    @api.depends('invoice_ids')
    def _compute_invoice_related_count(self):
        for billing in self:
            invoice_ids = self.env['account.invoice'].search([
                ('id', 'in', billing.invoice_ids.ids)
            ])
            billing.invoice_related_count = len(invoice_ids)

    @api.multi
    def invoice_relate_billing_tree_view(self):
        for rec in self:
            action = self.env.ref('account.action_invoice_tree2')
            result = action.read()[0]
            result.update({'domain': [('id', 'in', rec.invoice_ids.ids)]})
            return result

    @api.multi
    def action_billed(self):
        for rec in self:
            if rec.invoice_ids:
                for invoice in rec.invoice_ids:
                    invoice.update({
                        'date_due': rec.due_date,
                    })
            else:
                raise ValidationError(_('Should select at least 1 invoice.'))

            ctx = rec._context.copy()
            current_date = fields.Date.context_today(rec)
            fiscalyear_id = self.env['account.fiscalyear'].find(dt=current_date)
            ctx["fiscalyear_id"] = fiscalyear_id
            billing_number = self.env['ir.sequence']\
                .with_context(ctx).get('supplier.billing')
            res = rec.write({
                'state': 'billed',
                'number': billing_number,
            })
            return res

    @api.multi
    def action_cancel(self):
        res = self.write({'state': 'cancel'})
        if self.invoice_ids:
            for invoice in self.invoice_ids:
                invoice.update({
                    'date_due': False,
                    'supplier_billing_id': False,
                })
        return res
