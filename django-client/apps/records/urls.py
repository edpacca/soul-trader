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
    path("sales/pdf/", views.sales_pdf_export, name="sales_pdf_export"),
    path("purchases/pdf/", views.purchases_pdf_export, name="purchases_pdf_export"),
    path("business/pdf/", views.business_pdf_export, name="business_pdf_export"),
]
