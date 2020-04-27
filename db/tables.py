from sqlalchemy import Column, Integer, Float, String, Boolean, Date, Sequence, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(String(20), primary_key = True)
    credit_score = Column(Float)

class Company(Base):
    __tablename__ = 'companies'
    id = Column(Integer, primary_key=True)
    owner = Column(String(20), ForeignKey('users.id'), nullable=False)
    name = Column(String(30))
    balance = Column(Float)
    active = Column(Boolean)

class CompanyHistory(Base):
    __tablename__ = 'company_history'
    id = Column(Integer, primary_key=True)
    company = Column(Integer, ForeignKey('companies.id'), nullable=False)
    date = Column(Date)
    value = Column(Float)

class HeldStock(Base):
    __tablename__ = 'held_stock'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(6))
    quantity = Column(Integer)
    company = Column(Integer, ForeignKey('companies.id'), nullable=False)
    purchase_price = Column(Float)
    purchase_date = Column(Date)

class CloseHistory(Base):
    __tablename__ = 'close_history'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(6))
    date = Column(Date)
    close = Column(Float)
    volume = Column(Integer)

class Symbol(Base):
    __tablename__= 'symbols'
    symbol = Column(String(6), primary_key=True)
    name = Column(String(50))
    stock_type = Column(String(5))

class Transactions(Base):
    # Transaction types are classified as the following:
    # 0: sell
    # 1: buy
    # 2: dividends
    __tablename__='transactions'
    symbol = Column(String(6), primary_key=True)
    company = Column(Integer, ForeignKey('companies.id'), nullable=False)
    trans_type = Column(Integer)
    trans_volume = Column(Integer)
    trans_price = Column(Float)
    date = Column(Date)
