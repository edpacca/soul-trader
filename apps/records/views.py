from datetime import date, datetime
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.template.loader import render_to_string

from .models import PurchaseRecord, ReportPreset, SalesRecord, Source
from .services.aggregation import AggregationService
from .services.export_service import export_records_as_csv
from .services.presets import resolve_time_window

ALLOWED_PAGE_SIZES = [25, 50, 100]
DEFAULT_PAGE_SIZE = 25

SALES_COLUMNS = [
    # Date and Source filters are hardcoded so they don't have filter properties
    {"field": "date",          "label": "Date"},
    {"field": "order_id",     "label": "Order ID", "filter": "text"},
    {"field": "item_name",     "label": "Item", "filter": "text", "placeholder": "e.g. Plains, Swamp..."},
    {"field": "quantity",      "label": "Quantity"},
    {"field": "unit_price",    "label": "Unit Price"},
    {"field": "total_price",   "label": "Total Price", "filter": "num_range"},
    {"field": "shipping_cost", "label": "Shipping"},
    {"field": "source",        "label": "Source"},
    {"field": "commission_cost","label": "Commission", "has_toggle": True  },
    {"field": "post_code",     "label": "Post Code", "filter": "text", "has_toggle": True},
    {"field": "currency",      "label": "Currency", "has_toggle": True},
    {"field": "notes",         "label": "Notes", "filter": "text"},
]

PURCHASES_COLUMNS = [
    # Date and Source filters are hardcoded so they don't have filter properties
    {"field": "date",          "label": "Date"},
    {"field": "order_id",     "label": "Order ID", "filter": "text"},
    {"field": "item_name",     "label": "Item", "filter": "text"},
    {"field": "quantity",      "label": "Quantity"},
    {"field": "unit_price",    "label": "Unit Price"},
    {"field": "total_price",   "label": "Total Price", "filter": "num_range"},
    {"field": "shipping_cost", "label": "Shipping"},
    {"field": "source",        "label": "Source"},
    {"field": "currency",      "label": "Currency", "has_toggle": True},
    {"field": "notes",         "label": "Notes", "filter": "text"},
]

RECORD_CONFIG = {
    "sales": {
        "model":           SalesRecord,
        "columns":         SALES_COLUMNS,
        "get_records":        AggregationService.get_sales,
        "get_column_totals":  AggregationService.get_sales_column_totals,
        "report_type":     "sales",
        "page_title":      "Sales Records",
        "section_heading": "Sales",
        "detail_url_name": "records:sales_detail",
        "filter_prefix":   "sales",
        "table_id":        "sales-table",
        "pdf_template":    "records/pdf_sales.html",
        "pdf_filename":    "sales_report.pdf",
    },
    "purchases": {
        "model":           PurchaseRecord,
        "columns":         PURCHASES_COLUMNS,
        "get_records":        AggregationService.get_purchases,
        "get_column_totals":  AggregationService.get_column_totals,
        "report_type":     "purchases",
        "page_title":      "Purchases Records",
        "section_heading": "Purchases",
        "detail_url_name": "records:purchases_detail",
        "filter_prefix":   "purchases",
        "table_id":        "purchases-table",
        "pdf_template":    "records/pdf_purchases.html",
        "pdf_filename":    "purchases_report.pdf",
    },
}


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
    start_date = _parse_date(request.GET.get("start_date", ""))
    end_date = _parse_date(request.GET.get("end_date", ""))

    summary = AggregationService.get_summary(start_date, end_date)

    params = []
    if start_date is not None:
        params.append(f"start_date={start_date.isoformat()}")
    if end_date is not None:
        params.append(f"end_date={end_date.isoformat()}")
    qs = ("?" + "&".join(params)) if params else ""

    context = {
        "start_date": start_date.isoformat() if start_date else "",
        "end_date": end_date.isoformat() if end_date else "",
        "summary": summary,
        "sales_detail_url": "/sales/" + qs,
        "purchases_detail_url": "/purchases/" + qs,
        "presets": ReportPreset.objects.filter(report_type="combined"),
    }
    return render(request, "records/dashboard.html", context)


