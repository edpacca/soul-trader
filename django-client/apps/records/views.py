from datetime import date, datetime
from io import BytesIO

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.template.loader import render_to_string

from .models import PurchaseRecord, ReportPreset, SalesRecord
from .services.aggregation import AggregationService
from .services.presets import resolve_time_window

ALLOWED_PAGE_SIZES = [25, 50, 100]
DEFAULT_PAGE_SIZE = 25

SALES_COLUMNS = [
    # Date and Source filters are hardcoded so they don't have filter properties
    {"field": "date",          "label": "Date"},
    {"field": "item_name",     "label": "Item", "filter": "text", "placeholder": "e.g. Plains, Swamp..."},
    {"field": "quantity",      "label": "Quantity"},
    {"field": "unit_price",    "label": "Unit Price"},
    {"field": "total_price",   "label": "Total Price", "filter": "num_range"},
    {"field": "shipping_cost", "label": "Shipping"},
    {"field": "source",        "label": "Source"},
    {"field": "post_code",     "label": "Post Code", "filter": "text", "has_toggle": True},
    {"field": "currency",      "label": "Currency", "has_toggle": True},
    {"field": "notes",         "label": "Notes", "filter": "text"},
]

PURCHASES_COLUMNS = [
    # Date and Source filters are hardcoded so they don't have filter properties
    {"field": "date",          "label": "Date"},
    {"field": "item_name",     "label": "Item", "filter": "text"},
    {"field": "quantity",      "label": "Quantity"},
    {"field": "unit_price",    "label": "Unit Price"},
    {"field": "total_price",   "label": "Total Price", "filter": "num_range"},
    {"field": "shipping_cost", "label": "Shipping"},
    {"field": "source",        "label": "Source"},
    {"field": "currency",      "label": "Currency", "has_toggle": True},
    {"field": "notes",         "label": "Notes", "filter": "text"},
]

def _extract_filter_params(request, filters):
    return { filter_value: request.GET.get(f"{filter_value}", "") for filter_value in filters }

def _parse_filter_names(columns):
    filters_names = [
    ]
    for column in columns:
        if "filter" in column:
            if (column["filter"] == "num_range"):
                filters_names.append(f"{column['field']}_min")
                filters_names.append(f"{column['field']}_max")
            elif column["filter"] == "text":
                filters_names.append(column["field"])
    return filters_names

def _extract_sort_params(request, prefix):
    return {
        "sort_field": request.GET.get(f"{prefix}_sort", ""),
        "sort_order": request.GET.get(f"{prefix}_order", "asc"),
    }


def _get_page(paginator, page_number):
    try:
        return paginator.page(page_number)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


def _parse_date(value, default=None):
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def _build_year_range():
    """Return the min and max years that have records, for the year spinner."""
    today = date.today()
    return {
        "year_min": 2015,
        "year_max": today.year,
        "current_year": today.year,
    }


def _parse_page_size(request):
    try:
        page_size = int(request.GET.get("page_size", DEFAULT_PAGE_SIZE))
    except (ValueError, TypeError):
        page_size = DEFAULT_PAGE_SIZE
    if page_size not in ALLOWED_PAGE_SIZES:
        page_size = DEFAULT_PAGE_SIZE
    return page_size


def dashboard(request):
    sales_start_str = request.GET.get("sales_start_date", "")
    sales_end_str = request.GET.get("sales_end_date", "")
    purchases_start_str = request.GET.get("purchases_start_date", "")
    purchases_end_str = request.GET.get("purchases_end_date", "")

    sync_dates = request.GET.get("sync_dates", "") == "on"

    sales_start = _parse_date(sales_start_str)
    sales_end = _parse_date(sales_end_str)
    purchases_start = _parse_date(purchases_start_str)
    purchases_end = _parse_date(purchases_end_str)

    if sync_dates:
        if (sales_start is not None or sales_end is not None) and purchases_start is None and purchases_end is None:
            purchases_start = sales_start
            purchases_end = sales_end
        elif (purchases_start is not None or purchases_end is not None) and sales_start is None and sales_end is None:
            sales_start = purchases_start
            sales_end = purchases_end

    summary = AggregationService.get_summary(
        sales_start,
        sales_end,
    )
    summary_purchases = AggregationService.get_summary(
        purchases_start,
        purchases_end,
    )
    summary["total_purchases"] = summary_purchases["total_purchases"]
    summary["purchases_count"] = summary_purchases["purchases_count"]
    summary["net_profit"] = summary["total_sales"] - summary["total_purchases"]

    sales_detail_params = []
    if sales_start is not None:
        sales_detail_params.append(f"start_date={sales_start.isoformat()}")
    if sales_end is not None:
        sales_detail_params.append(f"end_date={sales_end.isoformat()}")
    sales_detail_url = "/sales/"
    if sales_detail_params:
        sales_detail_url += "?" + "&".join(sales_detail_params)

    purchases_detail_params = []
    if purchases_start is not None:
        purchases_detail_params.append(f"start_date={purchases_start.isoformat()}")
    if purchases_end is not None:
        purchases_detail_params.append(f"end_date={purchases_end.isoformat()}")
    purchases_detail_url = "/purchases/"
    if purchases_detail_params:
        purchases_detail_url += "?" + "&".join(purchases_detail_params)

    presets = ReportPreset.objects.filter(report_type="combined")

    context = {
        "sales_start_date": sales_start.isoformat() if sales_start else "",
        "sales_end_date": sales_end.isoformat() if sales_end else "",
        "purchases_start_date": purchases_start.isoformat() if purchases_start else "",
        "purchases_end_date": purchases_end.isoformat() if purchases_end else "",
        "sync_dates": sync_dates,
        "summary": summary,
        "sales_detail_url": sales_detail_url,
        "purchases_detail_url": purchases_detail_url,
        "presets": presets,
    }
    return render(request, "records/dashboard.html", context)


