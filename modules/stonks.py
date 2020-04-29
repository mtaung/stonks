import discord
from datetime import timedelta
from discord.ext import commands
from discord.ext.commands import errors
from db.interface import DB
from db.tables import User, Company, CompanyHistory, Symbol, HeldStock, CloseHistory
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

# TODO: 
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
        if not db.query(Symbol).filter(Symbol.symbol == symbol).first():
            await ctx.send(f"{symbol} is not a valid stock symbol.")
            raise StonksError()
    
    async def get_latest_close(self, ctx, db, symbol):
        close_row = db.query(CloseHistory).filter(CloseHistory.symbol == symbol).order_by(CloseHistory.date.desc()).first()
        if not close_row:
            close_row = self.iex.get_latest_close(db, symbol)
            return close_row
        return close_row
    
    @commands.command()
    async def time(self, ctx):
        """Return the current time 
        time = market_time()
        await ctx.send(f'It is currently {time} EDT for the market.')
    
    @commands.command()
    async def register(self, ctx, company_name: str):
        """Register a company under your username, joining the game.\nUse double quotation marks for names with multiple words or whitespace characters."""
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
                db.add(CompanyHistory(company=company.id, date=market_time() - timedelta(days=1), value=10000))
                await ctx.send(f'Your application to register {company_name} has been accepted. Happy trading!')
    
    @commands.command()
    async def buy(self, ctx, quantity: int, symbol: str):
        """Buy shares of a stock at market price."""
        symbol = symbol.upper()
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            await self.market_open_check(ctx)
            await self.stock_symbol_check(ctx, db, symbol)
            
            price = self.iex.price(symbol)
            cost = quantity * price
            if company.balance < cost:
                await ctx.send(f"{company.name}\nBalance: {company.balance} USD\nPurchase cost: {cost} USD")
                raise StonksError()

            self.iex.buy(db, company.id, symbol, quantity, price)
            await ctx.send(f"``{company.name} ⯮ {quantity} {symbol} @ {cost}``")

    @commands.command()
    async def sell(self, ctx, quantity: int, symbol: str):
        """Sell shares of a stock at market price."""
        symbol = symbol.upper()
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            await self.market_open_check(ctx)
            await self.stock_symbol_check(ctx, db, symbol)
            
            inventory = self.iex.get_held_stock_quantity(db, company.id, symbol)
            if inventory < quantity:
                await ctx.send(f"``{company.name}\n{inventory} {symbol}``")
                raise StonksError()

            price = self.iex.price(symbol)
            value = price * quantity
            self.iex.sell(db, company.id, symbol, quantity, price)
            await ctx.send(f"``{company.name} ⯬ {quantity} {symbol} @ {value}``")

    @commands.command()
    async def balance(self, ctx):
        """Check balance on your active company."""
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            history = db.query(CompanyHistory).filter(CompanyHistory.company == company.id).order_by(CompanyHistory.date.desc()).limit(2).all()
            net_worth = history[0].value
            delta = history[0].value - history[1].value if len(history) == 2 else 0
            percent = delta * 100 / history[1].value if len(history) == 2 else 0
            symbol = '⮝' if delta >= 0 else '⮟'
            embed = discord.Embed(title=f'{company.name}', description=f'{symbol}{round(percent, 2)}%', inline=True)
            embed.add_field(name='Cash Assets:', value=f'{round(company.balance, 2)} USD')
            embed.add_field(name='Net worth:', value=f'{round(net_worth, 2)} USD')
            await ctx.send(embed=embed)
    
    @commands.command()
    async def inv(self, ctx):
        """Simplified display of stocks owned by your current company."""
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            stock = self.iex.get_held_stocks(db, company.id)
            inventory = []
            for s in stock:
                close = await self.get_latest_close(ctx, db, s.symbol)
                inventory.append([s.symbol, s.quantity, close.close * s.quantity])
            inv_df = pd.DataFrame(inventory, columns=['Symbol', 'Quantity', 'Value'])
            aggregated = tabulate(inv_df.groupby(['Symbol']).sum().reset_index(), headers=['Symbol', 'Quantity', 'Value'])
            await ctx.send(f'```{aggregated}```')

    @commands.command()
    async def daily(self, ctx):
        # TODO: Asssess whether this can be cleaned up. 
        #       As it stands, very similar to inv()
        """Simplified display of stocks owned by your current company."""
        author = ctx.author
        with DB() as db:
            company = await self.get_active_company(ctx, db, author)
            stock = self.iex.get_held_stocks(db, company.id)
            inventory = []
            for s in stock:
                close = await self.get_latest_close(ctx, db, s.symbol)
                inventory.append([s.symbol, s.quantity, s.purchase_price, close.close, s.quantity*s.purchase_price - s.quantity*close.close]) 
            inv_df = pd.DataFrame(inventory, columns=['Symbol', 'Quantity', 'Purchase Price', 'Close', 'Current Value'])
            inv_df['sign'] = np.where(inv_df['Current Value']>=0, '+', '-')
            inv_df['%'] = abs(((inv_df['Purchase Price'] - inv_df['Close'])  / inv_df['Purchase Price']) * 100)
            inv_df['%'] = inv_df['%'].round(1)
            inv_df = inv_df.sort_values(['Symbol'])
            inv_df = inv_df[['sign', '%', 'Symbol', 'Quantity', 'Purchase Price', 'Close', 'Current Value']]
            aggregated = tabulate(inv_df.values.tolist(), headers=['Δ', '%', 'Symbol', 'Quantity', 'Purchase Price', 'Close', 'Current Value'])
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