import os
import psycopg2

def get_connection():
    # Intenta usar la URL de la nube, si no existe, usa una de prueba local
    url = os.environ.get('DATABASE_URL', 'postgres://tu_usuario:tu_password@localhost:5432/tu_db')
    return psycopg2.connect(url)