def sales_detail(request):
    start_date = _parse_date(request.GET.get("start_date", ""))
    end_date = _parse_date(request.GET.get("end_date", ""))
    page_size = _parse_page_size(request)

    sort_params = _extract_sort_params(request, "sales")
    col_filters = _parse_filter_names(SALES_COLUMNS)
    filters = _extract_filter_params(request, col_filters)
    sales_kwargs = {**filters, **sort_params}

    qs = AggregationService.get_sales(
        start_date, end_date, **sales_kwargs
    )
    column_totals = AggregationService.get_column_totals(qs)

    paginator = Paginator(qs, page_size)
    records = _get_page(paginator, request.GET.get("page"))

    presets = ReportPreset.objects.filter(report_type="sales")

    context = {
        "start_date": start_date.isoformat() if start_date else "",
        "end_date": end_date.isoformat() if end_date else "",
        "filters": filters,
        "records": records,
        "column_totals": column_totals,
        "page_size": page_size,
        "allowed_page_sizes": ALLOWED_PAGE_SIZES,
        "sort_field": sort_params["sort_field"],
        "sort_order": sort_params["sort_order"],
        "page_title": "Sales Records",
        "record_type": "sales",
        "section_heading": "Sales",
        "detail_url": reverse("records:sales_detail"),
        "filter_prefix": "sales",
        "table_id": "sales-table",
        "columns": SALES_COLUMNS,
        "presets": presets,
        **_build_year_range(),
    }
    return render(request, "records/detail.html", context)


def purchases_detail(request):
    start_date = _parse_date(request.GET.get("start_date", ""))
    end_date = _parse_date(request.GET.get("end_date", ""))
    page_size = _parse_page_size(request)

    sort_params = _extract_sort_params(request, "purchases")
    col_filters = _parse_filter_names(PURCHASES_COLUMNS)
    filters = _extract_filter_params(request, col_filters)
    purchases_kwargs = {**filters, **sort_params}

    qs = AggregationService.get_purchases(
        start_date, end_date,
        **purchases_kwargs
    )
    column_totals = AggregationService.get_column_totals(qs)

    paginator = Paginator(qs, page_size)
    records = _get_page(paginator, request.GET.get("page"))

    presets = ReportPreset.objects.filter(report_type="purchases")

    context = {
        "start_date": start_date.isoformat() if start_date else "",
        "end_date": end_date.isoformat() if end_date else "",
        "filters": filters,
        "records": records,
        "column_totals": column_totals,
        "page_size": page_size,
        "allowed_page_sizes": ALLOWED_PAGE_SIZES,
        "sort_field": sort_params["sort_field"],
        "sort_order": sort_params["sort_order"],
        "page_title": "Purchases Records",
        "record_type": "purchases",
        "section_heading": "Purchases",
        "detail_url": reverse("records:purchases_detail"),
        "filter_prefix": "purchases",
        "table_id": "purchases-table",
        "columns": PURCHASES_COLUMNS,
        "presets": presets,
        **_build_year_range(),
    }
    return render(request, "records/detail.html", context)


@require_POST
def update_sales_note(request, record_id):
    record = get_object_or_404(SalesRecord, pk=record_id)
    record.notes = request.POST.get("notes", "")[:255]
    record.save(update_fields=["notes"])
    return JsonResponse({"id": record.id, "notes": record.notes})


