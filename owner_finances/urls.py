from django.urls import path
from .views import bookings_por_propiedad

urlpatterns = [
    path('bookings-por-propiedad/', bookings_por_propiedad, name='bookings_por_propiedad'),
]