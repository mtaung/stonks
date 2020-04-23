import os
from db import tables
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

dbfile = 'stonks.db'

if not os.path.isfile(dbfile):
    engine = create_engine('sqlite:///' + dbfile)
    tables.Base.metadata.bind = engine
    tables.Base.metadata.create_all()
    print(f"{dbfile} created.")
else:
    print(f"{dbfile} already exists, no changes made.")