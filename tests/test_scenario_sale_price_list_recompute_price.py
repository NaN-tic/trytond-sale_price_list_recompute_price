import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install sale_price_list_recompute_price
        config = activate_modules('sale_price_list_recompute_price')

        # Create company
        _ = create_company()
        company = get_company()

        # Create sale user
        User = Model.get('res.user')
        Group = Model.get('res.group')
        sale_user = User()
        sale_user.name = 'Sale'
        sale_user.login = 'sale'
        sale_group, = Group.find([('name', '=', 'Sales')])
        sale_user.groups.append(sale_group)
        sale_user.save()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create parties
        Party = Model.get('party.party')
        customer = Party(name='Customer')
        customer.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        product = Product()
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.salable = True
        template.list_price = Decimal('10')
        template.cost_price_method = 'fixed'
        template.account_category = account_category
        template.save()
        product.template = template
        product.cost_price = Decimal('5')
        product.save()
        service = Product()
        template = ProductTemplate()
        template.name = 'service'
        template.default_uom = unit
        template.type = 'service'
        template.salable = True
        template.list_price = Decimal('100')
        template.cost_price_method = 'fixed'
        template.account_category = account_category
        template.save()
        service.template = template
        service.cost_price = Decimal('20')
        service.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create a price list
        PriceList = Model.get('product.price_list')
        default_price_list = PriceList(name='Default')
        line = default_price_list.lines.new()
        line.formula = 'unit_price * 1.2'
        default_price_list.save()
        reduced_price_list = PriceList(name='Reduced')
        line = reduced_price_list.lines.new()
        line.formula = 'unit_price * 0.8'
        reduced_price_list.save()

        # Create a sale with default price list
        config.user = sale_user.id
        Sale = Model.get('sale.sale')
        sale = Sale()
        sale.party = customer
        sale.payment_term = payment_term
        sale.price_list = default_price_list
        sale.invoice_method = 'order'
        sale_line = sale.lines.new()
        sale_line.product = product
        sale_line.quantity = 1.0
        sale_line = sale.lines.new()
        sale_line.product = service
        sale_line.quantity = 1.0
        sale_line = sale.lines.new()
        sale_line.type = 'comment'
        sale_line.description = 'Comment'
        sale.click('quote')
        self.assertEqual(sale.untaxed_amount, Decimal('132.00'))

        # Change price list to the reduced one
        recompute = Wizard('sale.recompute_price', [sale])
        recompute.form.method = 'price_list'
        recompute.form.price_list = reduced_price_list
        recompute.execute('compute')
        sale.reload()
        self.assertEqual(sale.price_list, reduced_price_list)
        self.assertEqual(sale.untaxed_amount, Decimal('88.00'))

        product_line, service_line, _ = sale.lines
        self.assertEqual(product_line.unit_price, Decimal('8.0000'))
        self.assertEqual(service_line.unit_price, Decimal('80.0000'))

        # Change to no price list
        recompute = Wizard('sale.recompute_price', [sale])
        recompute.form.method = 'price_list'
        recompute.form.price_list = None
        recompute.execute('compute')
        sale.reload()
        sale.price_list
        self.assertEqual(sale.untaxed_amount, Decimal('110.00'))

        product_line, service_line, _ = sale.lines
        self.assertEqual(product_line.unit_price, Decimal('10.0000'))
        self.assertEqual(service_line.unit_price, Decimal('100.0000'))
