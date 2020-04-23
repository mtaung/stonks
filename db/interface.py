from sqlalchemy import create_engine, literal
from sqlalchemy.orm import sessionmaker

class DatabaseInterface:
    def __init__(self, url):
        engine = create_engine(url)
        Session = sessionmaker(bind=engine)
        self.session = Session()
    
    def get_query(self, Table):
        return self.session.query(Table)
    
    def get_all(self, Table, **kwargs):
        q = self.session.query(Table)
        for key in kwargs:
            q = q.filter(getattr(Table, key) == kwargs[key])
        return q.all()
    
    def get(self, Table, **kwargs):
        q = self.get_all(Table, **kwargs)
        return q.first()
    
    def add(self, obj):
        self.session.add(obj)
        return None
    
    def count(self, Table):
        return self.session.query(Table).count()
    
    def delete(self, obj):
        self.session.delete(obj)
    
    def commit(self):
        self.session.commit()