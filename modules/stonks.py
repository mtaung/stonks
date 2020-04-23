import discord
from discord.ext import commands
from db.interface import DatabaseInterface

class Stonks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseInterface('sqlite:///stonks.db')
    
    @commands.command(pass_context=True)
    async def register(self, ctx, company_name: str):
        """Register a user for the game."""
        author = ctx.message.author
        uid = author.id
        uname = author.nick if hasattr(author, 'nick') else author.name
        await ctx.send(f"debug: {author}, {uid}, {uname}")

def setup(bot):
    bot.add_cog(Stonks(bot))