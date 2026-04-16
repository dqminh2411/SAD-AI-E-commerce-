from django.urls import path

from .views import EventsView, HealthView

urlpatterns = [
    path('api/health/', HealthView.as_view(), name='health'),
    path('api/events/', EventsView.as_view(), name='events'),
]
