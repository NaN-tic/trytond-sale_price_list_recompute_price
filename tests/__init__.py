# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

try:
    from trytond.modules.sale_price_list_recompute_price.test_sale_price_list_recompute_price import (
        suite)
except ImportError:
    from .test_sale_price_list_recompute_price import suite

__all__ = ['suite']
