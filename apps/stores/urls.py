from django.urls import path

from . import views

app_name = "stores"
urlpatterns = [
    path("stores/", views.StoreSelectView.as_view(), name="select"),
    path("stores/new/", views.StoreCreateView.as_view(), name="create"),
    path("stores/<int:pk>/switch/", views.StoreSwitchView.as_view(),
         name="switch"),
]
