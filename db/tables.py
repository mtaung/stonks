from sqlalchemy import Column, Integer, Float, String, Boolean, Date, Sequence, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(String(20), primary_key = True)

class Company(Base):
    __tablename__ = 'companies'
    id = Column(Integer, primary_key=True)
    owner = Column(String(20), ForeignKey('users.id'), nullable=False)
    name = Column(String(30))
    balance = Column(Float)
    value = Column(Float)
    credit_score = Column(Float)
    active = Column(Boolean)

class Stock(Base):
    __tablename__ = 'stocks'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(6))
    quantity = Column(Float)
    company = Column(String(20), ForeignKey('companies.id'), nullable=False)
    purchase_value = Column(Float)
    purchase_date = Column(Date)
