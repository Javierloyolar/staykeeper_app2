from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from bookings.models import Booking

@staff_member_required
def bookings_por_propiedad(request):
    listing_id = request.GET.get('listing_id')
    bookings = Booking.objects.filter(
        listing_id=listing_id
    ).select_related('guest').order_by('-check_in')

    data = [{
        'id': b.id,
        'label': f"{b.guest.full_name if b.guest else 'Sin huésped'} — {b.check_in.strftime('%d %b')} / {b.check_out.strftime('%d %b %Y')}"
    } for b in bookings]

    return JsonResponse(data, safe=False)