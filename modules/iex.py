from iexfinance import stocks
from iexfinance.refdata import get_symbols
from utils import config

token = config.load('iex').get('token')

stock =  stocks.Stock('GOOGL', token=token)
stock.get_quote()