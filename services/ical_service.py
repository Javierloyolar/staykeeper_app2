import requests
from icalendar import Calendar
from datetime import datetime, date

class ICalService:
    @staticmethod
    def get_upcoming(url):
        if not url: return []
        try:
            res = requests.get(url, timeout=5)
            cal = Calendar.from_ical(res.content)
            events = []
            for component in cal.walk():
                if component.name == "VEVENT":
                    start = component.get('dtstart').dt
                    if isinstance(start, datetime): start = start.date()
                    if start >= date.today():
                        events.append({
                            'start': start,
                            'end': component.get('dtend').dt,
                            'name': component.get('summary')
                        })
            return sorted(events, key=lambda x: x['start'])
        except: return []