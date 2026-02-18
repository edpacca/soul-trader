from datetime import date
from decimal import Decimal, InvalidOperation
from functools import reduce
from operator import or_
from typing import Optional

from django.db.models import Q, QuerySet, Sum

from apps.records.models import PurchaseRecord, SalesRecord

TOTAL_COLUMNS = ["total_price", "shipping_cost", "quantity"]

SORTABLE_FIELDS = {
    "date",
    "item_name",
    "quantity",
    "unit_price",
    "total_price",
    "shipping_cost",
    "post_code",
    "currency",
}


class AggregationService:
    @staticmethod
    def _apply_filters(
        qs: QuerySet,
        *,
        item_name: str = "",
        price_min: str = "",
        price_max: str = "",
        post_code: str = "",
    ) -> QuerySet:
        if item_name:
            terms = [t.strip() for t in item_name.split(",") if t.strip()]
            if terms:
                name_q = reduce(or_, (Q(item_name__icontains=t) for t in terms))
                qs = qs.filter(name_q)
        if price_min:
            try:
                qs = qs.filter(total_price__gte=Decimal(price_min))
            except InvalidOperation:
                pass
        if price_max:
            try:
                qs = qs.filter(total_price__lte=Decimal(price_max))
            except InvalidOperation:
                pass
        if post_code:
            qs = qs.filter(post_code__icontains=post_code)
        return qs

    @staticmethod
    def _apply_sort(
        qs: QuerySet,
        sort_field: str = "",
        sort_order: str = "asc",
    ) -> QuerySet:
        if sort_field and sort_field in SORTABLE_FIELDS:
            prefix = "-" if sort_order == "desc" else ""
            qs = qs.order_by(f"{prefix}{sort_field}")
        return qs

    @staticmethod
    def get_sales(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        *,
        item_name: str = "",
        price_min: str = "",
        price_max: str = "",
        post_code: str = "",
        sort_field: str = "",
        sort_order: str = "asc",
    ) -> QuerySet:
        qs = SalesRecord.objects.all()
        if start_date is not None:
            qs = qs.filter(date__gte=start_date)
        if end_date is not None:
            qs = qs.filter(date__lte=end_date)
        qs = AggregationService._apply_filters(
            qs,
            item_name=item_name,
            price_min=price_min,
            price_max=price_max,
            post_code=post_code,
        )
        qs = AggregationService._apply_sort(qs, sort_field, sort_order)
        return qs

    @staticmethod
    def get_purchases(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        *,
        item_name: str = "",
        price_min: str = "",
        price_max: str = "",
        post_code: str = "",
        sort_field: str = "",
        sort_order: str = "asc",
    ) -> QuerySet:
        qs = PurchaseRecord.objects.all()
        if start_date is not None:
            qs = qs.filter(date__gte=start_date)
        if end_date is not None:
            qs = qs.filter(date__lte=end_date)
        qs = AggregationService._apply_filters(
            qs,
            item_name=item_name,
            price_min=price_min,
            price_max=price_max,
            post_code=post_code,
        )
        qs = AggregationService._apply_sort(qs, sort_field, sort_order)
        return qs

    @staticmethod
    def get_column_totals(qs: QuerySet) -> dict:
        agg = qs.aggregate(
            total_price=Sum("total_price"),
            shipping_cost=Sum("shipping_cost"),
            quantity=Sum("quantity"),
        )
        return {
            "total_price": agg["total_price"] or Decimal("0"),
            "shipping_cost": agg["shipping_cost"] or Decimal("0"),
            "quantity": agg["quantity"] or 0,
        }

    @staticmethod
    def get_summary(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        *,
        sales_filters: Optional[dict] = None,
        purchases_filters: Optional[dict] = None,
    ) -> dict:
        sf = sales_filters or {}
        pf = purchases_filters or {}
        sales_qs = AggregationService.get_sales(start_date, end_date, **sf)
        purchases_qs = AggregationService.get_purchases(start_date, end_date, **pf)

        total_sales = (
            sales_qs.aggregate(total=Sum("total_price"))["total"] or Decimal("0")
        )
        total_purchases = (
            purchases_qs.aggregate(total=Sum("total_price"))["total"] or Decimal("0")
        )
        net_profit = total_sales - total_purchases

        return {
            "total_sales": total_sales,
            "total_purchases": total_purchases,
            "net_profit": net_profit,
            "sales_count": sales_qs.count(),
            "purchases_count": purchases_qs.count(),
        }
