from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.records.models import SalesRecord, PurchaseRecord
from apps.records.services.aggregation import AggregationService


class TestAggregationService(TestCase):
    def setUp(self):
        SalesRecord.objects.create(
            date=date(2024, 1, 15),
            item_name="Widget A",
            quantity=10,
            unit_price=Decimal("5.00"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("3.50"),
            post_code="SW1A 1AA",
        )
        SalesRecord.objects.create(
            date=date(2024, 2, 20),
            item_name="Widget B",
            quantity=5,
            unit_price=Decimal("20.00"),
            total_price=Decimal("100.00"),
            shipping_cost=Decimal("4.00"),
            post_code="EC1A 1BB",
        )
        PurchaseRecord.objects.create(
            date=date(2024, 1, 10),
            item_name="Raw Material",
            quantity=100,
            unit_price=Decimal("0.50"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("5.00"),
            post_code="N1 9GU",
        )

    def test_get_sales_filters_by_date(self):
        sales = AggregationService.get_sales(date(2024, 1, 1), date(2024, 1, 31))
        self.assertEqual(sales.count(), 1)

    def test_get_purchases_filters_by_date(self):
        purchases = AggregationService.get_purchases(date(2024, 1, 1), date(2024, 1, 31))
        self.assertEqual(purchases.count(), 1)

    def test_get_summary(self):
        summary = AggregationService.get_summary(date(2024, 1, 1), date(2024, 12, 31))
        self.assertEqual(summary["total_sales"], Decimal("150.00"))
        self.assertEqual(summary["total_purchases"], Decimal("50.00"))
        self.assertEqual(summary["net_profit"], Decimal("100.00"))
        self.assertEqual(summary["sales_count"], 2)
        self.assertEqual(summary["purchases_count"], 1)

    def test_get_summary_empty_range(self):
        summary = AggregationService.get_summary(date(2025, 1, 1), date(2025, 12, 31))
        self.assertEqual(summary["total_sales"], Decimal("0"))
        self.assertEqual(summary["total_purchases"], Decimal("0"))
        self.assertEqual(summary["net_profit"], Decimal("0"))
        self.assertEqual(summary["sales_count"], 0)
        self.assertEqual(summary["purchases_count"], 0)
