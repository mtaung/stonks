import discord, datetime
from discord.ext import commands
from discord.ext.commands import CommandError
from db.interface import DatabaseInterface
from db.tables import User, Company, History, Symbol, Stock
from .iex import Iex

def name(user):
    return user.nick if hasattr(user, 'nick') else user.name

class Stonks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseInterface('sqlite:///stonks.db')
        self.iex = Iex()
    
    async def get_active_company(self, ctx, user):
        uid = user.id
        company = self.db.get(Company, owner=uid, active=True)
        if not company:
            await ctx.send(f"You are not registered on the stonks market. Use $help register.")
            raise CommandError()
        return company
    
    async def market_open_check(self, ctx):
        if not self.iex.market_open_status():
            await ctx.send(f"The market is closed. Please try again in {str(self.iex.time_to_open())}")
            raise CommandError()
    
    async def stock_symbol_check(self, ctx, symbol):
        if not self.db.get(Symbol, symbol=symbol):
            await ctx.send(f"{symbol} is not a valid stock symbol.")
            raise CommandError()
    
    @commands.command(pass_context=True)
    async def register(self, ctx, company_name: str):
        """Register a company under your username, joining the game.\nUse quotation marks for names with multiple words or whitespace characters."""
        author = ctx.message.author
        uid = author.id
        uname = name(author)
        
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
    
    @commands.command(pass_context=True)
    async def buy(self, ctx, quantity: int, symbol: str):
        """Buy shares of a stock at market price."""
        symbol = symbol.upper()
        author = ctx.message.author
        company = await self.get_active_company(ctx, author)
        await self.market_open_check(ctx)
        await self.stock_symbol_check(ctx, symbol)
        
        price = self.iex.price(symbol)
        cost = quantity * price
        if company.balance < cost:
            await ctx.send(f"{company.name}\nBalance: {company.balance} USD\nPurchase cost: {cost} USD")
            return
        self.db.add(Stock(symbol=symbol, quantity=quantity, company=company.id, purchase_value=price, purchase_date=self.iex.market_time()))
        company.balance -= cost
        self.db.commit()
        await ctx.send(f"{company.name} BUYS {quantity} {symbol} for {cost} USD")
    
    @commands.command(pass_context=True)
    async def balance(self, ctx):
        """Check balance on your active company."""
        author = ctx.message.author
        company = await self.get_active_company(ctx, author)
        await ctx.send(f"{company.name}\nBalance: {company.balance} USD")

def setup(bot):
    bot.add_cog(Stonks(bot))