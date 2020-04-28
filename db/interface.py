from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

engine = create_engine('sqlite:///stonks.db')
Session = scoped_session(sessionmaker(bind=engine))

class DB:
    def __enter__(self):
        return Session()
    def __exit__(self, type, value, traceback):
        if not value:
            # commit only if no exception occured
            Session.commit()
        #self.sess.close()
        Session.remove()

def _list(list_of_tuples):
    return [v for (v,) in list_of_tuples]
