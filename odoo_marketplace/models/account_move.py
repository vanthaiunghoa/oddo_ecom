# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# License URL : https://store.webkul.com/license.html/
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################

from odoo import models, fields, api, _
from lxml import etree

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    seller_invoice_number = fields.Char(
        string='Seller Invoice Number', readonly=True, states={'draft': [('readonly', False)]}, translate=True)
    is_seller = fields.Boolean(string="Seller?", related="partner_id.seller")
    seller_payment_ids = fields.One2many("seller.payment", "invoice_id", string="Seller Payment")
    mp_seller_bill = fields.Boolean("MP Seller Bill")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        context = self._context

        res = super(AccountMove, self).fields_view_get(
            view_id, view_type, toolbar, submenu)
        doc = etree.XML(res['arch'])
        if context.get('type') in ('in_invoice', 'in_refund') and context.get('is_seller') is True:
            partner_string = _('Seller')
            partner_ref_string = _('Seller Reference')
            for node in doc.xpath("//field[@name='reference']"):
                node.set('invisible', '0')
                node.set('string', partner_ref_string)
            for node in doc.xpath("//field[@name='partner_id']"):
                node.set('string', partner_string)
                node.set('domain', "[('seller','=',True)]")

        res['arch'] = etree.tostring(doc)
        return res

    def mp_post_action_invoice_paid(self):
        self.create_seller_invoice_new()
        for rec in self:
            if rec.move_type in ['in_invoice', 'in_refund']:
                seller_payment = self.env["seller.payment"].search(
                    [("invoice_id", "=", rec.id)])
                if seller_payment and seller_payment.payment_mode == "seller_payment" and rec.payment_state == "paid":
                    seller_payment.write({'state': "posted"})

    @api.model
    def calculate_commission(self, list_price, seller_id):
        seller_obj = self.env["res.partner"].browse(seller_id)
        commission = seller_obj.get_seller_global_fields('commission')
        comm_factor = (list_price * (commission / 100.0))
        price_unit = list_price - comm_factor
        return price_unit

    def create_seller_invoice_new(self):
        for invoice_obj in self:
            sellers = {"seller_ids": {}}
            if invoice_obj.move_type in ['out_invoice', 'out_refund']:
                for invoice_line_obj in invoice_obj.invoice_line_ids:
                    seller_id = invoice_line_obj.product_id.marketplace_seller_id.id if invoice_line_obj.product_id.marketplace_seller_id else False
                    if seller_id:
                        seller_amount = self.calculate_commission(invoice_line_obj.price_total, seller_id)
                        invoice_line_obj.seller_commission = invoice_line_obj.price_total - seller_amount
                        invoice_line_obj.update_seller_admin_amount(seller_amount)
                        if sellers["seller_ids"].get(seller_id, False):
                            # ADD all product
                            sellers["seller_ids"][seller_id]["invoice_line_payment"].append(seller_amount)
                            sellers["seller_ids"][seller_id]["invoice_line_ids"].append(invoice_line_obj.id)
                        else:
                            sellers["seller_ids"].update({
                                    seller_id : {
                                        "invoice_line_payment": [seller_amount],
                                        "invoice_line_ids": [invoice_line_obj.id],
                                    }
                                }
                            )
                sellers.update({
                    "invoive_type": invoice_obj.move_type,
                    "invoice_id": invoice_obj.id,
                    "invoice_currency": invoice_obj.currency_id,
                    "payment_mode": "order_paid" if invoice_obj.move_type == "out_invoice" else "order_refund",
                    "description": _("Order Invoice Payment") if invoice_obj.move_type == "out_invoice" else _("Order Invoice Refund"),
                    "payment_type": "cr" if invoice_obj.move_type == "out_invoice" else "dr",
                    "state": "draft",
                    # "memo": invoice_obj.origin or invoice_obj.name, #13
                    "memo": invoice_obj.name,
                })
                self.create_seller_payment_new(sellers)

    @api.model
    def create_seller_payment_new(self, sellers_dict):
        for seller_id in list(sellers_dict.get("seller_ids")):
            search_domain = [
                ("payment_type", "=", "cr"),
                ("payment_mode", "=", "order_paid"),
                ("memo", "=", sellers_dict.get("memo")),
                ("seller_id", "=",  seller_id)
            ]
            try:
                seller_payment_obj = self.env["seller.payment"].search(search_domain, limit=1)
                if seller_payment_obj:
                    seller_payment_obj.write({"invoice_id": sellers_dict.get("invoice_id")})
                    sellers_dict["seller_ids"].pop(seller_id)
            except Exception as e:
                _logger.info("~~~~~~~~~~Exception~~~~~~~~%r~~~~~~~~~~~~~~~~~",e)
                pass

        if sellers_dict:
            vals = {
                "invoice_id": sellers_dict["invoice_id"],
                "payment_type": sellers_dict["payment_type"],
                "payment_mode": sellers_dict["payment_mode"],
                "description": sellers_dict["description"],
                "memo": sellers_dict["memo"],
                "state": "confirm"
            }
            invoice_currency = sellers_dict["invoice_currency"]
            for seller in sellers_dict["seller_ids"].keys():
                payment_method_ids = self.env[
                    "res.partner"].browse(seller).payment_method.ids
                if payment_method_ids:
                    payment_method = payment_method_ids[0]
                else:
                    payment_method = False
                vals.update({"seller_id": seller})
                vals.update({"payment_method": payment_method})
                total_amount = 0
                for amount in sellers_dict["seller_ids"][seller]["invoice_line_payment"]:
                    total_amount += amount
                mp_currency_obj = self.env["res.currency"].browse(self.env['ir.default'].get('res.config.settings', 'mp_currency_id')) or self.env.user.currency_id
                vals.update({
                    "invoiced_amount": total_amount,
                    "payable_amount": invoice_currency.compute(total_amount, mp_currency_obj),
                    "invoice_line_ids": [(6, 0,sellers_dict["seller_ids"][seller]["invoice_line_ids"])],
                })
                seller_payment_id = self.env['seller.payment'].create(vals)

    def post(self):
        not_paid_invoices = self.filtered(lambda move: move.is_invoice(include_receipts=True) and move.payment_state not in ('paid', 'in_payment'))
        result = super(AccountMove, self).post()
        not_paid_invoices.filtered(lambda move: move.payment_state in ('paid', 'in_payment')).mp_post_action_invoice_paid()
        return result

class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    def update_seller_admin_amount(self, seller_amount):
        self.ensure_one()
        sol_id = self.sale_line_ids[0] if self.sale_line_ids else False
        if sol_id:
            sol_id.write({
                'seller_amount' : seller_amount,
                'admin_commission' : self.seller_commission,
            })

    seller_commission = fields.Float("Marketplace Commission", readonly=True)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_seller_payment = fields.Boolean("Seller Payment?")
