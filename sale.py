# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Sale', 'RecomputePriceStart', 'RecomputePrice']


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    def _recompute_price_list_price(self, line):
        pool = Pool()
        Product = pool.get('product.product')
        values = {}
        with Transaction().set_context(line._get_context_sale_price()):
            unit_price = Product.get_sale_price([line.product],
                    line.quantity or 0)[line.product.id]
            if unit_price:
                values['unit_price'] = unit_price.quantize(
                    Decimal(1) / 10 ** line.__class__.unit_price.digits[1])
                if hasattr(line, 'gross_unit_price'):
                    digits = line.__class__.gross_unit_price.digits[1]
                    if line.discount:
                        gross_unit_price = (unit_price *
                            (Decimal(1) + line.discount)).quantize(
                            Decimal(str(10 ** -digits)))
                    else:
                        gross_unit_price = (unit_price).quantize(
                            Decimal(str(10 ** -digits)))
                    values['gross_unit_price'] = gross_unit_price
        return values

    @classmethod
    def recompute_price_by_price_list(cls, sales, price_list):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        to_write = []
        cls.write(sales, {'price_list': price_list.id if price_list else None})
        for sale in sales:
                for line in sale.lines:
                    if line.type != 'line':
                        continue
                    new_values = sale._recompute_price_list_price(line)
                    if new_values:
                        to_write.extend(([line], new_values))
        if to_write:
            SaleLine.write(*to_write)


class RecomputePriceStart(metaclass=PoolMeta):
    __name__ = 'sale.recompute_price.start'

    price_list = fields.Many2One('product.price_list', 'Price List',
        states={
            'invisible': Eval('method') != 'price_list',
            },
        depends=['method'])

    @classmethod
    def __setup__(cls):
        super(RecomputePriceStart, cls).__setup__()
        price_list = ('price_list', 'Update Price List')
        if price_list not in cls.method.selection:
            cls.method.selection.append(price_list)


class RecomputePrice(metaclass=PoolMeta):
    __name__ = 'sale.recompute_price'

    def default_start(self, fields):
        pool = Pool()
        Sale = pool.get('sale.sale')
        default = super(RecomputePrice, self).default_start(fields)
        if len(Transaction().context['active_ids']) == 1:
            sale = Sale(Transaction().context['active_id'])
            if sale.price_list:
                default['price_list'] = sale.price_list.id
        return default

    def get_additional_args_price_list(self):
        return {
            'price_list': self.start.price_list,
            }
