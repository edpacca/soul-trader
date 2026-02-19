from django.core.exceptions import ValidationError
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


class CSVFormatProfile(models.Model):
    RECORD_TYPE_CHOICES = [
        ("sales", "Sales"),
        ("purchase", "Purchase"),
    ]

    name = models.CharField(max_length=255)
    record_type = models.CharField(max_length=10, choices=RECORD_TYPE_CHOICES)
    delimiter = models.CharField(max_length=5, default=",")
    date_format = models.CharField(
        max_length=50,
        help_text="Python strftime format string, e.g. '%Y-%m-%d' or '%d/%m/%Y'",
    )
    field_mappings = models.JSONField(
        help_text="Dictionary mapping column index (as string) to model field name",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "CSV Format Profile"
        verbose_name_plural = "CSV Format Profiles"

    def __str__(self):
        return f"{self.name} ({self.get_record_type_display()})"

    def _get_model_fields(self):
        model_class = SalesRecord if self.record_type == "sales" else PurchaseRecord
        excluded = {"id", "created_at"}
        return {
            f.name
            for f in model_class._meta.get_fields()
            if hasattr(f, "column") and f.name not in excluded
        }

    def _get_required_fields(self):
        model_class = SalesRecord if self.record_type == "sales" else PurchaseRecord
        excluded = {"id", "created_at"}
        required = set()
        for f in model_class._meta.get_fields():
            if not hasattr(f, "column") or f.name in excluded:
                continue
            has_default = f.default is not models.fields.NOT_PROVIDED
            if not getattr(f, "blank", False) and not has_default:
                required.add(f.name)
        return required

    def clean(self):
        super().clean()
        if not self.field_mappings or not isinstance(self.field_mappings, dict):
            raise ValidationError(
                {"field_mappings": "field_mappings must be a non-empty dictionary."}
            )

        for key in self.field_mappings:
            if not str(key).isdigit():
                raise ValidationError(
                    {
                        "field_mappings": (
                            f"Key '{key}' is not a valid column index. "
                            f"Keys must be non-negative integer strings (e.g. '0', '1', '2')."
                        )
                    }
                )

        valid_fields = self._get_model_fields()
        mapping_values = set(self.field_mappings.values())

        invalid_fields = mapping_values - valid_fields
        if invalid_fields:
            raise ValidationError(
                {
                    "field_mappings": (
                        f"Invalid field name(s): {', '.join(sorted(invalid_fields))}. "
                        f"Valid fields are: {', '.join(sorted(valid_fields))}."
                    )
                }
            )

        required_fields = self._get_required_fields()
        missing_fields = required_fields - mapping_values
        if missing_fields:
            raise ValidationError(
                {
                    "field_mappings": (
                        f"Missing required field(s): {', '.join(sorted(missing_fields))}. "
                        f"All required fields must be present in field_mappings values."
                    )
                }
            )
