# -*- coding: utf-8 -*-
# Copyright 2009-2016 Noviat.
# Copyright 2017 Therp BV.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import xlwt
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell
from openerp.addons.account_financial_report_webkit.report \
    .aged_open_invoices import AccountAgedOpenInvoicesWebkit
from openerp.tools.translate import _
# import logging
# _logger = logging.getLogger(__name__)


class AccountAgedOpenInvoicesWebkitXls(report_xls):

    # pylint: disable=old-api7-method-defined
    def create(self, cr, uid, ids, data, context=None):
        self._column_sizes = [
            20,  # Date
            20,  # Entry
            15,  # Journal
            30,  # Label
            20,  # Rec.
            20,  # Due Date
            20,  # Amount
            20,  # Not Due
            20,  # Overdue 0-30
            20,  # Overdue 30-90
            20,  # Overdue 90-180
            20,  # Overdue 180-360
            20,  # Overdue 360+
            ]
        self._balance_pos = 6
        return super(AccountAgedOpenInvoicesWebkitXls, self).create(
            cr, uid, ids, data, context=context)

    def _cell_styles(self, _xs):
        self._style_title = xlwt.easyxf(_xs['xls_title'])
        self._style_bold_blue_center = xlwt.easyxf(
            _xs['bold'] + _xs['fill_blue'] + _xs['borders_all'] +
            _xs['center'])
        self._style_center = xlwt.easyxf(
            _xs['borders_all'] + _xs['wrap'] + _xs['center'])
        self._style_bold = xlwt.easyxf(_xs['bold'] + _xs['borders_all'])

        format_yellow_bold = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self._style_account_title = xlwt.easyxf(
            format_yellow_bold + _xs['xls_title'])
        self._style_yellow_bold = xlwt.easyxf(format_yellow_bold)
        self._style_yellow_bold_right = xlwt.easyxf(
            format_yellow_bold + _xs['right'])
        self._style_yellow_bold_decimal = xlwt.easyxf(
            format_yellow_bold + _xs['right'],
            num_format_str=report_xls.decimal_format)

        self._style_default = xlwt.easyxf(_xs['borders_all'] + _xs['wrap'])
        self._style_decimal = xlwt.easyxf(
            _xs['borders_all'] + _xs['right'],
            num_format_str=report_xls.decimal_format)
        self._style_percent = xlwt.easyxf(
            _xs['borders_all'] + _xs['right'],
            num_format_str='0.00%')

    def _setup_worksheet(self, _p, _xs, data, wb):
        self.ws = wb.add_sheet(_p.report_name[:31])
        self.ws.panes_frozen = True
        self.ws.remove_splits = True
        self.ws.portrait = 0  # Landscape
        self.ws.fit_width_to_pages = 1
        self.ws.header_str = self.xls_headers['standard']
        self.ws.footer_str = self.xls_footers['standard']

    def _print_title(self, _p, _xs, data, row_pos):
        report_name = ' - '.join(
            [_p.report_name.upper(),
             _p.company.partner_id.name,
             _p.company.currency_id.name])
        c_specs = [
            ('report_name', 1, 0, 'text', report_name),
            ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            self.ws, row_pos, row_data, row_style=self._style_title)
        return row_pos

    def _print_empty_row(self, _p, _xs, data, row_pos):
        """
        Print empty row to define column sizes
        """
        c_specs = [('empty%s' % i, 1, self._column_sizes[i], 'text', None)
                   for i in range(len(self._column_sizes))]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            self.ws, row_pos, row_data, set_column_size=True)
        return row_pos

    def _print_header_title(self, _p, _xs, data, row_pos):
        c_specs = [
            ('coa', 1, 0, 'text', _('Chart of Account')),
            ('fy', 1, 0, 'text', _('Fiscal Year')),
            ('period_filter', 2, 0, 'text', _('Periods Filter')),
            ('cd', 1, 0, 'text', _('Clearance Date')),
            ('account_filter', 2, 0, 'text', _('Accounts Filter')),
            # ('partner_filter', 1, 0, 'text', _('Partners Filter')),
            ('tm', 1, 0, 'text', _('Target Moves')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            self.ws, row_pos, row_data,
            row_style=self._style_bold_blue_center)
        return row_pos

    def _print_header_data(self, _p, _xs, data, row_pos):
        period_filter = _('From') + ': '
        period_filter += _p.start_period.name if _p.start_period else u''
        period_filter += ' ' + _('To') + ': '
        period_filter += _p.stop_period.name if _p.stop_period else u''
        c_specs = [
            ('coa', 1, 0, 'text', _p.chart_account.name),
            ('fy', 1, 0, 'text',
             _p.fiscalyear.name if _p.fiscalyear else '-'),
            ('period_filter', 2, 0, 'text', period_filter),
            ('cd', 1, 0, 'text', _p.date_until),
            ('account_filter', 2, 0, 'text',
             _p.display_partner_account(data)),
            # ('partner_filter', 1, 0, 'text',
            #  _('Selected Partners') if _p.partner_ids else '-'),
            ('tm', 1, 0, 'text',
             _p.display_target_move(data)),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            self.ws, row_pos, row_data, row_style=self._style_center)
        return row_pos

    def _print_header(self, _p, _xs, data, row_pos):
        """
        Header Table: Chart of Account, Fiscal year, Filters, ...
        """
        row_pos = self._print_header_title(_p, _xs, data, row_pos)
        row_pos = self._print_header_data(_p, _xs, data, row_pos)
        self.ws.set_horz_split_pos(row_pos)  # freeze the line
        return row_pos + 1

    def _print_account_header(self, _p, _xs, data, row_pos, account):
        """
        Fill in a row with the code and name of the account
        """
        c_specs = [
            ('acc_title', len(self._column_sizes), 0, 'text',
             ' - '.join([account.code, account.name])),
            ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            self.ws, row_pos, row_data, self._style_account_title)
        return row_pos + 1

    def _print_partner_header(self, _p, _xs, data, row_pos, partner):
        """
        Fill in a row with the partner's name
        """
        partner_name, p_id, p_ref, p_name = partner
        c_specs = [
            ('partner_title', len(self._column_sizes), 0, 'text',
             partner_name if partner_name else _('No Partner')),
            ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(self.ws, row_pos, row_data, self._style_bold)
        return row_pos

    def _print_invoice_header(self, _p, _xs, data, row_pos):
        """
        Partner header line
        """
        c_specs = [
            ('date_h', 1, 0, 'text', _('Date'),
             None, self._style_yellow_bold),
            ('entry_h', 1, 0, 'text', _('Entry'),
             None, self._style_yellow_bold),
            ('journal_h', 1, 0, 'text', _('Journal'),
             None, self._style_yellow_bold),
            ('label_h', 1, 0, 'text', _('Label'),
             None, self._style_yellow_bold),
            ('rec_h', 1, 0, 'text', _('Rec.'),
             None, self._style_yellow_bold),
            ('due_date_h', 1, 0, 'text', _('Due Date'),
             None, self._style_yellow_bold),
            ('amount_h', 1, 0, 'text', _('Amount'),
             None, self._style_yellow_bold),
            ('not_due_h', 1, 0, 'text', _('Not Due'),
             None, self._style_yellow_bold)]
        for days in [30, 90, 180, 360]:
            entry = 'od_%s_h' % days
            label = _("Overdue ≤ %s d.") % days
            c_specs += [(entry, 1, 0, 'text', label)]
        c_specs += [('older_h', 1, 0, 'text', _("Overdue > 360 d."))]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            self.ws, row_pos, row_data,
            row_style=self._style_yellow_bold_right)
        return row_pos

    def _print_invoice_line(self, _p, _xs, data, row_pos, partner_line):
        """
        Invoice data line
        """
        c_specs = [
            ('date', 1, 0, 'text', partner_line['ldate'],
             None, self._style_default),
            ('entry', 1, 0, 'text', partner_line['move_name'],
             None, self._style_default),
            ('journal', 1, 0, 'text', partner_line['jcode'],
             None, self._style_default),
            ('label', 1, 0, 'text', partner_line['lname'],
             None, self._style_default),
            ('rec', 1, 0, 'text', partner_line['rec_name'],
             None, self._style_default),
            ('due_date', 1, 0, 'text', partner_line['date_maturity'],
             None, self._style_default),
            ('amount', 1, 0, 'number', partner_line['balance'] or 0.0,
             None, self._style_decimal),
        ]
        for r in _p.ranges:
            entry = 'od_%s' % r[0]
            c_specs += [(entry, 1, 0, 'number', partner_line[r] or 0.0)]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            self.ws, row_pos, row_data,
            row_style=self._style_decimal)
        return row_pos

    def _print_partner_footer(self, _p, _xs, data, row_pos,
                              account, line_count):
        """
        Partner header line
        """
        # Totals
        c_specs = [
            ('total', 6, 0, 'text', _('Total Partner'),
             None, self._style_yellow_bold)
        ]
        row_start = row_pos - line_count
        col_start = self._balance_pos
        start = rowcol_to_cell(row_start, col_start)
        stop = rowcol_to_cell(row_pos - 1, col_start)
        formula = 'SUM(%s:%s)' % (start, stop)
        c_specs += [('total_balance', 1, 0, 'number', None, formula)]
        col_start += 1
        for i, r in enumerate(_p.ranges):
            entry = 'total_%s' % i
            start = rowcol_to_cell(row_start, col_start + i)
            stop = rowcol_to_cell(row_pos - 1, col_start + i)
            formula = 'SUM(%s:%s)' % (start, stop)
            c_specs += [(entry, 1, 0, 'number', None, formula)]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            self.ws, row_pos, row_data,
            row_style=self._style_yellow_bold_decimal)

        return row_pos

    def _print_account_footer(self, _p, _xs, data, row_pos, lines):
        """
        Account footer line
        """
        # Totals
        c_specs = [
            ('total', 6, 0, 'text', _('Total'),
             None, self._style_yellow_bold),
            ('total_amount', 1, 0, 'number', lines['balance'] or 0.0,
             None, self._style_yellow_bold_decimal),
            ]
        for r in _p.ranges:
            entry = 'od_%s' % r[0]
            c_specs += [(entry, 1, 0, 'number', lines[r] or 0.0)]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            self.ws, row_pos, row_data,
            row_style=self._style_yellow_bold_decimal)
        return row_pos

    def _print_account_data(self, _p, _xs, data, row_pos, account):
        if _p.aged_open_inv[account.id]:
            partners = _p.partners_order[account.id]
            if not partners:
                return row_pos
            row_pos = self._print_account_header(
                _p, _xs, data, row_pos, account)
            lines = _p.aged_open_inv[account.id]
            line_total = []
            for partner in partners:
                partner_id = partner[1]
                row_pos = self._print_partner_header(
                    _p, _xs, data, row_pos, partner)
                row_pos = self._print_invoice_header(
                    _p, _xs, data, row_pos)
                row_pos_start = row_pos
                if partner_id in lines:
                    partner_lines = lines[partner_id]['lines']
                    for partner_line in partner_lines:
                        row_pos = self._print_invoice_line(
                            _p, _xs, data, row_pos, partner_line)
                line_count = row_pos - row_pos_start
                line_total.append(row_pos)
                row_pos = self._print_partner_footer(
                    _p, _xs, data, row_pos, account, line_count)
            row_pos = self._print_account_footer(_p, _xs, data, row_pos, lines)

        return row_pos + 1

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        self._cell_styles(_xs)
        self._setup_worksheet(_p, _xs, data, wb)

        row_pos = 0
        row_pos = self._print_title(_p, _xs, data, row_pos)
        row_pos = self._print_empty_row(_p, _xs, data, row_pos)
        row_pos = self._print_header(_p, _xs, data, row_pos)

        for account in objects:
            row_pos = self._print_account_data(
                _p, _xs, data, row_pos, account)


AccountAgedOpenInvoicesWebkitXls(
    'report.account.aged_open_invoices_xls',
    'account.account',
    parser=AccountAgedOpenInvoicesWebkit)
