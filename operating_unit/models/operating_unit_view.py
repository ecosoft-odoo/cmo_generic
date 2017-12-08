# -*- coding: utf-8 -*-
from openerp import api, fields, models
from openerp import tools


class OperatingUnitView(models.Model):
    # This class is solely for PABI2
    _name = 'operating.unit.view'
    _auto = False

    name = fields.Char(
        string='Name',
    )
    code = fields.Char(
        string='Code',
    )
    active = fields.Boolean(
        string='Active',
    )

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" %
                   (self._table,
                    "select * from operating_unit",))
