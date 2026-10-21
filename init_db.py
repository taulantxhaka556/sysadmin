"""Run once before deploying, against the intended database."""
from main import initialize_database

if __name__ == '__main__':
    initialize_database()
    print('Database initialized. Existing accounts, lessons and grades preserved.')