@require_http_methods(["DELETE"])
def delete_sales_note(request, record_id):
    record = get_object_or_404(SalesRecord, pk=record_id)
    record.notes = ""
    record.save(update_fields=["notes"])
    return JsonResponse({"id": record.id, "notes": ""})


@require_POST
def update_purchase_note(request, record_id):
    record = get_object_or_404(PurchaseRecord, pk=record_id)
    record.notes = request.POST.get("notes", "")[:255]
    record.save(update_fields=["notes"])
    return JsonResponse({"id": record.id, "notes": record.notes})


@require_http_methods(["DELETE"])
def delete_purchase_note(request, record_id):
    record = get_object_or_404(PurchaseRecord, pk=record_id)
    record.notes = ""
    record.save(update_fields=["notes"])
    return JsonResponse({"id": record.id, "notes": ""})


def preset_list(request):
    presets_by_type = {}
    for report_type, label in ReportPreset.REPORT_TYPE_CHOICES:
        qs = ReportPreset.objects.filter(report_type=report_type)
        if qs.exists():
            presets_by_type[label] = qs

    context = {
        "presets_by_type": presets_by_type,
    }
    return render(request, "records/reports.html", context)


def preset_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        report_type = request.POST.get("report_type", "")
        time_window = request.POST.get("time_window", "")

        valid_report_types = [c[0] for c in ReportPreset.REPORT_TYPE_CHOICES]
        valid_time_windows = [c[0] for c in ReportPreset.TIME_WINDOW_CHOICES]

        errors = []
        if not name:
            errors.append("Name is required.")
        if report_type not in valid_report_types:
            errors.append("Invalid report type.")
        if time_window not in valid_time_windows:
            errors.append("Invalid time window.")

        if not errors:
            ReportPreset.objects.create(
                name=name,
                report_type=report_type,
                time_window=time_window,
            )
            return redirect("records:preset_list")

        context = {
            "errors": errors,
            "name": name,
            "report_type": report_type,
            "time_window": time_window,
            "report_type_choices": ReportPreset.REPORT_TYPE_CHOICES,
            "time_window_choices": ReportPreset.TIME_WINDOW_CHOICES,
        }
        return render(request, "records/report_preset_form.html", context)

    context = {
        "report_type_choices": ReportPreset.REPORT_TYPE_CHOICES,
        "time_window_choices": ReportPreset.TIME_WINDOW_CHOICES,
        "name": "",
        "report_type": "",
        "time_window": "",
    }
    return render(request, "records/report_preset_form.html", context)


@require_POST
def preset_delete(request, preset_id):
    preset = get_object_or_404(ReportPreset, pk=preset_id)
    preset.delete()
    return redirect("records:preset_list")


def preset_run(request, preset_id):
    preset = get_object_or_404(ReportPreset, pk=preset_id)
    start_date, end_date = resolve_time_window(preset.time_window)

    url_name_map = {
        "sales": "records:sales_pdf_export",
        "purchases": "records:purchases_pdf_export",
        "combined": "records:business_pdf_export",
    }
    url_name = url_name_map[preset.report_type]
    base_url = reverse(url_name)

    params = []
    if start_date is not None:
        params.append(f"start_date={start_date.isoformat()}")
    if end_date is not None:
        params.append(f"end_date={end_date.isoformat()}")

    if params:
        base_url += "?" + "&".join(params)

    return HttpResponseRedirect(base_url)


def notes_list(request):
    record_type = request.GET.get("type", "")

    sales_notes = []
    purchase_notes = []

    if record_type != "purchases":
        for r in SalesRecord.objects.exclude(notes=""):
            sales_notes.append({
                "id": r.id,
                "item_name": r.item_name,
                "date": r.date,
                "notes": r.notes,
                "record_type": "Sales",
                "record_type_key": "sales",
            })

    if record_type != "sales":
        for r in PurchaseRecord.objects.exclude(notes=""):
            purchase_notes.append({
                "id": r.id,
                "item_name": r.item_name,
                "date": r.date,
                "notes": r.notes,
                "record_type": "Purchase",
                "record_type_key": "purchases",
            })

    all_notes = sorted(
        sales_notes + purchase_notes,
        key=lambda x: x["date"],
        reverse=True,
    )

    context = {
        "notes": all_notes,
        "current_type": record_type,
    }
    return render(request, "records/notes_list.html", context)


