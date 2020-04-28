import discord
import datetime
from discord.ext import commands
from discord.ext.commands import errors
from db.interface import DB
from db.tables import User, Company, CompanyHistory, Symbol, HeldStock
from utils.scheduler import market_time, market_open_status, next_market_open
from .iex import Iex
from tabulate import tabulate
import pandas as pd
import numpy as np

def name(user):
    return user.nick if hasattr(user, 'nick') else user.name

def timedelta_string(delta):
    d = delta.days
    h, rem = divmod(delta.seconds, 3600)
    m, s = divmod(rem, 60)
    strs = []
    if d:
        strs.append(f"{d} days")
    if h:
        strs.append(f"{h} hours")
    if m:
        strs.append(f"{m} minutes")
    if s:
        strs.append(f"{s} seconds")
    return " ".join(strs)

class StonksError(errors.CommandError):
    pass

# TODO: pretty, concise printouts for frequent operations like sell/buy
# limit company name length in printout
# perhaps replace words like buy/sell with symbols?

class Stonks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.iex = Iex()
    
    async def get_active_company(self, ctx, db, user):
        uid = user.id
        company = db.query(Company).filter(Company.owner == uid).filter(Company.active == True).first()
        if not company:
            await ctx.send(f"You are not registered on the stonks market. Use $help register.")
            raise StonksError()
        return company
    
    async def market_open_check(self, ctx):
        if not market_open_status():
            await ctx.send(f"The market is closed. Please try again in {timedelta_string(next_market_open() - market_time())}.")
            raise StonksError()
    
    async def stock_symbol_check(self, ctx, db, symbol):
        if not db.query(Symbol).filter(Symbol.symbol == symbol):
            await ctx.send(f"{symbol} is not a valid stock symbol.")
            raise StonksError()
    
    @commands.command()
    async def register(self, ctx, company_name: str):
        """Register a company under your username, joining the game.\nUse quotation marks for names with multiple words or whitespace characters."""
        author = ctx.author
        uid = author.id
        uname = name(author)
        with DB() as db:
            if not db.query(User).filter(User.id == uid).first():
                db.add(User(id=uid, credit_score=0))
                await ctx.send(f'Welcome to the stonks market, {uname}. We have added you to our registry.')
            
            active_company = db.query(Company).filter(Company.owner == uid).filter(Company.active == True).first()
            if active_company:
                await ctx.send(f'You are already in ownership of the registered company {active_company.name}, {uname}.')

            else:
                company = Company(owner=uid, name=company_name, balance=10000, active=True)
                db.add(company)
                db.flush()
                db.add(CompanyHistory(company=company.id, date=datetime.datetime.now()))
                await ctx.send(f'Your application to register {company_name} has been accepted. Happy trading!')
    
    @commands.command()
    async def buy(self, ctx, quantity: int, symbol: str):
        """Buy shares of a stock at market price."""
        symbol = symbol.upper()
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            #TODO: uncomment
            #await self.market_open_check(ctx)
            await self.stock_symbol_check(ctx, db, symbol)
            
            price = self.iex.price(symbol)
            cost = quantity * price
            if company.balance < cost:
                await ctx.send(f"{company.name}\nBalance: {company.balance} USD\nPurchase cost: {cost} USD")
                raise StonksError()

            self.iex.buy(db, company.id, symbol, quantity, price)
            await ctx.send(f"{company.name} BUYS {quantity} {symbol} for {cost} USD")

    @commands.command()
    async def sell(self, ctx, quantity: int, symbol: str):
        """Sell shares of a stock at market price."""
        symbol = symbol.upper()
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            # TODO: uncomment
            #await self.market_open_check(ctx)
            await self.stock_symbol_check(ctx, db, symbol)
            
            inventory = self.iex.get_held_stock_quantity(db, company.id, symbol)
            if inventory < quantity:
                await ctx.send(f"{company.name}\n{inventory} {symbol}")
                raise StonksError()

            price = self.iex.price(symbol)
            value = price * quantity
            self.iex.sell(db, company.id, symbol, quantity, price)
            await ctx.send(f"{company.name} SELLS {quantity} {symbol} for {value} USD")

    @commands.command()
    async def balance(self, ctx):
        # TODO: Expand to include net value and other company information.
        """Check balance on your active company."""
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            embed = discord.Embed(title=f'Company: {company.name}', inline=True)
            embed.add_field(name='Cash Assets:', value=f'{round(company.balance, 2)} USD')
            await ctx.send(embed=embed)
    
    @commands.command()
    async def inv(self, ctx):
        """Simplified display of stocks owned by your current company."""
        # CONSIDER: Using an entirely pd.DataFrame based structure rather than converting from list
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            stock = self.iex.get_held_stocks(db, company.id)
            inventory = []
            for s in stock:
                inventory.append([s.symbol, s.quantity, s.purchase_price * s.quantity])
            inv_df = pd.DataFrame(inventory, columns=['Symbol', 'Quantity', 'Purchase Value'])
            aggregated = tabulate(inv_df.groupby(['Symbol']).sum().reset_index(), headers=['Symbol', 'Quantity', 'Purchase Value'])
            await ctx.send(f'```{aggregated}```')

    @commands.command()
    async def breakdown(self, ctx):
        # TODO: At the problem, this is assigning +/- based on testing parameters
        #       In production, we want to assign this based on current price of each stock. 
        #       This can potentially expend a lot of API calls, so we need to consider how to handle that.
        """Simplified display of stocks owned by your current company."""
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            stock = self.iex.get_held_stocks(db, company.id)
            inventory = []
            for s in stock:
                inventory.append([s.symbol, s.quantity, s.purchase_price * s.quantity])
            inv_df = pd.DataFrame(inventory, columns=['Symbol', 'Quantity', 'Purchase Value'])
            inv_df['sign'] = np.where(inv_df['Symbol'].str.contains('A'), '+', '-')
            inv_df = inv_df.sort_values(['Symbol'])
            inv_df = inv_df[['sign', 'Symbol', 'Quantity', 'Purchase Value']]
            aggregated = tabulate(inv_df.values.tolist(), headers=['Δ', 'Symbol', 'Quantity', 'Purchase Value'])
            await ctx.send(f'```diff\n{aggregated}```')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, errors.UserInputError):
            await ctx.send_help(ctx.command)
        elif isinstance(error, StonksError):
            pass
        else:
            await ctx.send("⚠")
            raise error

def setup(bot):
    bot.add_cog(Stonks(bot))