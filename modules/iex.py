from iexfinance import stocks
from iexfinance.refdata import get_symbols
from datetime import datetime, date, timedelta, timezone
from utils import config
from db.interface import DatabaseInterface
from db.tables import Symbol, Close

class Iex:

    def __init__(self, token):
        self.token = token
        self.db = DatabaseInterface('sqlite:///stonks.db')

    def price(self, symbol):
        stonk = stocks.Stock(symbol, token=self.token)
        quote = stonk.get_quote()
        return quote['latestPrice']

    def update_symbols(self):
        symbols = get_symbols(token = self.token)
        # handle adding of symbols
        for symbol in symbols:
            sym = symbol['symbol']
            if not self.db.get(Symbol, symbol=sym):
                self.db.add(Symbol(symbol=sym, name=symbol['name'], stock_type=symbol['type']))
        self.db.commit()
        # handle removal of symbols?
        # I think this is a bit more complicated, because what happens if someone owns stock etc
        # leave for later
    
    def symbols(self):
        return self.db.get_all(Symbol)
    
    def history(self, symbol):
        # TODO: account for timezones, account for weekends, then define start and end dates based on that
        # the historical market data on IEX is updated at 4AM ET (eastern time) Tue-Sat
        # must adjust datetime.now() by an appropriate offset so that it equals the previous day when it is < 4AM ET today
        # and further adjust it if it falls onto a weekend, this should affect timedelta as well
        delta = timedelta(days=3)
        end = datetime.now()
        start = end - delta
        # this fetches the history from iex and puts it in the db
        #close_history = stocks.get_historical_data(symbol, start=start, end=datetime.now(), close_only=True, output_format='json', token=self.token)
        #for close_date in close_history:
        #    self.db.add(Close(symbol=symbol, date=date.fromisoformat(close_date), close=close_history[close_date]['close'], volume=close_history[close_date]['volume']))
        #self.db.commit()

        # this gets the latest date available in the db
        #cached_history = self.db.get_query(Close).filter(Close.symbol == symbol).order_by(Close.date.desc()).first()
