from iexfinance import stocks
from iexfinance.refdata import get_symbols
from datetime import datetime, date, time, timedelta, timezone
from pytz import timezone
from math import floor
from utils import config
from db.interface import DatabaseInterface
from db.tables import Symbol, Close, Stock, Company

EDT = timezone('US/Eastern')
MARKET_OPEN_TIME = time(4,30)
MARKET_CLOSE_TIME = time(20)

class Iex:

    def __init__(self):
        self.token = config.load('iex').get('token')
        self.db = DatabaseInterface('sqlite:///stonks.db')
    
    def market_time(self):
        return datetime.now(tz=EDT)
    
    def market_open_status(self):
        now = self.market_time()
        return now.weekday() <= 4 and now.time() > MARKET_OPEN_TIME and now.time() < MARKET_CLOSE_TIME
    
    def time_to_open(self):
        now = self.market_time()
        weekend = min(max(6 - now.weekday(), 0), 2)
        next_open = datetime(
            now.year,
            now.month,
            now.day + 1 + weekend,
            MARKET_OPEN_TIME.hour,
            MARKET_OPEN_TIME.minute,
            MARKET_OPEN_TIME.second,
            MARKET_OPEN_TIME.microsecond,
            tzinfo=now.tzinfo)
        return next_open - now

    def price(self, symbol):
        quote = self.quote(symbol)
        return quote['latestPrice']

    def quote(self, symbol):
        stonk = stocks.Stock(symbol, token = self.token)
        quote = stonk.get_quote()
        return quote
    
    def splits_test(self, symbol):
        # generate fake split data for a given symbol, for testing
        if symbol == "TEST_SYM":
            return [{
                'exDate': "2020-04-26",
                'toFactor': 7,
                'fromFactor': 1}]
        else:
            return []

    def splits(self):
        unique_symbols = self.db.query(Stock.symbol).distinct().all()
        pending_splits = {}

        for symbol in unique_symbols:
            # TODO: uncomment when done testing
            #stock = stocks.Stock(symbol, token = self.token)
            #splits = stock.get_splits(range='1m')
            splits = self.splits_test(symbol)
            for split in splits:
                if self.market_time().date()  == date.fromisoformat(split['exDate']):
                    pending_splits[symbol] = {
                        'from': split['fromFactor'],
                        'to': split['toFactor']}

        for symbol in pending_splits:
            affected_companies = self.db.query(Stock.company).filter(Stock.symbol == symbol).distinct().all()
            fromFactor = pending_splits[symbol]['from']
            toFactor = pending_splits[symbol]['to']
            sell_price = self.quote(symbol)['close']
            rebuy_price = sell_price * fromFactor / toFactor
            for company_id in affected_companies:
                # sell
                inventory = sum(self.db.get_all(Stock.quantity, company=company_id, symbol=symbol))
                self.sell(company_id, symbol, inventory, sell_price)
                # rebuy
                new_inventory = inventory * toFactor // fromFactor
                self.buy(company_id, symbol, new_inventory, rebuy_price)
    
    def buy(self, company_id, symbol, quantity, price):
        """Buy stock, at given price and quantity, without error checking."""
        value = price * quantity
        # add stock
        self.db.add(Stock(symbol=symbol, quantity=quantity, company=company_id, purchase_value=price, purchase_date=self.market_time()))
        # subtract balance
        company = self.db.get(Company, id=company_id)
        company.balance -= value
        # TODO: log buy transaction
        self.db.commit()

    def sell(self, company_id, symbol, quantity, price):
        """Sell stock, at given price and quantity, without error checking."""
        value = price * quantity
        stocks = self.db.get_all(Stock.quantity, company=company_id, symbol=symbol)
        # FIFO subtract stock
        for s in stocks:
            amnt = min(quantity, s.quantity)
            s.quantity -= amnt
            quantity -= amnt
            if quantity == 0:
                break
        # delete 0 quant rows
        for s in stocks:
            if s.quantity == 0:
                self.db.delete(s)
        # add balance
        company = self.db.get(Company, id=company_id)
        company.balance += value
        # TODO: log sell transaction
        self.db.commit()
    
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
