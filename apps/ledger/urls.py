from django.urls import path

from . import views

app_name = "ledger"
urlpatterns = [
    path("review/", views.MappingQueueView.as_view(), name="queue"),
    path("review/<int:pk>/", views.MappingReviewView.as_view(), name="review"),
    path("transactions/", views.TransactionListView.as_view(), name="transactions"),
]
