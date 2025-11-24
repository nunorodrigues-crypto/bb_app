import sqlite3

def fix_database():
    print("🔧 A iniciar reparação da Base de Dados...")
    conn = sqlite3.connect('babyconnect.db')
    c = conn.cursor()
    
    # 1. Tentar adicionar a coluna pending_extension
    try:
        c.execute("ALTER TABLE bookings ADD COLUMN pending_extension INTEGER DEFAULT 0")
        print("✅ Coluna 'pending_extension' adicionada com sucesso!")
    except sqlite3.OperationalError:
        print("ℹ️ A coluna 'pending_extension' já existia. (OK)")

    # 2. Verificar se a tabela de mensagens existe
    try:
        c.execute("SELECT count(*) FROM messages")
        print("ℹ️ Tabela 'messages' já existe. (OK)")
    except sqlite3.OperationalError:
        print("⚠️ Tabela 'messages' em falta. A criar...")
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_email TEXT NOT NULL,
                receiver_email TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Tabela 'messages' criada.")

    conn.commit()
    conn.close()
    print("🚀 Base de dados reparada! Podes reiniciar a App.")

if __name__ == "__main__":
    fix_database()