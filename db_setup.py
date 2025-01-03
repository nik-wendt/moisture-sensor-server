import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from settings import DATABASE_URL

log = logging.getLogger(__name__)

log.info("Connecting to database")
engine = create_engine(DATABASE_URL)
log.info("Connected to database")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Database setup
Base.metadata.create_all(bind=engine)
log.info("Created tables in database")