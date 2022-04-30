# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TankStage(models.Model):
    _name = 'petrol.tank.stage'
    _description = 'Petrol Tank Stage'

    name = fields.Char(string="Stage Name", required=True)


class PetrolTank(models.Model):
    _name = 'petrol.tank'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Petrol Tank'

    name = fields.Char(required=True)
    capacity = fields.Float()
    used = fields.Float(compute='compute_used', store=True)
    charged = fields.Float(compute='compute_charged', store=True)
    balance = fields.Float(compute='compute_balance', store=True)
    balance_progress = fields.Float(compute='compute_balance')
    last_charge = fields.Date(compute='compute_last_charge', store=True)
    stage_id = fields.Many2one('petrol.tank.stage')
    charge_ids = fields.One2many('petrol.tank.charge', 'tank_id')
    use_ids = fields.One2many('petrol.tank.use', 'tank_id')

    @api.depends('use_ids.quantity')
    def compute_used(self):
        for rec in self:
            rec.used = 0
            if rec.use_ids:
                rec.used = sum([rec.quantity for rec in rec.use_ids])

    @api.depends('charge_ids.quantity')
    def compute_charged(self):
        for rec in self:
            rec.charged = 0
            if rec.use_ids:
                rec.charged = sum([rec.quantity for rec in rec.charge_ids])

    @api.depends('capacity', 'used', 'charged')
    def compute_balance(self):
        for rec in self:
            rec.balance = rec.charged + rec.capacity - rec.used
            if rec.capacity:
                rec.balance_progress = rec.balance * 100 / rec.capacity
            else:
                rec.balance_progress = 0

    @api.depends('charge_ids.charge_date')
    def compute_last_charge(self):
        for rec in self:
            if rec.charge_ids:
                dates = []
                for charge in rec.charge_ids:
                    if charge.charge_date:
                        dates.append(charge.charge_date)
                if dates:
                    rec.last_charge = max(dates)
            else:
                rec.last_charge = False


class TankCharge(models.Model):
    _name = 'petrol.tank.charge'
    _description = 'Petrol Tank Charge'

    name = fields.Char(required=True)
    tank_id = fields.Many2one('petrol.tank')
    charge_date = fields.Date()
    quantity = fields.Float()
    cost = fields.Float()


class TankUse(models.Model):
    _name = 'petrol.tank.use'
    _description = 'Petrol Tank Use'

    name = fields.Char(required=True)
    tank_id = fields.Many2one('petrol.tank', string="Source of Record")
    vehicle_id = fields.Many2one('fleet.vehicle')
    odometer = fields.Many2one('fleet.vehicle.odometer')
    current_quantity = fields.Float()
    quantity = fields.Float()
    datetime = fields.Datetime(string="Date & Time")
    last_odometer = fields.Float()
    last_quantity = fields.Float(compute='compute_last_quantity', store=True)
    liter_per_km_rate = fields.Float(compute='compute_liter_per_km_rate', store=True)

    @api.depends('odometer', 'last_odometer', 'quantity', 'last_quantity')
    def compute_liter_per_km_rate(self):
        for rec in self:
            if rec.odometer and rec.last_odometer and rec.quantity and rec.last_quantity:
                if rec.last_quantity - rec.quantity != 0:
                    rec.liter_per_km_rate = round((rec.last_odometer - rec.odometer.value) / (rec.last_quantity - rec.quantity), 2)
                else:
                    rec.liter_per_km_rate = 0

    @api.depends('tank_id.use_ids')
    def compute_last_quantity(self):
        for rec in self:
            rec.last_quantity = 0
            dates = [use.datetime for use in rec.tank_id.use_ids if use.datetime]
            if dates:
                last_date = rec.tank_id.use_ids.filtered(lambda u: u.datetime == max(dates))
                rec.last_quantity = last_date.quantity
