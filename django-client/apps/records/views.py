from datetime import date

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_POST

from .models import PurchaseRecord, SalesRecord
from .services.aggregation import AggregationService

ALLOWED_PAGE_SIZES = [25, 50, 100]
DEFAULT_PAGE_SIZE = 25


def _extract_filter_params(request, prefix):
    return {
        "item_name": request.GET.get(f"{prefix}_item_name", ""),
        "price_min": request.GET.get(f"{prefix}_price_min", ""),
        "price_max": request.GET.get(f"{prefix}_price_max", ""),
        "post_code": request.GET.get(f"{prefix}_post_code", ""),
    }


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
    filters = _extract_filter_params(request, "sales")
    sales_kwargs = {**filters, **sort_params}

    qs = AggregationService.get_sales(
        start_date, end_date, **sales_kwargs
    )
    column_totals = AggregationService.get_column_totals(qs)

    paginator = Paginator(qs, page_size)
    page = _get_page(paginator, request.GET.get("page"))

    context = {
        "start_date": start_date.isoformat() if start_date else "",
        "end_date": end_date.isoformat() if end_date else "",
        "filters": filters,
        "records": page,
        "column_totals": column_totals,
        "page_size": page_size,
        "allowed_page_sizes": ALLOWED_PAGE_SIZES,
        "sort_field": sort_params["sort_field"],
        "sort_order": sort_params["sort_order"],
    }
    return render(request, "records/sales_detail.html", context)


def purchases_detail(request):
    start_date = _parse_date(request.GET.get("start_date", ""))
    end_date = _parse_date(request.GET.get("end_date", ""))
    page_size = _parse_page_size(request)

    sort_params = _extract_sort_params(request, "purchases")
    filters = _extract_filter_params(request, "purchases")
    purchases_kwargs = {**filters, **sort_params}

    qs = AggregationService.get_purchases(
        start_date, end_date,
        **purchases_kwargs
    )
    column_totals = AggregationService.get_column_totals(qs)

    paginator = Paginator(qs, page_size)
    page = _get_page(paginator, request.GET.get("page"))

    context = {
        "start_date": start_date.isoformat() if start_date else "",
        "end_date": end_date.isoformat() if end_date else "",
        "filters": filters,
        "records": page,
        "column_totals": column_totals,
        "page_size": page_size,
        "allowed_page_sizes": ALLOWED_PAGE_SIZES,
        "sort_field": sort_params["sort_field"],
        "sort_order": sort_params["sort_order"],
    }
    return render(request, "records/purchases_detail.html", context)


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
