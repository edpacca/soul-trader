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
            commission_cost=Decimal("0.50"),
            post_code="SW1A 1AA",
        )
        SalesRecord.objects.create(
            date=date(2024, 2, 20),
            item_name="Widget B",
            quantity=5,
            unit_price=Decimal("12.00"),
            total_price=Decimal("60.00"),
            shipping_cost=Decimal("4.00"),
            commission_cost=Decimal("0.50"),
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
            self.url, {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            }
        )
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["summary"]["total_sales"], Decimal("50.00"))
        self.assertEqual(context["summary"]["total_purchases"], Decimal("50.00"))
        self.assertEqual(context["summary"]["total_sales_shipping"], Decimal("3.50"))
        self.assertEqual(context["summary"]["total_commission"], Decimal("0.50"))
        self.assertEqual(context["summary"]["net_profit"], Decimal("-4.00"))
        self.assertEqual(context["summary"]["sales_count"], 1)
        self.assertEqual(context["summary"]["purchases_count"], 1)

    def test_dashboard_full_range(self):
        response = self.client.get(
            self.url, {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        )
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["summary"]["total_sales"], Decimal("110.00"))
        self.assertEqual(context["summary"]["total_purchases"], Decimal("100.00"))
        self.assertEqual(context["summary"]["net_profit"], Decimal("1.50"))
        self.assertEqual(context["summary"]["total_sales_shipping"], Decimal("7.50"))
        self.assertEqual(context["summary"]["total_commission"], Decimal("1.00"))
        self.assertEqual(context["summary"]["sales_count"], 2)
        self.assertEqual(context["summary"]["purchases_count"], 2)

    def test_dashboard_no_results(self):
        response = self.client.get(
            self.url, {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
            }
        )
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["summary"]["total_sales"], Decimal("0"))
        self.assertEqual(context["summary"]["total_purchases"], Decimal("0"))
        self.assertEqual(context["summary"]["total_sales_shipping"], Decimal("0"))
        self.assertEqual(context["summary"]["total_commission"], Decimal("0"))
        self.assertEqual(context["summary"]["net_profit"], Decimal("0"))

    def test_dashboard_invalid_dates_use_defaults(self):
        response = self.client.get(
            self.url, {"start_date": "not-a-date", "end_date": "also-bad"}
        )
        self.assertEqual(response.status_code, 200)

