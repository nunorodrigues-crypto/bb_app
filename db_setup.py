import sqlite3

def create_database():
    conn = sqlite3.connect('babyconnect.db')
    c = conn.cursor()

    # --- TABELA 1: UTILIZADORES ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            location TEXT,
            photo_url TEXT,
            bio TEXT,
            price_per_hour REAL,
            rating REAL DEFAULT 5.0,
            years_experience INTEGER
        )
    ''')

    # --- TABELA 2: PEDIDOS E SERVIÇOS ---
    # Adicionei: check_in_time, health_report, extension_minutes
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            babysitter_id INTEGER NOT NULL,
            
            service_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration INTEGER NOT NULL,
            
            children_count INTEGER,
            children_ages TEXT,
            
            address TEXT NOT NULL,
            location_city TEXT,
            notes TEXT,
            
            status TEXT DEFAULT 'Confirmado', 
            total_price REAL,
            
            -- Campos para gestão em tempo real
            check_in_time TEXT,
            health_report TEXT,
            extension_minutes INTEGER DEFAULT 0,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (babysitter_id) REFERENCES users (id)
        )
    ''')

    # --- SEED DATA (Utilizadores Iniciais) ---
    users = [
        ('admin@email.com', 'admin', 'Administrador', 'Admin', None, None, None, None),
        ('cliente@email.com', '123', 'Família Rodrigues', 'Cliente', '912345678', 'Lisboa', None, None),
        ('baba@email.com', '123', 'Maria Oliveira', 'Babysitter', '910000001', 'Lisboa', 'https://api.dicebear.com/7.x/avataaars/svg?seed=Maria', 'Educadora experiente.'),
        ('ana@email.com', '123', 'Ana Silva', 'Babysitter', '910000002', 'Porto', 'https://api.dicebear.com/7.x/avataaars/svg?seed=Ana', 'Enfermeira pediátrica.')
    ]
    
    # Inserção segura
    c.executemany('''
        INSERT OR IGNORE INTO users (email, password, name, role, phone, location, photo_url, bio, price_per_hour) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 35.0)
    ''', users)

    conn.commit()
    conn.close()
    print("✅ Base de dados criada/atualizada com sucesso!")

if __name__ == '__main__':
    create_database()