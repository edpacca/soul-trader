from django.urls import path

from . import views

app_name = "records"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sales/", views.sales_detail, name="sales_detail"),
    path("purchases/", views.purchases_detail, name="purchases_detail"),
    path("sales/<int:record_id>/note/", views.update_sales_note, name="update_sales_note"),
    path("sales/<int:record_id>/note/delete/", views.delete_sales_note, name="delete_sales_note"),
    path("purchases/<int:record_id>/note/", views.update_purchase_note, name="update_purchase_note"),
    path("purchases/<int:record_id>/note/delete/", views.delete_purchase_note, name="delete_purchase_note"),
    path("notes/", views.notes_list, name="notes_list"),
    path("reports/", views.preset_list, name="preset_list"),
    path("presets/create/", views.preset_create, name="preset_create"),
    path("presets/<int:preset_id>/delete/", views.preset_delete, name="preset_delete"),
    path("reports/<int:preset_id>/run/", views.preset_run, name="preset_run"),
    path("sales/pdf/", views.sales_pdf_export, name="sales_pdf_export"),
    path("purchases/pdf/", views.purchases_pdf_export, name="purchases_pdf_export"),
    path("business/pdf/", views.business_pdf_export, name="business_pdf_export"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("chart-data/", views.chart_data, name="chart_data"),
]
