from iexfinance import stocks
from iexfinance.refdata import get_symbols
from datetime import datetime
from datetime import timedelta
from utils import config
from db.interface import DatabaseInterface

class Iex:

    def __init__(self, token):
        
        self.token = token
        self.db = DatabaseInterface('sqlite:///stonks.db')

    def price(self, symbol):
        stonk = stocks.Stock(symbol, token=self.token)
        quote = stonk.get_quote()
        return quote['latestPrice']

    def symbols(self):
        symbols = get_symbols(token = self.token)

        for symbol in symbols:
            
            if symbol['symbol']

        return symbols
    
    def history(self, symbol):
        start = datetime.now() - timedelta(days=3)
        close_history = stocks.get_historical_data(symbol, start=start, end=datetime.now(), close_only=True, output_format='json', token=self.token)
        return close_history

    