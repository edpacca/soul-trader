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

    def test_get_sales_filter_by_item_name(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), item_name="Widget A"
        )
        self.assertEqual(sales.count(), 1)
        self.assertEqual(sales.first().item_name, "Widget A")

    def test_get_sales_filter_by_price_range(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), price_min="60", price_max="200"
        )
        self.assertEqual(sales.count(), 1)
        self.assertEqual(sales.first().item_name, "Widget B")

    def test_get_sales_filter_by_post_code(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), post_code="SW1A"
        )
        self.assertEqual(sales.count(), 1)
        self.assertEqual(sales.first().item_name, "Widget A")

    def test_get_purchases_filter_by_item_name(self):
        purchases = AggregationService.get_purchases(
            date(2024, 1, 1), date(2024, 12, 31), item_name="Raw"
        )
        self.assertEqual(purchases.count(), 1)

    def test_get_sales_sort_by_item_name_asc(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), sort_field="item_name", sort_order="asc"
        )
        names = list(sales.values_list("item_name", flat=True))
        self.assertEqual(names, ["Widget A", "Widget B"])

    def test_get_sales_sort_by_item_name_desc(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), sort_field="item_name", sort_order="desc"
        )
        names = list(sales.values_list("item_name", flat=True))
        self.assertEqual(names, ["Widget B", "Widget A"])

    def test_get_sales_sort_by_total_price(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), sort_field="total_price", sort_order="asc"
        )
        prices = list(sales.values_list("total_price", flat=True))
        self.assertEqual(prices, [Decimal("50.00"), Decimal("100.00")])

    def test_get_sales_invalid_sort_field_ignored(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), sort_field="invalid_field"
        )
        self.assertEqual(sales.count(), 2)

    def test_get_sales_invalid_price_ignored(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), price_min="not_a_number"
        )
        self.assertEqual(sales.count(), 2)

    def test_get_sales_combined_filters(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31),
            item_name="Widget",
            price_min="55",
        )
        self.assertEqual(sales.count(), 1)
        self.assertEqual(sales.first().item_name, "Widget B")

    def test_get_sales_filter_by_multiple_item_names(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), item_name="Widget A, Widget B"
        )
        self.assertEqual(sales.count(), 2)

    def test_get_sales_filter_by_multiple_item_names_partial(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), item_name="Widget A, Nonexistent"
        )
        self.assertEqual(sales.count(), 1)
        self.assertEqual(sales.first().item_name, "Widget A")

    def test_get_sales_filter_by_single_comma_separated_term(self):
        sales = AggregationService.get_sales(
            date(2024, 1, 1), date(2024, 12, 31), item_name="Widget A"
        )
        self.assertEqual(sales.count(), 1)

    def test_get_purchases_filter_by_multiple_item_names(self):
        PurchaseRecord.objects.create(
            date=date(2024, 3, 1),
            item_name="Gadget Z",
            quantity=10,
            unit_price=Decimal("2.00"),
            total_price=Decimal("20.00"),
            shipping_cost=Decimal("1.00"),
            post_code="W1 1AA",
        )
        purchases = AggregationService.get_purchases(
            date(2024, 1, 1), date(2024, 12, 31), item_name="Raw, Gadget"
        )
        self.assertEqual(purchases.count(), 2)

    def test_get_summary_with_filters(self):
        summary = AggregationService.get_summary(
            date(2024, 1, 1), date(2024, 12, 31),
            sales_filters={"item_name": "Widget A"},
        )
        self.assertEqual(summary["total_sales"], Decimal("50.00"))
        self.assertEqual(summary["sales_count"], 1)
        self.assertEqual(summary["purchases_count"], 1)
