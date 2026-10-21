import os
from pathlib import Path

ROOT = Path(__file__).parent
ON_VERCEL = bool(os.getenv('VERCEL'))
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or ('sqlite:///' + str(ROOT / 'local.db'))
DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
SESSION_SECRET = os.getenv('SESSION_SECRET', '')
if ON_VERCEL:
    if not DATABASE_URL.startswith('postgresql+psycopg://'):
        raise RuntimeError('Vercel requires a persistent PostgreSQL DATABASE_URL')
    if len(SESSION_SECRET) < 32 or SESSION_SECRET.startswith('replace-'):
        raise RuntimeError('Set a random SESSION_SECRET of at least 32 characters')
