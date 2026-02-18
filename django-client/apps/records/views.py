from datetime import date, timedelta

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import render

from .services.aggregation import AggregationService

ALLOWED_PAGE_SIZES = [25, 50, 100]
DEFAULT_PAGE_SIZE = 25


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

    summary = AggregationService.get_summary(start_date, end_date)
    sales_qs = AggregationService.get_sales(start_date, end_date)
    purchases_qs = AggregationService.get_purchases(start_date, end_date)

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
    }
    return render(request, "records/dashboard.html", context)


def _get_page(paginator, page_number):
    try:
        return paginator.page(page_number)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)
