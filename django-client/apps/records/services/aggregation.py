from datetime import date
from decimal import Decimal

from django.db.models import QuerySet, Sum

from apps.records.models import PurchaseRecord, SalesRecord


class AggregationService:
    @staticmethod
    def get_sales(start_date: date, end_date: date) -> QuerySet:
        return SalesRecord.objects.filter(date__gte=start_date, date__lte=end_date)

    @staticmethod
    def get_purchases(start_date: date, end_date: date) -> QuerySet:
        return PurchaseRecord.objects.filter(
            date__gte=start_date, date__lte=end_date
        )

    @staticmethod
    def get_summary(start_date: date, end_date: date) -> dict:
        sales_qs = AggregationService.get_sales(start_date, end_date)
        purchases_qs = AggregationService.get_purchases(start_date, end_date)

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
