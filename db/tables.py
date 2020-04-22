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

class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True)
    company = Column(Integer, ForeignKey('companies.id'), nullable=False)
    date = Column(Date)
    value = Column(Float)

class Stock(Base):
    __tablename__ = 'stocks'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(6))
    quantity = Column(Float)
    company = Column(Integer, ForeignKey('companies.id'), nullable=False)
    purchase_value = Column(Float)
    purchase_date = Column(Date)

class Close(Base):
    __tablename__ = 'closes'
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
    