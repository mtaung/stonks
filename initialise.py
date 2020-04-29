import os
from db import tables
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from modules.iex import Iex

dbfile = 'stonks.db'

if not os.path.isfile(dbfile):
    engine = create_engine('sqlite:///' + dbfile)
    tables.Base.metadata.bind = engine
    tables.Base.metadata.create_all()
    print(f"{dbfile} created.")
else:
    print(f"{dbfile} already exists, no changes made.")

populate = input("Populate symbols table? [y/n]")
if populate=="y" or "Y":
    iex = Iex()
    iex.update_symbols()
    print("symbols updated")