from datetime import date

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from .models import PurchaseRecord, SalesRecord
from .services.aggregation import AggregationService

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
                filters_names.append(f"{column["field"]}_min")
                filters_names.append(f"{column["field"]}_max")
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

    context = {
        "sales_start_date": sales_start.isoformat() if sales_start else "",
        "sales_end_date": sales_end.isoformat() if sales_end else "",
        "purchases_start_date": purchases_start.isoformat() if purchases_start else "",
        "purchases_end_date": purchases_end.isoformat() if purchases_end else "",
        "sync_dates": sync_dates,
        "summary": summary,
        "sales_detail_url": sales_detail_url,
        "purchases_detail_url": purchases_detail_url,
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
