import discord
from discord.ext import commands
from utils import config

# Configs
discord_token = config.load('discord').get('token')
bot = commands.Bot(command_prefix = '$')

# Cogs
startup_extensions = ["modules.stonks"]
for extension in startup_extensions:
    try:
        bot.load_extension(extension)
    except Exception as e:
        exc = '{}: {}'.format(type(e).__name__, e)
        print('Failed to load extension {}\n{}'.format(extension, exc))

# Run
bot.run(discord_token)