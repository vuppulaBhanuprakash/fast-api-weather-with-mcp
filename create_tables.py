# create_tables.py
from database import Base, engine
import models   # this ensures WeatherRequest gets registered

Base.metadata.create_all(bind=engine)