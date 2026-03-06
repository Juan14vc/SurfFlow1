import psycopg2
import os

def get_connection():
    # PEGA AQUÍ la URL de Render (la que empieza con postgresql://)
    url = "postgresql://surfflow_db_n8n1_user:WUIsvcU1076u2AdlN9GBghroraT2eOhN@dpg-d6kbd84r85hc739jfkt0-a.ohio-postgres.render.com/surfflow_db_n8n1"
    return psycopg2.connect(url)
