from django.db import models


class BaseRecord(models.Model):
    date = models.DateField()
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    post_code = models.CharField(max_length=20)
    currency = models.CharField(max_length=3, blank=True, default="GBP")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} | {self.item_name} | {self.total_price}"


class SalesRecord(BaseRecord):
    class Meta(BaseRecord.Meta):
        verbose_name = "Sales Record"
        verbose_name_plural = "Sales Records"


class PurchaseRecord(BaseRecord):
    class Meta(BaseRecord.Meta):
        verbose_name = "Purchase Record"
        verbose_name_plural = "Purchase Records"


class CSVUpload(models.Model):
    RECORD_TYPE_CHOICES = [
        ("sales", "Sales"),
        ("purchase", "Purchase"),
    ]

    file = models.FileField(upload_to="csv_uploads/")
    record_type = models.CharField(max_length=10, choices=RECORD_TYPE_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    rows_imported = models.PositiveIntegerField(default=0)
    errors = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "CSV Upload"
        verbose_name_plural = "CSV Uploads"

    def __str__(self):
        return f"{self.record_type} upload at {self.uploaded_at}"
