import pyodbc

def get_connection():
    # Ajusta 'Server' si tu instancia tiene nombre, ej: localhost\SQLEXPRESS
    conn_str = (
        "Driver={SQL Server};"
        "Server=localhost;" 
        "Database=SurfFlow;"
        "UID=sa;"
        "PWD=123456789;"
        "Timeout=30;"
    )
    return pyodbc.connect(conn_str)