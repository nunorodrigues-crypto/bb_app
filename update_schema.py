import sqlite3

def update_db():
    conn = sqlite3.connect('babyconnect.db')
    c = conn.cursor()
    
    # 1. Criar Tabela de Mensagens (Para o Chat funcionar entre contas diferentes)
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_email TEXT NOT NULL,
            receiver_email TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Adicionar coluna de Pedidos Pendentes à tabela bookings
    try:
        c.execute("ALTER TABLE bookings ADD COLUMN pending_extension INTEGER DEFAULT 0")
        print("✅ Coluna 'pending_extension' adicionada.")
    except:
        print("ℹ️ Coluna 'pending_extension' já existia.")

    conn.commit()
    conn.close()
    print("✅ Base de dados atualizada com sucesso!")

if __name__ == "__main__":
    update_db()