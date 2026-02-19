import csv
import io
import json

from django import forms
from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.urls import path

from .forms import CSVFormatProfileForm
from .models import CSVFormatProfile, CSVUpload, PurchaseRecord, SalesRecord
from .services.csv_parser import DefaultCSVParser


class BaseRecordAdmin(admin.ModelAdmin):
    list_display = ("date", "item_name", "quantity", "unit_price", "total_price", "shipping_cost", "post_code", "currency")
    list_filter = ("date", "currency")
    search_fields = ("item_name", "post_code")
    readonly_fields = ("created_at",)


@admin.register(SalesRecord)
class SalesRecordAdmin(BaseRecordAdmin):
    pass


@admin.register(PurchaseRecord)
class PurchaseRecordAdmin(BaseRecordAdmin):
    pass


class CSVUploadForm(forms.ModelForm):
    class Meta:
        model = CSVUpload
        fields = "__all__"

    def clean_format_profile(self):
        profile = self.cleaned_data.get("format_profile")
        if not self.instance.pk and not profile:
            raise forms.ValidationError("A format profile is required for new uploads.")
        return profile

    def clean(self):
        cleaned_data = super().clean()
        record_type = cleaned_data.get("record_type")
        profile = cleaned_data.get("format_profile")
        if profile and record_type and profile.record_type != record_type:
            raise forms.ValidationError(
                "The selected format profile does not match the chosen record type."
            )
        return cleaned_data