def _record_detail(request, record_type_key):
    cfg = RECORD_CONFIG[record_type_key]
    start_date = _parse_date(request.GET.get("start_date", ""))
    end_date   = _parse_date(request.GET.get("end_date", ""))
    page_size  = _parse_page_size(request)
    source_ids = [int(s) for s in request.GET.getlist("source_ids") if s.isdigit()]
    sort_params  = _extract_sort_params(request, cfg["filter_prefix"])
    filters      = _extract_filter_params(request, _parse_filter_names(cfg["columns"]))
    query_kwargs = {**filters, **sort_params, "source_ids": source_ids}
    qs            = cfg["get_records"](start_date, end_date, **query_kwargs)
    column_totals = cfg["get_column_totals"](qs)
    records = _get_page(Paginator(qs, page_size), request.GET.get("page"))
    context = {
        "start_date":          start_date.isoformat() if start_date else "",
        "end_date":            end_date.isoformat() if end_date else "",
        "filters":             filters,
        "records":             records,
        "column_totals":       column_totals,
        "page_size":           page_size,
        "allowed_page_sizes":  ALLOWED_PAGE_SIZES,
        "sort_field":          sort_params["sort_field"],
        "sort_order":          sort_params["sort_order"],
        "page_title":          cfg["page_title"],
        "record_type":         cfg["report_type"],
        "section_heading":     cfg["section_heading"],
        "detail_url":          reverse(cfg["detail_url_name"]),
        "filter_prefix":       cfg["filter_prefix"],
        "table_id":            cfg["table_id"],
        "columns":             cfg["columns"],
        "presets":             ReportPreset.objects.filter(report_type=cfg["report_type"]),
        "all_sources":         Source.objects.all(),
        "selected_source_ids": source_ids,
        **_build_year_range(),
    }
    return render(request, "records/detail.html", context)


def sales_detail(request):
    return _record_detail(request, "sales")


def purchases_detail(request):
    return _record_detail(request, "purchases")


def _update_note(request, record_id, record_type_key):
    record = get_object_or_404(RECORD_CONFIG[record_type_key]["model"], pk=record_id)
    record.notes = request.POST.get("notes", "")[:255]
    record.save(update_fields=["notes"])
    return JsonResponse({"id": record.id, "notes": record.notes})


def _delete_note(request, record_id, record_type_key):
    record = get_object_or_404(RECORD_CONFIG[record_type_key]["model"], pk=record_id)
    record.notes = ""
    record.save(update_fields=["notes"])
    return JsonResponse({"id": record.id, "notes": ""})


@require_POST
def update_sales_note(request, record_id):
    return _update_note(request, record_id, "sales")


@require_http_methods(["DELETE"])
def delete_sales_note(request, record_id):
    return _delete_note(request, record_id, "sales")


@require_POST
def update_purchase_note(request, record_id):
    return _update_note(request, record_id, "purchases")


@require_http_methods(["DELETE"])
def delete_purchase_note(request, record_id):
    return _delete_note(request, record_id, "purchases")


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
    if settings.DEBUG or settings.TESTING:
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


def _record_pdf_export(request, record_type_key):
    cfg = RECORD_CONFIG[record_type_key]
    start_date = _parse_date(request.GET.get("start_date", ""))
    end_date   = _parse_date(request.GET.get("end_date", ""))
    source_ids = [int(s) for s in request.GET.getlist("source_ids") if s.isdigit()]
    sort_params  = _extract_sort_params(request, cfg["filter_prefix"])
    filters      = _extract_filter_params(request, _parse_filter_names(cfg["columns"]))
    query_kwargs = {**filters, **sort_params, "source_ids": source_ids}
    qs            = cfg["get_records"](start_date, end_date, **query_kwargs)
    column_totals = cfg["get_column_totals"](qs)
    columns = _parse_columns(request.GET.get("columns", ""), cfg["columns"])
    context = {
        "records":       qs,
        "column_totals": column_totals,
        "columns":       columns,
        "start_date":    start_date.isoformat() if start_date else "All",
        "end_date":      end_date.isoformat() if end_date else "All",
        "generated_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    content, content_type_str = _render_pdf(cfg["pdf_template"], context)
    content_type = "text/html" if content_type_str == "html" else "application/pdf"
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{cfg["pdf_filename"]}"'
    return response


def sales_pdf_export(request):
    return _record_pdf_export(request, "sales")


def purchases_pdf_export(request):
    return _record_pdf_export(request, "purchases")


@login_required
def export_csv(request):
    table = request.GET.get("table", "all")
    record_type_map = {
        "sales": "sales",
        "purchases": "purchase",
        "all": "all",
    }
    record_type = record_type_map.get(table, "all")
    try:
        csv_content = export_records_as_csv(record_type)
    except Exception as e:
        messages.error(request, f"CSV export failed: {e}")
        return redirect("records:dashboard")

    today = date.today().isoformat()
    response = HttpResponse(csv_content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="soultrader_export_{table}_{today}.csv"'
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
        "total_commission": sales_summary["total_commission"],
        "total_sales_shipping":sales_summary["total_sales_shipping"],
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

    content, content_type_str = _render_pdf("records/pdf_business.html", context)
    content_type = "text/html" if content_type_str == "html" else "application_pdf"
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = 'attachment; filename="business_report.pdf"'
    return response
