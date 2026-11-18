import os
import psycopg2

def get_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta la variable de entorno DATABASE_URL")
    return psycopg2.connect(url, connect_timeout=10)