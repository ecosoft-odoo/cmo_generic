# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Eficent (<http://www.eficent.com/>)
#               <jordi.ballester@eficent.com>
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
##############################################################################
from openerp import models, fields, api


class HrExpenseExpense(models.Model):

    _inherit = 'hr.expense.expense'

    operating_unit_id = fields.Many2one(
        'operating.unit',
        string='Operating Unit',
        default=lambda self: self.env['res.users'].
        operating_unit_default_get(self._uid),
    )

    @api.model
    def account_move_get(self, expense_id):
        res = super(HrExpenseExpense, self).account_move_get(expense_id)
        expense = self.browse(expense_id)
        if expense.operating_unit_id:
            res['operating_unit_id'] = expense.operating_unit_id.id
        return res
