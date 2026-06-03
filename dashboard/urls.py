from django.urls import path
from .views import DashboardIndexView, KpiIngresosView, KpiOcupacionView, EstadiaView

app_name = 'dashboard'
urlpatterns = [
    path('', DashboardIndexView.as_view(), name='index'),
    path('kpi/ingresos/', KpiIngresosView.as_view(), name='kpi_ingresos'),
    path('kpi/ocupacion/', KpiOcupacionView.as_view(), name='kpi_ocupacion'),
    path('estadias/', EstadiaView.as_view(), name='estadias'),
]