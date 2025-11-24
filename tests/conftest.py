import os
from importlib import reload

os.environ["POSTGRES_DSN"] = "sqlite:///./tests/test.db"
os.environ["INGEST_BUCKET_PATH"] = "./data/test-uploads"
os.environ["PROCESSED_TEXT_PATH"] = "./data/test-processed"
os.environ["CLAIM_EXTRACTOR"] = "simple"

from backend.app.core.config import get_settings

get_settings.cache_clear()

import backend.app.db.session as db_session

reload(db_session)

