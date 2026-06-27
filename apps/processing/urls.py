from django.urls import path
from . import views

app_name = "processing"
urlpatterns = [
    path("data/", views.DataViewerView.as_view(), name="data"),
    path("export/<str:fmt>/", views.ExportView.as_view(), name="export"),
]