@admin.register(CSVUpload)
class CSVUploadAdmin(admin.ModelAdmin):
    form = CSVUploadForm
    list_display = ("record_type", "format_profile", "uploaded_at", "rows_imported", "file")
    list_filter = ("record_type",)
    readonly_fields = ("uploaded_at", "rows_imported", "errors")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "format_profile":
            kwargs["queryset"] = CSVFormatProfile.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _get_profile_record_type_map(self):
        profiles = CSVFormatProfile.objects.filter(is_active=True).values_list(
            "id", "record_type"
        )
        return {str(pk): rt for pk, rt in profiles}

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["profile_record_type_map"] = mark_safe(
            json.dumps(self._get_profile_record_type_map())
        )
        return super().changeform_view(request, object_id, form_url, extra_context)

    class Media:
        js = ("admin/js/csv_upload_filter.js",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if not change:
            self._process_csv(request, obj)

    def _process_csv(self, request, obj):
        if obj.format_profile:
            parser = DefaultCSVParser(profile=obj.format_profile)
        else:
            parser = DefaultCSVParser()

        try:
            file_content = obj.file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            obj.errors = "File encoding error. Please upload a UTF-8 encoded CSV."
            obj.save()
            self.message_user(request, obj.errors, messages.ERROR)
            return

        records, errors = parser.parse(file_content)

        model_class = SalesRecord if obj.record_type == "sales" else PurchaseRecord
        created = 0
        for record_data in records:
            model_class.objects.create(**record_data)
            created += 1

        obj.rows_imported = created
        obj.errors = "\n".join(errors) if errors else ""
        obj.save()

        if errors:
            self.message_user(
                request,
                f"Imported {created} records with {len(errors)} error(s). Check the upload details for more info.",
                messages.WARNING,
            )
        else:
            self.message_user(
                request,
                f"Successfully imported {created} {obj.record_type} records.",
                messages.SUCCESS,
            )


@admin.register(CSVFormatProfile)
class CSVFormatProfileAdmin(admin.ModelAdmin):
    form = CSVFormatProfileForm
    list_display = ("name", "record_type", "delimiter", "is_active", "created_at", "updated_at")
    list_filter = ("record_type", "is_active")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    change_form_template = "admin/records/csvformatprofile/change_form.html"
    actions = ["duplicate_profile", "activate_profiles", "deactivate_profiles"]

    fieldsets = (
        (None, {
            "fields": ("name", "record_type", "is_active"),
        }),
        ("CSV Format Settings", {
            "fields": ("delimiter", "date_format"),
            "description": (
                "<strong>Delimiter:</strong> The character separating columns. "
                "Common options: <code>,</code> (comma), <code>;</code> (semicolon), "
                "<code>\\t</code> (tab), <code>|</code> (pipe).<br>"
                "<strong>Date format:</strong> Python strftime codes &mdash; "
                "<code>%Y</code> = 4-digit year, <code>%m</code> = 2-digit month, "
                "<code>%d</code> = 2-digit day, <code>%b</code> = abbreviated month name, "
                "<code>%B</code> = full month name.<br>"
                "Examples: <code>%Y-%m-%d</code> &rarr; 2024-01-31, "
                "<code>%d/%m/%Y</code> &rarr; 31/01/2024, "
                "<code>%m/%d/%Y</code> &rarr; 01/31/2024, "
                "<code>%d-%b-%Y</code> &rarr; 31-Jan-2024."
            ),
        }),
        ("Field Mappings", {
            "fields": ("field_mappings",),
            "description": (
                "Map each CSV column index (0-based) to a model field. "
                "Required fields are marked with <strong>*</strong> and must all be mapped "
                "for the profile to be valid."
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.action(description="Duplicate selected profiles")
    def duplicate_profile(self, request, queryset):
        duplicated = 0
        for profile in queryset:
            profile.pk = None
            profile.name = f"{profile.name} (copy)"
            profile.save()
            duplicated += 1
        self.message_user(
            request,
            f"Successfully duplicated {duplicated} profile(s).",
            messages.SUCCESS,
        )

    @admin.action(description="Activate selected profiles")
    def activate_profiles(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"Successfully activated {updated} profile(s).",
            messages.SUCCESS,
        )

    @admin.action(description="Deactivate selected profiles")
    def deactivate_profiles(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"Successfully deactivated {updated} profile(s).",
            messages.SUCCESS,
        )

    def get_urls(self):
        custom_urls = [
            path(
                "<int:profile_id>/test-csv/",
                self.admin_site.admin_view(self.test_csv_view),
                name="records_csvformatprofile_test_csv",
            ),
        ]
        return custom_urls + super().get_urls()

    def test_csv_view(self, request, profile_id):
        try:
            profile = CSVFormatProfile.objects.get(pk=profile_id)
        except CSVFormatProfile.DoesNotExist:
            return JsonResponse({"error": "Profile not found."}, status=404)

        if request.method != "POST":
            return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            return JsonResponse({"error": "No file uploaded."}, status=400)

        try:
            file_content = csv_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return JsonResponse({"error": "File encoding error. Please upload a UTF-8 encoded CSV."})

        parser = DefaultCSVParser(profile=profile)
        records, errors = parser.parse(file_content)

        if not records and errors and not any(e.startswith("Row ") for e in errors):
            return JsonResponse({"error": "; ".join(errors)})

        delimiter = profile.delimiter
        if delimiter == "\\t":
            delimiter = "\t"
        reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)
        try:
            csv_headers = next(reader)
        except StopIteration:
            csv_headers = []

        mappings = profile.field_mappings
        mapped_headers = []
        header_fields = []
        for col_index_str in sorted(mappings.keys(), key=lambda x: int(x)):
            field_name = mappings[col_index_str]
            col_index = int(col_index_str)
            csv_header = csv_headers[col_index] if col_index < len(csv_headers) else f"Column {col_index}"
            mapped_headers.append(f"{field_name} (CSV: {csv_header})")
            header_fields.append(field_name)

        preview = []
        for record in records[:10]:
            row = {}
            for field in header_fields:
                val = record.get(field, "")
                row[field] = str(val) if val is not None else ""
            preview.append(row)

        return JsonResponse({
            "headers": mapped_headers,
            "header_fields": header_fields,
            "preview": preview,
            "total_parsed": len(records),
            "errors": errors[:20],
        })
