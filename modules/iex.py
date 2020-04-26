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

def _list(list_of_tuples):
    return [v for (v,) in list_of_tuples]

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
        return stocks.Stock(symbol, token = self.token).get_quote()
    
    def get_symbols_in_use(self):
        unique_symbols = self.db.query(Stock.symbol).distinct().all()
        return _list(unique_symbols)
    
    def get_owners_of(self, symbol):
        owners = self.db.query(Stock.company).filter(Stock.symbol == symbol).distinct().all()
        return _list(owners)

    def splits(self):
        unique_symbols = self.get_symbols_in_use()
        pending_splits = {}
        # first, find which stocks start trading at split price today
        for symbol in unique_symbols:
            stock = stocks.Stock(symbol, token = self.token)
            splits = stock.get_splits(range='1m')
            # TODO: remove line
            #splits = self.splits_test(symbol)
            for split in splits:
                if self.market_time().date()  == date.fromisoformat(split['exDate']):
                    pending_splits[symbol] = {
                        'from': split['fromFactor'],
                        'to': split['toFactor']}
        
        # process affected companies
        # modeling split as:
        # selling existing inventory at last known (close) price
        # rebuying inventory at price * ratio and quantity / ratio
        # ratio = fromFactor / toFactor
        # company gets to keep liquidated cash in case of division with remainder
        for symbol in pending_splits:
            affected_companies = self.get_owners_of(symbol)

            fromFactor = pending_splits[symbol]['from']
            toFactor = pending_splits[symbol]['to']

            sell_price = self.quote(symbol)['close']
            rebuy_price = sell_price * fromFactor / toFactor

            for company_id in affected_companies:
                # sell
                inventory = self.db.query(Stock.quantity).filter(Stock.company == company_id).filter(Stock.symbol == symbol).all()
                inventory = sum(_list(inventory))
                self.sell(company_id, symbol, inventory, sell_price)
                # rebuy
                new_inventory = inventory * toFactor // fromFactor
                self.buy(company_id, symbol, new_inventory, rebuy_price)
    
    def dividends(self):
        unique_symbols = self.get_symbols_in_use()
        # dividend rules:
        # recordDate - the date by which you have to legally own the share to receive dividends
        # exDate - date set by the stock exchange by which you can buy the stock and still be eligible for dividends, always a few days before recordDate
        # for all intents and purposes, we can take exDate to be the cutoff point for eligibility
        # paymentDate - the date when dividend payments are processed
        # amount - the amount paid per share

        pending_dividends = {}
        # first, find which stocks must get dividend payments today
        for symbol in unique_symbols:
            stock = stocks.Stock(symbol, token = self.token)
            dividends = stock.get_dividends(range='1m')
            for event in dividends:
                if self.market_time().date()  == date.fromisoformat(event['paymentDate']):
                    pending_dividends[symbol] = {
                        'amount': event['amount'],
                        'cutoff': date.fromisoformat(event['exDate'])}
        
        # process affected companies
        for symbol in pending_dividends:
            affected_companies = self.get_owners_of(symbol)

            for company_id in affected_companies:
                company = self.db.get(Company, id=company_id)

                eligible_quantity = self.db.query(Stock.quantity).filter(Stock.company == company_id).filter(Stock.symbol == symbol).filter(Stock.purchase_date < pending_dividends[symbol]['cutoff'])
                eligible_quantity = sum(_list(eligible_quantity))

                value = pending_dividends[symbol]['amount'] * eligible_quantity
                company.balance += value
                # TODO: log dividend income?
            self.db.commit()

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
        stocks = self.db.query(Stock).filter(Stock.company==company_id).filter(Stock.symbol==symbol).order_by(Stock.purchase_date.desc())
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
