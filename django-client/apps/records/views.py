from datetime import date, timedelta

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import render

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


def dashboard(request):
    start_date_str = request.GET.get("start_date", "")
    end_date_str = request.GET.get("end_date", "")

    today = date.today()
    default_start = today - timedelta(days=30)

    try:
        start_date = date.fromisoformat(start_date_str) if start_date_str else default_start
    except ValueError:
        start_date = default_start

    try:
        end_date = date.fromisoformat(end_date_str) if end_date_str else today
    except ValueError:
        end_date = today

    try:
        page_size = int(request.GET.get("page_size", DEFAULT_PAGE_SIZE))
    except (ValueError, TypeError):
        page_size = DEFAULT_PAGE_SIZE
    if page_size not in ALLOWED_PAGE_SIZES:
        page_size = DEFAULT_PAGE_SIZE

    sync_filters = request.GET.get("sync_filters", "") == "on"

    sales_filters = _extract_filter_params(request, "sales")
    purchases_filters = _extract_filter_params(request, "purchases")

    if sync_filters:
        if any(sales_filters.values()) and not any(purchases_filters.values()):
            purchases_filters = dict(sales_filters)
        elif any(purchases_filters.values()) and not any(sales_filters.values()):
            sales_filters = dict(purchases_filters)

    sales_sort = _extract_sort_params(request, "sales")
    purchases_sort = _extract_sort_params(request, "purchases")

    sales_kwargs = {**sales_filters, **sales_sort}
    purchases_kwargs = {**purchases_filters, **purchases_sort}

    summary = AggregationService.get_summary(
        start_date,
        end_date,
        sales_filters=sales_filters,
        purchases_filters=purchases_filters,
    )
    sales_qs = AggregationService.get_sales(start_date, end_date, **sales_kwargs)
    purchases_qs = AggregationService.get_purchases(
        start_date, end_date, **purchases_kwargs
    )

    sales_paginator = Paginator(sales_qs, page_size)
    purchases_paginator = Paginator(purchases_qs, page_size)

    sales_page = _get_page(sales_paginator, request.GET.get("sales_page"))
    purchases_page = _get_page(purchases_paginator, request.GET.get("purchases_page"))

    context = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": summary,
        "sales": sales_page,
        "purchases": purchases_page,
        "page_size": page_size,
        "allowed_page_sizes": ALLOWED_PAGE_SIZES,
        "sync_filters": sync_filters,
        "sales_filters": sales_filters,
        "purchases_filters": purchases_filters,
        "sales_sort": sales_sort["sort_field"],
        "sales_order": sales_sort["sort_order"],
        "purchases_sort": purchases_sort["sort_field"],
        "purchases_order": purchases_sort["sort_order"],
    }
    return render(request, "records/dashboard.html", context)