class TestPaginationBehaviour(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:sales_detail")

        for i in range(30):
            SalesRecord.objects.create(
                date=date(2024, 1, 1),
                item_name=f"Sale Item {i}",
                quantity=1,
                unit_price=Decimal("10.00"),
                total_price=Decimal("10.00"),
                shipping_cost=Decimal("1.00"),
                commission_cost=Decimal("0.50"),
                post_code="SW1A 1AA",
            )

    def test_page_1_default(self):
        response = self.client.get(
            self.url, {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        )
        page = response.context["records"]
        self.assertEqual(page.number, 1)
        self.assertEqual(len(page.object_list), 25)
        self.assertTrue(page.has_next())
        self.assertFalse(page.has_previous())

    def test_page_2(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "page": "2",
            },
        )
        page = response.context["records"]
        self.assertEqual(page.number, 2)
        self.assertEqual(len(page.object_list), 5)
        self.assertFalse(page.has_next())
        self.assertTrue(page.has_previous())

    def test_out_of_range_page_returns_last_page(self):
        response = self.client.get(
            self.url,
            {
                "page": "999",
            },
        )
        page = response.context["records"]
        self.assertEqual(page.number, page.paginator.num_pages)

    def test_invalid_page_number_returns_page_1(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "page": "abc",
            },
        )
        self.assertEqual(response.context["records"].number, 1)

    def test_date_filters_preserved_with_pagination(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "page": "1",
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
        page = response.context["records"]
        self.assertEqual(len(page.object_list), 30)
        self.assertEqual(page.paginator.num_pages, 1)

    def test_pagination_controls_shown_when_multiple_pages(self):
        response = self.client.get(
            self.url, {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        )
        self.assertContains(response, 'class="pagination"')
        self.assertContains(response, "Next")

    def test_pagination_controls_hidden_when_single_page(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "page_size": "50"
            },
        )
        self.assertNotContains(response, 'class="pagination"')


class TestSalesDetailView(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:sales_detail")

        SalesRecord.objects.create(
            date=date(2024, 1, 15),
            item_name="Widget A",
            quantity=10,
            unit_price=Decimal("5.00"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("3.50"),
            commission_cost=Decimal("0.50"),
            post_code="SW1A 1AA",
        )
        SalesRecord.objects.create(
            date=date(2024, 2, 20),
            item_name="Widget B",
            quantity=5,
            unit_price=Decimal("12.00"),
            total_price=Decimal("60.00"),
            shipping_cost=Decimal("4.00"),
            commission_cost=Decimal("0.50"),
            post_code="EC1A 1BB",
        )

    def test_sales_detail_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "records/detail.html")

    def test_sales_detail_shows_all_records_without_date(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Widget A")
        self.assertContains(response, "Widget B")

    def test_sales_detail_with_date_filter(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-01-31"}
        )
        self.assertEqual(response.status_code, 200)
        records = list(response.context["records"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].item_name, "Widget A")

    def test_sales_detail_column_totals(self):
        response = self.client.get(self.url)
        totals = response.context["column_totals"]
        self.assertEqual(totals["total_price"], Decimal("110.00"))
        self.assertEqual(totals["shipping_cost"], Decimal("7.50"))
        self.assertEqual(totals["quantity"], 15)

    def test_sales_detail_column_totals_with_date_filter(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-01-31"}
        )
        totals = response.context["column_totals"]
        self.assertEqual(totals["total_price"], Decimal("50.00"))
        self.assertEqual(totals["shipping_cost"], Decimal("3.50"))
        self.assertEqual(totals["quantity"], 10)

    def test_sales_detail_contains_postcode(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Post Code")
        self.assertContains(response, "SW1A 1AA")

    def test_sales_detail_has_postcode_toggle(self):
        response = self.client.get(self.url)
        self.assertContains(response, "toggle-post_code")

    def test_sales_detail_sorting(self):
        response = self.client.get(
            self.url, {"sales_sort": "item_name", "sales_order": "desc"}
        )
        records = list(response.context["records"])
        self.assertEqual(records[0].item_name, "Widget B")
        self.assertEqual(records[1].item_name, "Widget A")

    def test_sales_detail_no_results(self):
        response = self.client.get(
            self.url, {"start_date": "2025-01-01", "end_date": "2025-12-31"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No records found")

class TestPurchasesDetailView(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:purchases_detail")

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

    def test_purchases_detail_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "records/detail.html")

    def test_purchases_detail_shows_all_records_without_date(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Raw Material X")
        self.assertContains(response, "Raw Material Y")

    def test_purchases_detail_with_date_filter(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-01-31"}
        )
        records = list(response.context["records"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].item_name, "Raw Material X")

    def test_purchases_detail_column_totals(self):
        response = self.client.get(self.url)
        totals = response.context["column_totals"]
        self.assertEqual(totals["total_price"], Decimal("100.00"))
        self.assertEqual(totals["shipping_cost"], Decimal("8.00"))
        self.assertEqual(totals["quantity"], 150)

    def test_purchases_detail_no_postcode_column(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "Post Code")
        self.assertNotContains(response, "N1 9GU")

        response = self.client.get(self.url)
        self.assertNotContains(response, "toggle-postcode")

    def test_purchases_detail_sorting(self):
        response = self.client.get(
            self.url, {"purchases_sort": "date", "purchases_order": "asc"}
        )
        records = list(response.context["records"])
        self.assertEqual(records[0].item_name, "Raw Material X")
        self.assertEqual(records[1].item_name, "Raw Material Y")

    def test_purchases_detail_no_results(self):
        response = self.client.get(
            self.url, {"start_date": "2025-01-01", "end_date": "2025-12-31"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No records found")

    def test_purchases_detail_page_size(self):
        response = self.client.get(self.url, {"page_size": "100"})
        self.assertEqual(response.context["page_size"], 100)


class TestDashboardDetailButtons(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:dashboard")

    def test_dashboard_has_detail_buttons(self):
        response = self.client.get(self.url)
        self.assertContains(response, "View Sales Details")
        self.assertContains(response, "View Purchases Details")

    def test_detail_buttons_open_in_new_tab(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'target="_blank"')

    def test_detail_button_urls_without_dates(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["sales_detail_url"], "/sales/")
        self.assertEqual(response.context["purchases_detail_url"], "/purchases/")

    def test_detail_button_urls_with_dates(self):
        response = self.client.get(
            self.url, {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            }
        )
        self.assertEqual(
            response.context["sales_detail_url"],
            "/sales/?start_date=2024-01-01&end_date=2024-12-31"
        )
        self.assertEqual(
            response.context["purchases_detail_url"],
            "/purchases/?start_date=2024-01-01&end_date=2024-12-31"
        )

    def test_dashboard_no_default_date_filter(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["start_date"], "")
        self.assertEqual(response.context["end_date"], "")
