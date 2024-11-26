# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    @classmethod
    def recompute_price_by_price_list(cls, sales, price_list):
        pool = Pool()
        SaleLine = pool.get('sale.line')

        cls.write(sales, {'price_list': price_list.id if price_list else None})

        to_save = []
        for sale in sales:
            for line in sale.lines:
                if line.type != 'line':
                    continue
                line._recompute_price_list_price()
                to_save.append(line)
        if to_save:
            SaleLine.save(to_save)


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    @fields.depends('unit_price', methods=['compute_unit_price'])
    def _recompute_price_list_price(self):
        self.unit_price = self.compute_unit_price()


class RecomputePriceStart(metaclass=PoolMeta):
    __name__ = 'sale.recompute_price.start'

    price_list = fields.Many2One('product.price_list', 'Price List',
        states={
            'invisible': Eval('method') != 'price_list',
            })

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


class SaleLineDiscount(metaclass=PoolMeta):
    __name__ = 'sale.line'

    @fields.depends('discount_rate', 'discount_amount')
    def _recompute_price_list_price(self):
        super()._recompute_price_list_price()
        self.base_price = self.unit_price
        if self.discount_rate is not None:
            self.on_change_discount_rate()
        elif self.discount_amount is not None:
            self.on_change_discount_amount()
