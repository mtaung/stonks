from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

engine = create_engine('sqlite:///stonks.db')
Session = sessionmaker(bind=engine)

class DB:
    def __enter__(self):
        self.sess = Session()
        return self.sess
    def __exit__(self, type, value, traceback):
        if not value:
            # commit only if no exception occured
            self.sess.commit()
        self.sess.close()

def _list(list_of_tuples):
    return [v for (v,) in list_of_tuples]
