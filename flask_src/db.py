import os
import mysql.connector
from dotenv import load_dotenv
from pathlib import Path

# Carrega variáveis do .env
load_dotenv()

def conectar():
    try:
        ssl_path = Path.cwd() / os.getenv("SSL_CA")

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            ssl_disabled=False,
            ssl_ca=str(ssl_path)
        )

        print("✅ Conectado com sucesso!")

        return conn

    except mysql.connector.Error as erro:
        print("❌ Erro ao conectar:")
        print(erro)
        return None


# Teste de conexão
if __name__ == "__main__":
    conn = conectar()
    if conn:
        cursor = conn.cursor()
        print("Cursor criado com sucesso!")
        conn.close()