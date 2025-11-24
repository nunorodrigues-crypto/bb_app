import sqlite3

def add_column():
    conn = sqlite3.connect('babyconnect.db')
    c = conn.cursor()
    try:
        # Adiciona coluna para guardar pedidos de extensão (minutos) pendentes
        c.execute("ALTER TABLE bookings ADD COLUMN pending_extension INTEGER DEFAULT 0")
        conn.commit()
        print("✅ Coluna 'pending_extension' adicionada com sucesso!")
    except Exception as e:
        print(f"Nota: {e} (Provavelmente a coluna já existe)")
    finally:
        conn.close()

if __name__ == '__main__':
    add_column()