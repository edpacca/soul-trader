from datetime import date
from decimal import Decimal

from django.core.paginator import Page
from django.test import TestCase, Client
from django.urls import reverse

from apps.records.models import SalesRecord, PurchaseRecord


class TestDashboardView(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:dashboard")

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
            unit_price=Decimal("12.00"),
            total_price=Decimal("60.00"),
            shipping_cost=Decimal("4.00"),
            post_code="EC1A 1BB",
        )
        PurchaseRecord.objects.create(
            date=date(2024, 1, 10),
            item_name="Raw Material X",
            quantity=100,
            unit_price=Decimal("0.50"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("5.00"),
            post_code="N1 9GU",
        )
        PurchaseRecord.objects.create(
            date=date(2024, 3, 1),
            item_name="Raw Material Y",
            quantity=50,
            unit_price=Decimal("1.00"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("3.00"),
            post_code="E1 6AN",
        )

    def test_dashboard_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "records/dashboard.html")

    def test_dashboard_with_date_filter(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-01-31"}
        )
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["summary"]["total_sales"], Decimal("50.00"))
        self.assertEqual(context["summary"]["total_purchases"], Decimal("50.00"))
        self.assertEqual(context["summary"]["net_profit"], Decimal("0.00"))
        self.assertEqual(context["summary"]["sales_count"], 1)
        self.assertEqual(context["summary"]["purchases_count"], 1)

    def test_dashboard_full_range(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["summary"]["total_sales"], Decimal("110.00"))
        self.assertEqual(context["summary"]["total_purchases"], Decimal("100.00"))
        self.assertEqual(context["summary"]["net_profit"], Decimal("10.00"))
        self.assertEqual(context["summary"]["sales_count"], 2)
        self.assertEqual(context["summary"]["purchases_count"], 2)

    def test_dashboard_no_results(self):
        response = self.client.get(
            self.url, {"start_date": "2025-01-01", "end_date": "2025-12-31"}
        )
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["summary"]["total_sales"], Decimal("0"))
        self.assertEqual(context["summary"]["total_purchases"], Decimal("0"))
        self.assertEqual(context["summary"]["net_profit"], Decimal("0"))

    def test_dashboard_invalid_dates_use_defaults(self):
        response = self.client.get(
            self.url, {"start_date": "not-a-date", "end_date": "also-bad"}
        )
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_records_in_template(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        self.assertContains(response, "Widget A")
        self.assertContains(response, "Widget B")
        self.assertContains(response, "Raw Material X")
        self.assertContains(response, "Raw Material Y")

    def test_sort_sales_by_item_name_asc(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_sort": "item_name",
                "sales_order": "asc",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        self.assertEqual(sales[0].item_name, "Widget A")
        self.assertEqual(sales[1].item_name, "Widget B")

    def test_sort_sales_by_item_name_desc(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_sort": "item_name",
                "sales_order": "desc",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        self.assertEqual(sales[0].item_name, "Widget B")
        self.assertEqual(sales[1].item_name, "Widget A")

    def test_sort_purchases_by_date_asc(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "purchases_sort": "date",
                "purchases_order": "asc",
            },
        )
        self.assertEqual(response.status_code, 200)
        purchases = list(response.context["purchases"])
        self.assertEqual(purchases[0].item_name, "Raw Material X")
        self.assertEqual(purchases[1].item_name, "Raw Material Y")

    def test_filter_sales_by_item_name(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_item_name": "Widget A",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Widget A")
        self.assertNotContains(response, "Widget B")

    def test_filter_sales_by_price_range(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_price_min": "55",
                "sales_price_max": "100",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0].item_name, "Widget B")

    def test_filter_sales_by_post_code(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_post_code": "SW1A",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0].item_name, "Widget A")

    def test_filter_purchases_by_item_name(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "purchases_item_name": "Material X",
            },
        )
        self.assertEqual(response.status_code, 200)
        purchases = list(response.context["purchases"])
        self.assertEqual(len(purchases), 1)
        self.assertEqual(purchases[0].item_name, "Raw Material X")

    def test_combined_filters_and_sort(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_item_name": "Widget",
                "sales_sort": "total_price",
                "sales_order": "desc",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        self.assertEqual(len(sales), 2)
        self.assertEqual(sales[0].item_name, "Widget B")
        self.assertEqual(sales[1].item_name, "Widget A")

    def test_sync_filters_copies_sales_to_purchases(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sync_filters": "on",
                "sales_item_name": "Widget",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        purchases = list(response.context["purchases"])
        self.assertEqual(len(sales), 2)
        self.assertEqual(len(purchases), 0)

    def test_sync_filters_copies_purchases_to_sales(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sync_filters": "on",
                "purchases_item_name": "Raw",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        purchases = list(response.context["purchases"])
        self.assertEqual(len(sales), 0)
        self.assertEqual(len(purchases), 2)

    def test_invalid_sort_field_ignored(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_sort": "hacked_field",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(list(response.context["sales"])), 2)

    def test_filter_state_in_context(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_item_name": "Widget",
                "sales_sort": "date",
                "sales_order": "desc",
            },
        )
        self.assertEqual(response.context["sales_filters"]["item_name"], "Widget")
        self.assertEqual(response.context["sales_sort"], "date")
        self.assertEqual(response.context["sales_order"], "desc")

    def test_sort_headers_rendered(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        self.assertContains(response, "sortable")
        self.assertContains(response, "sales_sort=date")

    def test_filter_sales_by_multiple_item_names(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_item_name": "Widget A, Widget B",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        self.assertEqual(len(sales), 2)

    def test_filter_sales_by_multiple_item_names_partial_match(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_item_name": "Widget A, Nonexistent",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0].item_name, "Widget A")

    def test_filter_multiple_item_names_combined_with_price(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_item_name": "Widget A, Widget B",
                "sales_price_min": "55",
            },
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"])
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0].item_name, "Widget B")

    def test_context_contains_page_objects(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        self.assertIsInstance(response.context["sales"], Page)
        self.assertIsInstance(response.context["purchases"], Page)

    def test_default_page_size_is_25(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        self.assertEqual(response.context["page_size"], 25)
        self.assertEqual(response.context["sales"].paginator.per_page, 25)

    def test_page_size_50(self):
        response = self.client.get(
            self.url,
            {"start_date": "2024-01-01", "end_date": "2024-12-31", "page_size": "50"},
        )
        self.assertEqual(response.context["page_size"], 50)
        self.assertEqual(response.context["sales"].paginator.per_page, 50)

    def test_page_size_100(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "page_size": "100",
            },
        )
        self.assertEqual(response.context["page_size"], 100)

    def test_invalid_page_size_falls_back_to_default(self):
        response = self.client.get(
            self.url,
            {"start_date": "2024-01-01", "end_date": "2024-12-31", "page_size": "10"},
        )
        self.assertEqual(response.context["page_size"], 25)

    def test_non_numeric_page_size_falls_back_to_default(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "page_size": "abc",
            },
        )
        self.assertEqual(response.context["page_size"], 25)

    def test_allowed_page_sizes_in_context(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["allowed_page_sizes"], [25, 50, 100])


class TestPaginationBehaviour(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:dashboard")

        for i in range(30):
            SalesRecord.objects.create(
                date=date(2024, 1, 1),
                item_name=f"Sale Item {i}",
                quantity=1,
                unit_price=Decimal("10.00"),
                total_price=Decimal("10.00"),
                shipping_cost=Decimal("1.00"),
                post_code="SW1A 1AA",
            )
        for i in range(30):
            PurchaseRecord.objects.create(
                date=date(2024, 1, 1),
                item_name=f"Purchase Item {i}",
                quantity=1,
                unit_price=Decimal("5.00"),
                total_price=Decimal("5.00"),
                shipping_cost=Decimal("1.00"),
                post_code="N1 9GU",
            )

    def test_sales_page_1_default(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        sales_page = response.context["sales"]
        self.assertEqual(sales_page.number, 1)
        self.assertEqual(len(sales_page.object_list), 25)
        self.assertTrue(sales_page.has_next())
        self.assertFalse(sales_page.has_previous())

    def test_sales_page_2(self):
        response = self.client.get(
            self.url,
            {"start_date": "2024-01-01", "end_date": "2024-12-31", "sales_page": "2"},
        )
        sales_page = response.context["sales"]
        self.assertEqual(sales_page.number, 2)
        self.assertEqual(len(sales_page.object_list), 5)
        self.assertFalse(sales_page.has_next())
        self.assertTrue(sales_page.has_previous())

    def test_purchases_page_2(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "purchases_page": "2",
            },
        )
        purchases_page = response.context["purchases"]
        self.assertEqual(purchases_page.number, 2)
        self.assertEqual(len(purchases_page.object_list), 5)

    def test_independent_pagination(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_page": "2",
                "purchases_page": "1",
            },
        )
        self.assertEqual(response.context["sales"].number, 2)
        self.assertEqual(response.context["purchases"].number, 1)

    def test_out_of_range_page_returns_last_page(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_page": "999",
            },
        )
        sales_page = response.context["sales"]
        self.assertEqual(sales_page.number, sales_page.paginator.num_pages)

    def test_invalid_page_number_returns_page_1(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_page": "abc",
            },
        )
        self.assertEqual(response.context["sales"].number, 1)

    def test_date_filters_preserved_with_pagination(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "sales_page": "1",
            },
        )
        self.assertEqual(response.context["start_date"], "2024-01-01")
        self.assertEqual(response.context["end_date"], "2024-12-31")

    def test_page_size_with_pagination(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "page_size": "50",
            },
        )
        sales_page = response.context["sales"]
        self.assertEqual(len(sales_page.object_list), 30)
        self.assertEqual(sales_page.paginator.num_pages, 1)

    def test_pagination_controls_shown_when_multiple_pages(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        self.assertContains(response, 'class="pagination"')
        self.assertContains(response, "Next")

    def test_pagination_controls_hidden_when_single_page(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "page_size": "50",
            },
        )
        self.assertNotContains(response, 'class="pagination"')
