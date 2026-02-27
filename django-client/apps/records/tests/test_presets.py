from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.records.models import ReportPreset, SalesRecord, PurchaseRecord
from apps.records.services.presets import resolve_time_window


class TestReportPresetModel(TestCase):
    def test_create_sales_preset(self):
        preset = ReportPreset.objects.create(
            name="Weekly Sales",
            report_type="sales",
            time_window="last_7_days",
        )
        self.assertEqual(preset.name, "Weekly Sales")
        self.assertEqual(preset.report_type, "sales")
        self.assertEqual(preset.time_window, "last_7_days")
        self.assertIsNotNone(preset.created_at)

    def test_create_purchases_preset(self):
        preset = ReportPreset.objects.create(
            name="Monthly Purchases",
            report_type="purchases",
            time_window="last_30_days",
        )
        self.assertEqual(preset.report_type, "purchases")
        self.assertEqual(preset.time_window, "last_30_days")

    def test_create_combined_preset(self):
        preset = ReportPreset.objects.create(
            name="Year Overview",
            report_type="combined",
            time_window="this_year",
        )
        self.assertEqual(preset.report_type, "combined")
        self.assertEqual(preset.time_window, "this_year")

    def test_str_representation(self):
        preset = ReportPreset.objects.create(
            name="Test Preset",
            report_type="sales",
            time_window="all_time",
        )
        self.assertIn("Test Preset", str(preset))
        self.assertIn("Sales", str(preset))
        self.assertIn("All Time", str(preset))


class TestResolveTimeWindow(TestCase):
    @patch("apps.records.services.presets.date")
    def test_last_30_days(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 26)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        start, end = resolve_time_window("last_30_days")
        self.assertEqual(start, date(2026, 1, 27))
        self.assertEqual(end, date(2026, 2, 26))

    @patch("apps.records.services.presets.date")
    def test_last_7_days(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 26)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        start, end = resolve_time_window("last_7_days")
        self.assertEqual(start, date(2026, 2, 19))
        self.assertEqual(end, date(2026, 2, 26))

    @patch("apps.records.services.presets.date")
    def test_this_month(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 26)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        start, end = resolve_time_window("this_month")
        self.assertEqual(start, date(2026, 2, 1))
        self.assertEqual(end, date(2026, 2, 26))

    @patch("apps.records.services.presets.date")
    def test_this_year(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 26)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        start, end = resolve_time_window("this_year")
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 2, 26))

    def test_all_time(self):
        start, end = resolve_time_window("all_time")
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_unknown_window_returns_none(self):
        start, end = resolve_time_window("unknown_value")
        self.assertIsNone(start)
        self.assertIsNone(end)


