import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv('NEON_DB_HOST')
PORT = os.getenv('NEON_DB_PORT', 5432)
DATABASE = os.getenv('NEON_DB_DATABASE')
USER = os.getenv('NEON_DB_USER')
PASSWORD = os.getenv('NEON_DB_PASSWORD')


def get_connection():
    try:
        connection = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USER,
            password=PASSWORD,
            cursor_factory=RealDictCursor  # return dict rows
        )
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        return None
