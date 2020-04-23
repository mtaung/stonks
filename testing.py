from modules.iex import Iex
from utils import config

iex_token = config.load('iex').get('token')
iex = Iex(token = iex_token)

iex.history('GOOGL')