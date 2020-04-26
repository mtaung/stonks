from sqlalchemy import create_engine, literal
from sqlalchemy.orm import sessionmaker

class DatabaseInterface:
    def __init__(self, url):
        engine = create_engine(url)
        Session = sessionmaker(bind=engine)
        self.session = Session()
    
    def query(self, Table):
        return self.session.query(Table)
    
    def _get(self, Table, **kwargs):
        q = self.session.query(Table)
        for key in kwargs:
            q = q.filter(getattr(Table, key) == kwargs[key])
        return q
    
    def get_all(self, Table, **kwargs):
        return self._get(Table, **kwargs).all()
    
    def get(self, Table, **kwargs):
        return self._get(Table, **kwargs).first()
    
    def add(self, obj):
        self.session.add(obj)
        self.session.flush()
    
    def count(self, Table):
        return self.session.query(Table).count()
    
    def delete(self, obj):
        self.session.delete(obj)
    
    def commit(self):
        self.session.commit()