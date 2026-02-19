import json

from django import forms

from .models import CSVFormatProfile, SalesRecord, PurchaseRecord


def get_model_fields_info(record_type):
    model_class = SalesRecord if record_type == "sales" else PurchaseRecord
    excluded = {"id", "created_at"}
    fields = []
    for f in model_class._meta.get_fields():
        if not hasattr(f, "column") or f.name in excluded:
            continue
        from django.db.models import fields as model_fields

        has_default = f.default is not model_fields.NOT_PROVIDED
        is_required = not getattr(f, "blank", False) and not has_default
        fields.append(
            {
                "name": f.name,
                "required": is_required,
                "type": f.get_internal_type(),
            }
        )
    return sorted(fields, key=lambda x: (not x["required"], x["name"]))


class FieldMappingsWidget(forms.Textarea):
    template_name = "admin/records/csvformatprofile/field_mappings_widget.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        sales_fields = get_model_fields_info("sales")
        purchase_fields = get_model_fields_info("purchase")
        context["widget"]["sales_fields"] = sales_fields
        context["widget"]["purchase_fields"] = purchase_fields
        context["widget"]["sales_fields_json"] = json.dumps(sales_fields)
        context["widget"]["purchase_fields_json"] = json.dumps(purchase_fields)
        return context


class CSVFormatProfileForm(forms.ModelForm):
    class Meta:
        model = CSVFormatProfile
        fields = "__all__"
        widgets = {
            "field_mappings": FieldMappingsWidget(attrs={"rows": 8, "cols": 60}),
            "delimiter": forms.TextInput(attrs={"size": 5}),
            "date_format": forms.TextInput(attrs={"size": 30}),
        }
        help_texts = {
            "delimiter": (
                "The character that separates columns in the CSV file. "
                "Common options: comma (,), semicolon (;), tab (\\t), pipe (|). "
                "Default is comma."
            ),
            "date_format": (
                "Python strftime format string for parsing dates. Examples: "
                "'%Y-%m-%d' for 2024-01-31, "
                "'%d/%m/%Y' for 31/01/2024, "
                "'%m/%d/%Y' for 01/31/2024, "
                "'%d-%b-%Y' for 31-Jan-2024, "
                "'%B %d, %Y' for January 31, 2024."
            ),
            "field_mappings": (
                "Map CSV column indices (0-based) to model fields. "
                "Required fields are marked with * and must all be mapped. "
                "Use the visual editor below or enter JSON directly, e.g.: "
                '{\"0\": \"date\", \"1\": \"item_name\", \"2\": \"quantity\", '
                '\"3\": \"unit_price\", \"4\": \"total_price\", \"5\": \"post_code\"}'
            ),
        }
