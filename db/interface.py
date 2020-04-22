from sqlalchemy import create_engine, literal
from sqlalchemy.orm import sessionmaker
from . import tables 

class BasicInterface:

    def __init__(self, table, session):
        self.Table = table 
        self.session = session

    def get(self, id):
        return self.session.query(self.Table).filter(self.Table.id == id).first()

    def add(self, **kwargs):
        if kwargs:
            dbo = self.Table(**kwargs)
            self.session.add(dbo)
            self.session.flush()
            return dbo
        return None

    def count(self):
        return self.session.query(self.Table).count()

    def getrow(self, row):
        return self.session.query(self.Table).offset(row).first()

class StockInterface(BasicInterface):

    def company_inventory(self, company):
        return self.session.query(self.Table).filter(self.Table.company == company)

class CompanyInterface(BasicInterface):

    def get_active(self, id):
        return self.session.query(self.Table).filter(self.Table.owner == id).filter(self.Table.active).first()

class DatabaseInterface:

    def __init__(self, url):
        engine = create_engine(url)
        Session = sessionmaker(bind=engine)
        self.main_session = Session()
        self.users = BasicInterface(tables.User, self.main_session)
        self.history = BasicInterface(tables.History, self.main_session)
        self.companies = CompanyInterface(tables.Company, self.main_session)
        self.symbols = BasicInterface(tables.Symbol, self.main_session)
        self.closes = BasicInterface(tables.Close, self.main_session)
    
    def commit(self):
        self.main_session.commit()
