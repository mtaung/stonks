import discord
from discord.ext import commands
from utils import config
from utils.scheduler import Scheduler, next_daily_data, next_market_close
from modules.iex import Iex

# Configs
discord_token = config.load('discord').get('token')
bot = commands.Bot(command_prefix = '$')

# Exchange
iex = Iex()

# Cogs
startup_extensions = ["modules.stonks"]
for extension in startup_extensions:
    try:
        bot.load_extension(extension)
    except Exception as e:
        exc = '{}: {}'.format(type(e).__name__, e)
        print('Failed to load extension {}\n{}'.format(extension, exc))

# Scheduler
sched = Scheduler()
sched.schedule(iex.evaluate, next_market_close)
sched.schedule(iex.splits, next_daily_data)
sched.schedule(iex.dividends, next_daily_data)
sched.start()

# Run
bot.run(discord_token)