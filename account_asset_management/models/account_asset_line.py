# -*- coding: utf-8 -*-
# Copyright 2009-2017 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime
import logging
import pandas as pd
from openerp import api, fields, models, _
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.exceptions import Warning as UserError

_logger = logging.getLogger(__name__)


class AccountAssetLine(models.Model):
    _name = 'account.asset.line'
    _description = 'Asset depreciation table line'
    _order = 'type, line_date'

    name = fields.Char(string='Depreciation Name', size=64, readonly=True)
    asset_id = fields.Many2one(
        comodel_name='account.asset', string='Asset',
        required=True, ondelete='cascade')
    previous_id = fields.Many2one(
        comodel_name='account.asset.line',
        string='Previous Depreciation Line',
        readonly=True)
    parent_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('open', 'Running'),
            ('close', 'Close'),
            ('removed', 'Removed')],
        related='asset_id.state',
        string='State of Asset')
    depreciation_base = fields.Float(
        related='asset_id.depreciation_base',
        string='Depreciation Base')
    amount = fields.Float(
        string='Amount', digits=dp.get_precision('Account'),
        required=True)
    remaining_value = fields.Float(
        compute='_compute_values',
        digits=dp.get_precision('Account'),
        string='Next Period Depreciation',
        store=True)
    depreciated_value = fields.Float(
        compute='_compute_values',
        digits=dp.get_precision('Account'),
        string='Amount Already Depreciated',
        store=True)
    line_date = fields.Date(string='Date', required=True)
    line_days = fields.Integer(
        string='Days',
        readonly=True,
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Depreciation Entry', readonly=True)
    move_check = fields.Boolean(
        compute='_compute_move_check',
        string='Posted',
        store=True)
    type = fields.Selection(
        selection=[
            ('create', 'Depreciation Base'),
            ('depreciate', 'Depreciation'),
            ('remove', 'Asset Removal')],
        readonly=True, default='depreciate')
    init_entry = fields.Boolean(
        string='Initial Balance Entry',
        help="Set this flag for entries of previous fiscal years "
             "for which OpenERP has not generated accounting entries.")

    @api.depends('amount', 'previous_id')
    @api.multi
    def _compute_values(self):
        dlines = self
        if self._context.get('no_compute_asset_line_ids'):
            # skip compute for lines in unlink
            exclude_ids = self._context['no_compute_asset_line_ids']
            dlines = dlines.filtered(lambda l: l.id not in exclude_ids)
        dlines = self.filtered(lambda l: l.type == 'depreciate')
        dlines = dlines.sorted(key=lambda l: l.line_date)

        for i, dl in enumerate(dlines):
            if i == 0:
                depreciation_base = dl.depreciation_base
                depreciated_value = dl.previous_id \
                    and (depreciation_base - dl.previous_id.remaining_value) \
                    or 0.0
                remaining_value = \
                    depreciation_base - depreciated_value - dl.amount
            else:
                depreciated_value += dl.previous_id.amount
                remaining_value -= dl.amount
            dl.depreciated_value = depreciated_value
            dl.remaining_value = remaining_value

    @api.depends('move_id')
    @api.multi
    def _compute_move_check(self):
        for line in self:
            line.move_check = bool(line.move_id)

    @api.onchange('amount')
    def _onchange_amount(self):
        if self.type == 'depreciate':
            self.remaining_value = self.depreciation_base - \
                self.depreciated_value - self.amount

    @api.multi
    def write(self, vals):
        for dl in self:
            if vals.get('line_date'):
                if isinstance(vals['line_date'], datetime.date):
                    vals['line_date'] = vals['line_date'].strftime('%Y-%m-%d')
            line_date = vals.get('line_date') or dl.line_date
            asset_lines = dl.asset_id.depreciation_line_ids
            if vals.keys() == ['move_id'] and not vals['move_id']:
                # allow to remove an accounting entry via the
                # 'Delete Move' button on the depreciation lines.
                if not self._context.get('unlink_from_asset'):
                    raise UserError(_(
                        "You are not allowed to remove an accounting entry "
                        "linked to an asset."
                        "\nYou should remove such entries from the asset."))
            elif vals.keys() == ['asset_id']:
                continue
            elif dl.move_id and not self._context.get(
                    'allow_asset_line_update'):
                raise UserError(_(
                    "You cannot change a depreciation line "
                    "with an associated accounting entry."))
            elif vals.get('init_entry'):
                check = asset_lines.filtered(
                    lambda l: l.move_check and l.type == 'depreciate' and
                    l.line_date <= line_date)
                if check:
                    raise UserError(_(
                        "You cannot set the 'Initial Balance Entry' flag "
                        "on a depreciation line "
                        "with prior posted entries."))
            elif vals.get('line_date'):
                if dl.type == 'create':
                    check = asset_lines.filtered(
                        lambda l: l.type != 'create' and
                        (l.init_entry or l.move_check) and
                        l.line_date < vals['line_date'])
                    if check:
                        raise UserError(
                            _("You cannot set the Asset Start Date "
                              "after already posted entries."))
                else:
                    check = asset_lines.filtered(
                        lambda x: (x.init_entry or x.move_check) and
                        x.line_date > vals['line_date'] and x != dl)
                    if check:
                        raise UserError(_(
                            "You cannot set the date on a depreciation line "
                            "prior to already posted entries."))
        return super(AccountAssetLine, self).write(vals)

    @api.multi
    def unlink(self):
        ctx = {}
        for dl in self:
            if dl.type == 'create':
                raise UserError(_(
                    "You cannot remove an asset line "
                    "of type 'Depreciation Base'."))
            elif dl.move_id:
                raise UserError(_(
                    "You cannot delete a depreciation line with "
                    "an associated accounting entry."))
            previous = dl.previous_id
            next = dl.asset_id.depreciation_line_ids.filtered(
                lambda l: l.previous_id == dl and l not in self)
            if next:
                next.previous_id = previous
            ctx = dict(self._context, no_compute_asset_line_ids=self.ids)
        return super(
            AccountAssetLine, self.with_context(ctx)).unlink()

    def _setup_move_data(self, depreciation_date, period):
        asset = self.asset_id
        move_data = {
            'name': asset.name,
            'date': depreciation_date,
            'ref': self.name,
            'period_id': period.id,
            'journal_id': asset.profile_id.journal_id.id,
        }
        return move_data

    def _setup_move_line_data(self, depreciation_date, period,
                              account, type, move_id):
        asset = self.asset_id
        amount = self.amount
        analytic_id = False
        if type == 'depreciation':
            debit = amount < 0 and -amount or 0.0
            credit = amount > 0 and amount or 0.0
        elif type == 'expense':
            debit = amount > 0 and amount or 0.0
            credit = amount < 0 and -amount or 0.0
            analytic_id = asset.account_analytic_id.id
        move_line_data = {
            'name': asset.name,
            'ref': self.name,
            'move_id': move_id,
            'account_id': account.id,
            'credit': credit,
            'debit': debit,
            'period_id': period.id,
            'journal_id': asset.profile_id.journal_id.id,
            'partner_id': asset.partner_id.id,
            'analytic_account_id': analytic_id,
            'date': depreciation_date,
            'asset_id': asset.id,
            'state': 'valid',
        }
        return move_line_data

    @api.multi
    def create_move(self):
        created_move_ids = []
        asset_ids = []
        for line in self:
            asset = line.asset_id
            depreciation_date = line.line_date
            ctx = dict(self._context,
                       account_period_prefer_normal=True,
                       company_id=asset.company_id.id,
                       allow_asset=True, novalidate=True)
            period = self.env['account.period'].with_context(ctx).find(
                depreciation_date)
            am_vals = line._setup_move_data(depreciation_date, period)
            move = self.env['account.move'].with_context(ctx).create(am_vals)
            depr_acc = asset.profile_id.account_depreciation_id
            exp_acc = asset.profile_id.account_expense_depreciation_id
            aml_d_vals = line._setup_move_line_data(
                depreciation_date, period, depr_acc, 'depreciation', move.id)
            self.env['account.move.line'].with_context(ctx).create(aml_d_vals)
            aml_e_vals = line._setup_move_line_data(
                depreciation_date, period, exp_acc, 'expense', move.id)
            self.env['account.move.line'].with_context(ctx).create(aml_e_vals)
            if move.journal_id.entry_posted:
                del ctx['novalidate']
                move.with_context(ctx).post()
            write_ctx = dict(self._context, allow_asset_line_update=True)
            line.with_context(write_ctx).write({'move_id': move.id})
            created_move_ids.append(move.id)
            asset_ids.append(asset.id)
        # we re-evaluate the assets to determine if we can close them
        for asset in self.env['account.asset'].browse(
                list(set(asset_ids))):
            if asset.company_id.currency_id.is_zero(asset.value_residual):
                asset.state = 'close'
        return created_move_ids

    @api.multi
    def create_single_move(self, depre_date, compound=True):
        """ Similar to create_move() but used for case Grouping
            - This method will always use depre_date as posting date!
            - Will use info of first asset to process, as it will merge lines!
            - If compound, it will aggregate by dr and cr
        """
        # TODO: currently, we only group all depreciation line of same group
        # into 1 JE. But still pending merge multiple lines into 1 line for
        # performance boost (will not able to assign asset id to move line)
        ctx = dict(self._context,
                   account_period_prefer_normal=True,
                   company_id=self.env.user.company_id.id,
                   allow_asset=True, novalidate=True)
        period = self.env['account.period'].with_context(ctx).find(depre_date)
        asset_ids = [x.asset_id.id for x in self]
        assets = self.env['account.asset'].browse(list(set(asset_ids)))
        if not assets:
            return []
        # Use data of the first asset, to get accounting information.
        asset = assets[0]
        journal = asset.profile_id.journal_id
        depr_acc = asset.profile_id.account_depreciation_id
        exp_acc = asset.profile_id.account_expense_depreciation_id
        asset_profile = asset.profile_id.display_name
        am_vals = {
            'name': '/',
            'date': depre_date,
            'ref': asset_profile,
            'period_id': period.id,
            'journal_id': journal.id,
        }
        move_lines = []
        if not compound:
            for line in self:
                aml_d_vals = line._setup_move_line_data(
                    depre_date, period, depr_acc, 'depreciation', False)
                move_lines.append((0, 0, aml_d_vals))
                aml_e_vals = line._setup_move_line_data(
                    depre_date, period, exp_acc, 'expense', False)
                move_lines.append((0, 0, aml_e_vals))
        if compound:
            move_lines = self._do_compound_move_lines(asset_profile,
                                                      depre_date, period,
                                                      depr_acc, exp_acc)
        # Create Move
        am_vals.update({'line_id': move_lines})
        move = self.env['account.move'].with_context(ctx).create(am_vals)
        # Link to depre lines
        write_ctx = dict(self._context, allow_asset_line_update=True)
        self.with_context(write_ctx).write({'move_id': move.id})
        if move.journal_id.entry_posted:
            del ctx['novalidate']
            move.with_context(ctx).post()
        # we re-evaluate the assets to determine if we can close them
        for asset in assets:
            if asset.company_id.currency_id.is_zero(asset.value_residual):
                asset.state = 'close'
        return [move.id]

    @api.multi
    def _do_compound_move_lines(self, asset_profile, depre_date,
                                period, depr_acc, exp_acc):

        def _setup_compound_move_line_data(c_lines, c_depre_date,
                                           c_period, c_acct, c_ttype):
            remove_list = [  # fields not to be used in group by sum
                'asset_id', 'ref', 'name', 'state', 'date',
                'period_id', 'partner_id', 'tag_id', 'tag_type_id',
            ]
            move_lines = []
            for line in c_lines:
                aml_vals = line._setup_move_line_data(
                    c_depre_date, c_period, c_acct, c_ttype, False)
                for f in remove_list:
                    if f in aml_vals:
                        del aml_vals[f]
                move_lines.append(aml_vals)
            return move_lines

        def _merge_compound_move_lines(debit_lines, credit_lines):
            merged_move_lines = []
            for move_lines in (debit_lines, credit_lines):
                if not move_lines:
                    continue
                keys = move_lines[0].keys()
                group_by = [x for x in keys if x not in ['debit', 'credit']]
                # Split Dr and Cr, don't mix it.
                dr_lines = filter(lambda x: x['debit'] > 0.0, move_lines)
                cr_lines = filter(lambda x: x['credit'] > 0.0, move_lines)
                for lines in (dr_lines, cr_lines):
                    if not lines:
                        continue
                    df = pd.DataFrame(lines)
                    df = df.fillna(False)
                    grouped = df.groupby(group_by).agg(sum)
                    lines = grouped.reset_index().to_dict('records')
                    for vals in lines:
                        vals.update({'name': asset_profile})
                        merged_move_lines.append((0, 0, vals))
            return merged_move_lines

        # Get cr/dr lines without some columns, prepare for merge
        debit_lines = _setup_compound_move_line_data(self, depre_date, period,
                                                     depr_acc, 'depreciation')
        credit_lines = _setup_compound_move_line_data(self, depre_date, period,
                                                      exp_acc, 'expense')
        move_lines = _merge_compound_move_lines(debit_lines, credit_lines)
        return move_lines

    @api.multi
    def open_move(self):
        self.ensure_one()
        return {
            'name': _("Journal Entry"),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': self._context,
            'nodestroy': True,
            'domain': [('id', '=', self.move_id.id)],
        }

    @api.multi
    def unlink_move(self):
        for line in self:
            move = line.move_id
            if move.state == 'posted':
                move.button_cancel()
            move.with_context(unlink_from_asset=True).unlink()
            # trigger store function
            line.with_context(unlink_from_asset=True).write(
                {'move_id': False})
            if line.parent_state == 'close':
                line.asset_id.write({'state': 'open'})
            elif line.parent_state == 'removed' and line.type == 'remove':
                line.asset_id.write({'state': 'close'})
                line.unlink()
        return True
