import sched
import time as time_t
import threading
from datetime import datetime, date, time, timedelta
from pytz import timezone

EDT = timezone('US/Eastern')
UTC = timezone('UTC')
MARKET_OPEN_TIME = time(4,30)
MARKET_CLOSE_TIME = time(20)
DAILY_DATA = time(9)

def market_time():
    return datetime.now(tz=EDT)

def market_open_status():
    now = market_time()
    return now.weekday() <= 4 and now.time() > MARKET_OPEN_TIME and now.time() < MARKET_CLOSE_TIME

def next_daily_event(event_time, workday=True, tz=EDT):
    now = datetime.now(tz=tz)
    weekend = min(max(6 - now.weekday(), 0), 2) if workday else 0
    delta = timedelta(0) if now.time() < event_time else timedelta(days=1 + weekend)
    return datetime.combine(now.date() + delta, event_time, tzinfo=now.tzinfo)

def next_market_open():
    return next_daily_event(MARKET_OPEN_TIME)

def next_market_close():
    return next_daily_event(MARKET_CLOSE_TIME)

def next_daily_data():
    return next_daily_event(DAILY_DATA, tz=UTC)

class Scheduler:
    def __init__(self):
        self.scheduler = sched.scheduler(time_t.time, time_t.sleep)
        self.daemon = threading.Thread(target=self.scheduler.run, daemon=True)
        self.events = {}

    def start(self):
        for time_func in self.events:
            self._schedule_event_group(time_func)
        self.daemon.start()
    
    def schedule(self, event_func, time_func):
        """Schedule a periodic event.
        event_func : target event
        time_func : must return a datetime of next event"""
        if time_func not in self.events:
            self.events[time_func] = []
        self.events[time_func].append(event_func)
    
    def _schedule_event_group(self, time_func):
        self.scheduler.enterabs(time_func().timestamp(), 0, self._run_event_group, [time_func])

    def _run_event_group(self, time_func):
        self._schedule_event_group(time_func)
        # run in separate worker thread
        threading.Thread(target=lambda: [f() for f in self.events[time_func]], daemon=False).start()
