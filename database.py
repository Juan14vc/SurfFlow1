import psycopg2
import os

def get_connection():
    # REEMPLAZA esta URL con la "External Connection String" de tu Dashboard de Render
    # Se ve algo como: postgresql://user:password@endpoint.render.com/dbname
    url = "postgresql://surfflow_db_n8n1_user:WUIsvcU1076u2AdlN9GBghroraT2eOhN@dpg-d6kbd84r85hc739jfkt0-a.ohio-postgres.render.com/surfflow_db_n8n1" 
    return psycopg2.connect(url)
