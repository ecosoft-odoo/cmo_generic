# -*- coding: utf-8 -*-
# © 2015 Eficent Business and IT Consulting Services S.L. -
# Jordi Ballester Alomar
# © 2015 Serpent Consulting Services Pvt. Ltd. - Sudhir Arya
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # kittiu: this purchase_order_change not exists in V8 it is from V8
    # PR at https://github.com/Eficent/operating-unit/pull/42
    # Load all unsold PO lines
#     @api.onchange('purchase_id')
#     def purchase_order_change(self):
#         """
#         Override to add Operating Unit from Purchase Order to Invoice.
#         """
#         if self.purchase_id and self.purchase_id.operating_unit_id:
#             # Assign OU from PO to Invoice
#             self.operating_unit_id = self.purchase_id.operating_unit_id.id
#         return super(AccountInvoice, self).purchase_order_change()

    @api.model
    def create(self, vals):
        if self._context.get('operating_unit_id', False):
            operating_unit_id = self._context['operating_unit_id']
            vals.update({'operating_unit_id': operating_unit_id})
        return super(AccountInvoice, self).create(vals)
