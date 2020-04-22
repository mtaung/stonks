import discord, datetime
from discord.ext import commands
from db.interface import DatabaseInterface
from db.tables import User, Company, History

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
        
        if not self.db.get(User, id=uid):
            self.db.add(User(id=uid, credit_score=0))
            await ctx.send(f'Welcome to the stonks market, {uname}. We have added you to our registry.')
        
        active_company = self.db.get(Company, owner=uid, active=True)
        if active_company:
            await ctx.send(f'You are already in ownership of the registered company {active_company.name}, {uname}.')

        else:
            company = Company(owner=uid, name=company_name, balance=10000, active=True)
            self.db.add(company)
            self.db.add(History(company=company.id, date=datetime.datetime.now()))
            self.db.commit()
            await ctx.send(f'Your application to register {company_name} has been accepted. Happy trading!')

def setup(bot):
    bot.add_cog(Stonks(bot))