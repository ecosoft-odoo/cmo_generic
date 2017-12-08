# -*- coding: utf-8 -*-
# © 2015 Eficent Business and IT Consulting Services S.L. -
# Jordi Ballester Alomar
# © 2015 Serpent Consulting Services Pvt. Ltd. - Sudhir Arya
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class PurchaseLineInvoice(models.TransientModel):
    _inherit = 'purchase.order.line_invoice'

    @api.model
    def _make_invoice_by_partner(self, partner, orders, lines_ids):
        # Passing ou_id before create invoice
        operating_unit_id = orders and orders[0].operating_unit_id.id or False
        self = self.with_context(operating_unit_id=operating_unit_id)
        res = super(PurchaseLineInvoice, self).\
            _make_invoice_by_partner(partner, orders, lines_ids)
        return res