def _render_pdf(template_name, context):
    """Render a Django template to HTML or PDF based on DEBUG setting.

    Returns:
        tuple: (content, content_type) where content is either HTML string or PDF bytes,
               and content_type is either "html" or "pdf"
    """
    html_string = render_to_string(template_name, context)
    if settings.DEBUG:
        return html_string, "html"

    import weasyprint
    pdf_file = BytesIO()
    weasyprint.HTML(string=html_string).write_pdf(pdf_file)
    return pdf_file.getvalue(), "pdf"


def _parse_columns(columns_param, all_columns):
    """Parse a comma-separated columns param into a filtered list of column dicts."""
    if not columns_param:
        return list(all_columns)
    requested = [c.strip() for c in columns_param.split(",") if c.strip()]
    all_fields = {col["field"] for col in all_columns}
    valid = [f for f in requested if f in all_fields]
    if not valid:
        return list(all_columns)
    field_to_col = {col["field"]: col for col in all_columns}
    return [field_to_col[f] for f in valid]


def sales_pdf_export(request):
    start_date = _parse_date(request.GET.get("start_date", ""))
    end_date = _parse_date(request.GET.get("end_date", ""))

    sort_params = _extract_sort_params(request, "sales")
    col_filters = _parse_filter_names(SALES_COLUMNS)
    filters = _extract_filter_params(request, col_filters)
    sales_kwargs = {**filters, **sort_params}

    qs = AggregationService.get_sales(start_date, end_date, **sales_kwargs)
    column_totals = AggregationService.get_column_totals(qs)

    columns = _parse_columns(request.GET.get("columns", ""), SALES_COLUMNS)

    context = {
        "records": qs,
        "column_totals": column_totals,
        "columns": columns,
        "start_date": start_date.isoformat() if start_date else "All",
        "end_date": end_date.isoformat() if end_date else "All",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    content, content_type = _render_pdf("records/pdf_sales.html", context)
    if content_type == "html":
        return HttpResponse(content, content_type="text/html")
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="sales_report.pdf"'
    return response


def purchases_pdf_export(request):
    start_date = _parse_date(request.GET.get("start_date", ""))
    end_date = _parse_date(request.GET.get("end_date", ""))

    sort_params = _extract_sort_params(request, "purchases")
    col_filters = _parse_filter_names(PURCHASES_COLUMNS)
    filters = _extract_filter_params(request, col_filters)
    purchases_kwargs = {**filters, **sort_params}

    qs = AggregationService.get_purchases(start_date, end_date, **purchases_kwargs)
    column_totals = AggregationService.get_column_totals(qs)

    columns = _parse_columns(request.GET.get("columns", ""), PURCHASES_COLUMNS)

    context = {
        "records": qs,
        "column_totals": column_totals,
        "columns": columns,
        "start_date": start_date.isoformat() if start_date else "All",
        "end_date": end_date.isoformat() if end_date else "All",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    content, content_type = _render_pdf("records/pdf_purchases.html", context)
    if content_type == "html":
        return HttpResponse(content, content_type="text/html")
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="purchases_report.pdf"'
    return response


def business_pdf_export(request):
    sales_start = _parse_date(request.GET.get("sales_start_date", ""))
    sales_end = _parse_date(request.GET.get("sales_end_date", ""))
    purchases_start = _parse_date(request.GET.get("purchases_start_date", ""))
    purchases_end = _parse_date(request.GET.get("purchases_end_date", ""))

    sales_summary = AggregationService.get_summary(sales_start, sales_end)
    purchases_summary = AggregationService.get_summary(purchases_start, purchases_end)

    sales_qs = AggregationService.get_sales(sales_start, sales_end)
    purchases_qs = AggregationService.get_purchases(purchases_start, purchases_end)
    sales_totals = AggregationService.get_column_totals(sales_qs)
    purchases_totals = AggregationService.get_column_totals(purchases_qs)

    total_sales = sales_summary["total_sales"]
    total_purchases = purchases_summary["total_purchases"]
    net_profit = total_sales - total_purchases

    context = {
        "total_sales": total_sales,
        "total_purchases": total_purchases,
        "net_profit": net_profit,
        "sales_count": sales_summary["sales_count"],
        "purchases_count": purchases_summary["purchases_count"],
        "sales_totals": sales_totals,
        "purchases_totals": purchases_totals,
        "sales_start_date": sales_start.isoformat() if sales_start else "All",
        "sales_end_date": sales_end.isoformat() if sales_end else "All",
        "purchases_start_date": purchases_start.isoformat() if purchases_start else "All",
        "purchases_end_date": purchases_end.isoformat() if purchases_end else "All",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    content, content_type = _render_pdf("records/pdf_business.html", context)
    if content_type == "html":
        return HttpResponse(content, content_type="text/html")
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="business_report.pdf"'
    return response
