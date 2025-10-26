from prometheus_client import Counter, Gauge

carts_created_counter = Counter(
    "shop_carts_created_total", "Total number of carts created"
)
items_in_stock_gauge = Gauge(
    "shop_items_total", "Current number of non-deleted items in stock"
)
