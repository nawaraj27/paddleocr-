from django.urls import path
from . import views

app_name = "uploads"
urlpatterns = [
    path("", views.UploadCenterView.as_view(), name="index"),
    path("ingest/", views.UploadIngestView.as_view(), name="ingest"),
]
