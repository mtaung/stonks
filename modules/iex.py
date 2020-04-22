from iexfinance import stocks
from iexfinance.refdata import get_symbols
from datetime import datetime
from datetime import timedelta
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
        return self.db.getall(Symbol)
    
    def history(self, symbol):
        delta = timedelta(days=3)
        end = datetime.now()
        start = end - delta
        cached_history = self.db.getall(Close, symbol=symbol)
        #close_history = stocks.get_historical_data(symbol, start=start, end=datetime.now(), close_only=True, output_format='json', token=self.token)
        #return close_history