class TestPresetRunView(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.records.views.resolve_time_window")
    def test_run_sales_preset_redirects_to_sales_pdf(self, mock_resolve):
        mock_resolve.return_value = (date(2026, 1, 27), date(2026, 2, 26))
        preset = ReportPreset.objects.create(
            name="Sales 30d",
            report_type="sales",
            time_window="last_30_days",
        )
        url = reverse("records:preset_run", args=[preset.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/sales/pdf/", response["Location"])
        self.assertIn("start_date=2026-01-27", response["Location"])
        self.assertIn("end_date=2026-02-26", response["Location"])

    @patch("apps.records.views.resolve_time_window")
    def test_run_combined_preset_redirects_to_business_pdf(self, mock_resolve):
        mock_resolve.return_value = (date(2026, 1, 1), date(2026, 2, 26))
        preset = ReportPreset.objects.create(
            name="Business Year",
            report_type="combined",
            time_window="this_year",
        )
        url = reverse("records:preset_run", args=[preset.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/business/pdf/", response["Location"])

    @patch("apps.records.views.resolve_time_window")
    def test_run_purchases_preset_redirects_to_purchases_pdf(self, mock_resolve):
        mock_resolve.return_value = (date(2026, 2, 19), date(2026, 2, 26))
        preset = ReportPreset.objects.create(
            name="Purchases 7d",
            report_type="purchases",
            time_window="last_7_days",
        )
        url = reverse("records:preset_run", args=[preset.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/purchases/pdf/", response["Location"])

    @patch("apps.records.views.resolve_time_window")
    def test_run_all_time_preset_no_date_params(self, mock_resolve):
        mock_resolve.return_value = (None, None)
        preset = ReportPreset.objects.create(
            name="All Time Sales",
            report_type="sales",
            time_window="all_time",
        )
        url = reverse("records:preset_run", args=[preset.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/sales/pdf/", response["Location"])
        self.assertNotIn("start_date", response["Location"])
        self.assertNotIn("end_date", response["Location"])


class TestPresetDeleteView(TestCase):
    def setUp(self):
        self.client = Client()

    def test_delete_preset_removes_from_db(self):
        preset = ReportPreset.objects.create(
            name="To Delete",
            report_type="sales",
            time_window="last_7_days",
        )
        self.assertEqual(ReportPreset.objects.count(), 1)
        url = reverse("records:preset_delete", args=[preset.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReportPreset.objects.count(), 0)

    def test_delete_requires_post(self):
        preset = ReportPreset.objects.create(
            name="No GET Delete",
            report_type="sales",
            time_window="last_7_days",
        )
        url = reverse("records:preset_delete", args=[preset.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(ReportPreset.objects.count(), 1)


class TestPresetCreateView(TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_preset_saves_to_db(self):
        url = reverse("records:preset_create")
        response = self.client.post(url, {
            "name": "New Preset",
            "report_type": "sales",
            "time_window": "last_30_days",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReportPreset.objects.count(), 1)
        preset = ReportPreset.objects.first()
        self.assertEqual(preset.name, "New Preset")
        self.assertEqual(preset.report_type, "sales")
        self.assertEqual(preset.time_window, "last_30_days")

    def test_create_form_loads(self):
        url = reverse("records:preset_create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "records/report_preset_form.html")

    def test_create_with_missing_name_shows_error(self):
        url = reverse("records:preset_create")
        response = self.client.post(url, {
            "name": "",
            "report_type": "sales",
            "time_window": "last_30_days",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ReportPreset.objects.count(), 0)


class TestPresetListView(TestCase):
    def setUp(self):
        self.client = Client()

    def test_preset_list_loads(self):
        url = reverse("records:preset_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "records/reports.html")

    def test_preset_list_groups_by_type(self):
        ReportPreset.objects.create(name="S1", report_type="sales", time_window="last_7_days")
        ReportPreset.objects.create(name="P1", report_type="purchases", time_window="last_30_days")
        url = reverse("records:preset_list")
        response = self.client.get(url)
        self.assertContains(response, "S1")
        self.assertContains(response, "P1")


class TestReportControlsPartial(TestCase):
    """Tests for the _report_controls.html reusable template include."""

    def setUp(self):
        self.client = Client()

    def test_dashboard_has_generate_report_button(self):
        url = reverse("records:dashboard")
        response = self.client.get(url)
        self.assertContains(response, "Generate Report")
        self.assertContains(response, 'id="generate-report-btn"')

    def test_sales_detail_has_generate_report_button(self):
        url = reverse("records:sales_detail")
        response = self.client.get(url)
        self.assertContains(response, "Generate Report")
        self.assertContains(response, 'id="generate-report-btn"')

    def test_purchases_detail_has_generate_report_button(self):
        url = reverse("records:purchases_detail")
        response = self.client.get(url)
        self.assertContains(response, "Generate Report")
        self.assertContains(response, 'id="generate-report-btn"')

    def test_dashboard_has_current_filters_as_first_option(self):
        url = reverse("records:dashboard")
        response = self.client.get(url)
        self.assertContains(response, '<option value="current">Current Filters</option>')

    def test_sales_detail_has_current_filters_as_first_option(self):
        url = reverse("records:sales_detail")
        response = self.client.get(url)
        self.assertContains(response, '<option value="current">Current Filters</option>')

    def test_purchases_detail_has_current_filters_as_first_option(self):
        url = reverse("records:purchases_detail")
        response = self.client.get(url)
        self.assertContains(response, '<option value="current">Current Filters</option>')

    def test_report_controls_renders_with_presets(self):
        preset = ReportPreset.objects.create(
            name="Sales Weekly",
            report_type="sales",
            time_window="last_7_days",
        )
        url = reverse("records:sales_detail")
        response = self.client.get(url)
        self.assertContains(response, "Sales Weekly")
        self.assertContains(response, f'<option value="{preset.id}">Sales Weekly</option>')

    def test_report_controls_renders_without_presets(self):
        url = reverse("records:sales_detail")
        response = self.client.get(url)
        self.assertContains(response, 'id="report-preset-select"')
        self.assertContains(response, '<option value="current">Current Filters</option>')
        # The select should only contain the "Current Filters" option
        content = response.content.decode()
        select_start = content.index('id="report-preset-select"')
        select_end = content.index('</select>', select_start)
        select_html = content[select_start:select_end]
        self.assertEqual(select_html.count('<option'), 1)

    def test_dashboard_report_controls_uses_combined_report_type(self):
        url = reverse("records:dashboard")
        response = self.client.get(url)
        self.assertContains(response, "var reportType = 'combined';")

    def test_sales_report_controls_uses_sales_report_type(self):
        url = reverse("records:sales_detail")
        response = self.client.get(url)
        self.assertContains(response, "var reportType = 'sales';")

    def test_purchases_report_controls_uses_purchases_report_type(self):
        url = reverse("records:purchases_detail")
        response = self.client.get(url)
        self.assertContains(response, "var reportType = 'purchases';")

    def test_report_controls_only_shows_matching_presets(self):
        ReportPreset.objects.create(
            name="Sales Preset", report_type="sales", time_window="last_7_days",
        )
        ReportPreset.objects.create(
            name="Purchases Preset", report_type="purchases", time_window="last_30_days",
        )
        url = reverse("records:sales_detail")
        response = self.client.get(url)
        self.assertContains(response, "Sales Preset")
        self.assertNotContains(response, "Purchases Preset")


class TestDashboardPresetsContext(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_includes_combined_presets(self):
        ReportPreset.objects.create(
            name="Combined Preset",
            report_type="combined",
            time_window="this_year",
        )
        ReportPreset.objects.create(
            name="Sales Only",
            report_type="sales",
            time_window="last_7_days",
        )
        url = reverse("records:dashboard")
        response = self.client.get(url)
        presets = list(response.context["presets"])
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0].name, "Combined Preset")
        self.assertEqual(presets[0].report_type, "combined")


class TestSalesDetailPresetsContext(TestCase):
    def setUp(self):
        self.client = Client()

    def test_sales_detail_includes_sales_presets(self):
        ReportPreset.objects.create(
            name="Sales Preset",
            report_type="sales",
            time_window="last_30_days",
        )
        ReportPreset.objects.create(
            name="Purchases Preset",
            report_type="purchases",
            time_window="last_7_days",
        )
        url = reverse("records:sales_detail")
        response = self.client.get(url)
        presets = list(response.context["presets"])
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0].name, "Sales Preset")
        self.assertEqual(presets[0].report_type, "sales")


class TestPurchasesDetailPresetsContext(TestCase):
    def setUp(self):
        self.client = Client()

    def test_purchases_detail_includes_purchases_presets(self):
        ReportPreset.objects.create(
            name="Purchases Preset",
            report_type="purchases",
            time_window="all_time",
        )
        ReportPreset.objects.create(
            name="Combined Preset",
            report_type="combined",
            time_window="this_month",
        )
        url = reverse("records:purchases_detail")
        response = self.client.get(url)
        presets = list(response.context["presets"])
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0].name, "Purchases Preset")
        self.assertEqual(presets[0].report_type, "purchases")
