from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, Boolean, Text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy_json import NestedMutableJson, MutableJson
import configparser

Base = declarative_base()


class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True)

    round = Column(Integer)
    owner = Column(BigInteger)

    seed = Column(Integer) # separate seed from ID to prevent predictability of results and 100% matching between round and ticket


class Round(Base):
    __tablename__ = 'rounds'

    id = Column(Integer, primary_key=True)
    completed = Column(Boolean)


class RootData(Base):
    __tablename__ = 'dat'

    id = Column(Integer, primary_key=True)
    prefix = Column(Text)
    prizes = Column(NestedMutableJson)



engine = create_engine('sqlite:///app.db')
Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()
