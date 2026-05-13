from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from properties.models import Property
from bookings.models import Booking
from services.ical_service import ICalService
from django.db.models import Sum

class DashboardIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Filtro de propiedad
        props = Property.objects.filter(owner=user)
        listing_id = self.request.GET.get('listing')
        selected = props.filter(id=listing_id).first() if listing_id else None

        # Datos
        bookings = Booking.objects.filter(listing__owner=user)
        if selected: bookings = bookings.filter(listing=selected)

        # iCal
        upcoming = []
        ical_svc = ICalService()
        to_check = [selected] if selected else props
        for p in to_check:
            events = ical_svc.get_upcoming(p.airbnb_ical_url)
            for e in events: e['prop'] = p.name
            upcoming.extend(events)

        context.update({
            'properties': props,
            'selected': selected,
            'total_net': bookings.aggregate(Sum('net_revenue'))['net_revenue__sum'] or 0,
            'upcoming': upcoming[:10],
            'recent': bookings.order_by('-check_in')[:5]
        })
        return context