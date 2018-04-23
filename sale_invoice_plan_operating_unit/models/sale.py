# -*- coding: utf-8 -*-
from openerp import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _prepare_invoice(self, order, lines):
        invoice_vals = super(SaleOrder, self)._prepare_invoice(order, lines)
        invoice_vals.update({'operating_unit_id': order.operating_unit_id.id})
        return invoice_vals
