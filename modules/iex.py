from iexfinance import stocks
from iexfinance.refdata import get_symbols
from datetime import date
from utils import config
from utils.scheduler import market_time
from db.interface import DatabaseInterface
from db.tables import Symbol, CloseHistory, HeldStock, Company, Transactions

def _list(list_of_tuples):
    return [v for (v,) in list_of_tuples]

class Iex:
    def __init__(self):
        self.token = config.load('iex').get('token')
        self.db = DatabaseInterface('sqlite:///stonks.db')

    def price(self, symbol):
        quote = self.quote(symbol)
        return quote['latestPrice']

    def quote(self, symbol):
        return stocks.Stock(symbol, token = self.token).get_quote()
    
    def get_symbols_in_use(self):
        unique_symbols = self.db.query(HeldStock.symbol).distinct().all()
        return _list(unique_symbols)
    
    def get_owners_of(self, symbol):
        owners = self.db.query(HeldStock.company).filter(HeldStock.symbol == symbol).distinct().all()
        return _list(owners)

    def splits(self):
        """Check for stock splits and process them."""
        unique_symbols = self.get_symbols_in_use()
        pending_splits = {}
        # first, find which stocks start trading at split price today
        for symbol in unique_symbols:
            stock = stocks.Stock(symbol, token = self.token)
            splits = stock.get_splits(range='1m')
            # TODO: remove line
            #splits = self.splits_test(symbol)
            for split in splits:
                if market_time().date()  == date.fromisoformat(split['exDate']):
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
                inventory = self.db.query(HeldStock.quantity).filter(HeldStock.company == company_id).filter(HeldStock.symbol == symbol).all()
                inventory = sum(_list(inventory))
                self.sell(company_id, symbol, inventory, sell_price)
                # rebuy
                new_inventory = inventory * toFactor // fromFactor
                self.buy(company_id, symbol, new_inventory, rebuy_price)
    
    def dividends(self):
        """Check for stock dividends and process them."""
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
                if market_time().date()  == date.fromisoformat(event['paymentDate']):
                    pending_dividends[symbol] = {
                        'amount': event['amount'],
                        'cutoff': date.fromisoformat(event['exDate'])}
        
        # process affected companies
        for symbol in pending_dividends:
            affected_companies = self.get_owners_of(symbol)

            for company_id in affected_companies:
                company = self.db.get(Company, id=company_id)

                eligible_quantity = self.db.query(HeldStock.quantity).filter(HeldStock.company == company_id).filter(HeldStock.symbol == symbol).filter(HeldStock.purchase_date < pending_dividends[symbol]['cutoff'])
                eligible_quantity = sum(_list(eligible_quantity))

                dividend_amount = pending_dividends[symbol]['amount']
                value = dividend_amount * eligible_quantity
                company.balance += value
                # Record dividend income.
                self.db.add(Transactions(symbol=symbol, company=company_id, trans_type=2, trans_volume=eligible_quantity, trans_price=dividend_amount, date=self.market_time()))
            self.db.commit()

    def buy(self, company_id, symbol, quantity, price):
        """Buy stock, at given price and quantity, without error checking."""
        value = price * quantity
        # add stock
        self.db.add(HeldStock(symbol=symbol, quantity=quantity, company=company_id, purchase_price=price, purchase_date=self.market_time()))
        # subtract balance
        company = self.db.get(Company, id=company_id)
        company.balance -= value
        # record transaction
        self.db.add(Transactions(symbol=symbol, company=company_id, trans_type=1, trans_volume=quantity, trans_price=price, date=self.market_time()))
        self.db.commit()

    def sell(self, company_id, symbol, quantity, price):
        """Sell stock, at given price and quantity, without error checking."""
        value = price * quantity
        stocks = self.db.query(HeldStock).filter(HeldStock.company==company_id).filter(HeldStock.symbol==symbol).order_by(HeldStock.purchase_date.asc())
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
        # Record sell transaction
        self.db.add(Transactions(symbol=symbol, company=company_id, trans_type=0, trans_volume=quantity, trans_price=price, date=self.market_time()))
        self.db.commit()
    
    def update_symbols(self):
        """Update internal list of symbols."""
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
    
    def evaluate(self):
        """Evaluate the net worth all player companies. Accumulate statistical information."""
        # get the close value of all stock in use
        symbols = self.get_symbols_in_use()
        for symbol in symbols:
            #quote = self.quote(symbol)
            return
    
    def history(self, symbol):
        # TODO: account for timezones, account for weekends, then define start and end dates based on that
        # the historical market data on IEX is updated at 4AM ET (eastern time) Tue-Sat
        # must adjust datetime.now() by an appropriate offset so that it equals the previous day when it is < 4AM ET today
        # and further adjust it if it falls onto a weekend, this should affect timedelta as well
        #delta = timedelta(days=3)
        #end = datetime.now()
        #start = end - delta
        # this fetches the history from iex and puts it in the db
        #close_history = stocks.get_historical_data(symbol, start=start, end=datetime.now(), close_only=True, output_format='json', token=self.token)
        #for close_date in close_history:
        #    self.db.add(CloseHistory(symbol=symbol, date=date.fromisoformat(close_date), close=close_history[close_date]['close'], volume=close_history[close_date]['volume']))
        #self.db.commit()
        # this gets the latest date available in the db
        #cached_history = self.db.get_query(Close).filter(Close.symbol == symbol).order_by(Close.date.desc()).first()
        
        #cached_history = self.db.get_query(CloseHistory).filter(CloseHistory.symbol == symbol).order_by(CloseHistory.date.desc()).first()
        pass
