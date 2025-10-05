from __future__ import annotations

from prometheus_client import REGISTRY
from prometheus_client.core import GaugeMetricFamily

from store.queries import compute_store_statistics


class StoreMetricsCollector:
    """Exports aggregated in-memory store statistics for Prometheus."""

    def collect(self):  # type: ignore[override]
        stats = compute_store_statistics()
        yield GaugeMetricFamily(
            "Shop: Number of carts",
            "Number of carts in service",
            value=stats["cart_count"],
        )
        yield GaugeMetricFamily(
            "Shop: Number of items",
            "Number of items in service",
            value=stats["item_count"],
        )
        yield GaugeMetricFamily(
            "Shop: Number of deleted items",
            "Number of deleted items",
            value=stats["deleted_item_count"],
        )
        yield GaugeMetricFamily(
            "Shop: Items average price",
            "Average price of items",
            value=stats["average_item_price"],
        )
        yield GaugeMetricFamily(
            "Shop: Active items average price",
            "Average price of non-deleted items",
            value=stats["average_active_item_price"],
        )
        yield GaugeMetricFamily(
            "Shop: Average items per cart",
            "Average number of items in carts",
            value=stats["average_items_per_cart"],
        )


_collector: StoreMetricsCollector | None = None


def register_collector() -> None:
    global _collector
    if _collector is None:
        _collector = StoreMetricsCollector()
        REGISTRY.register(_collector)


register_collector()
