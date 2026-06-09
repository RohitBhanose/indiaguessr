import os
from app.core.config import settings
print('CWD:', os.getcwd())
print('DATABASE_URL:', settings.DATABASE_URL)
