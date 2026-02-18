from django.urls import path

from . import views

app_name = "records"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sales/", views.sales_detail, name="sales_detail"),
    path("purchases/", views.purchases_detail, name="purchases_detail"),
]
