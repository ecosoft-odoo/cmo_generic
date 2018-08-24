# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    bank_transfer_id = fields.Many2one(
        'bank.account.transfer', string='Bank Transfer', copy=False)
