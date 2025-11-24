import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = 'babyconnect.db'

def get_connection():
    return sqlite3.connect(DB_NAME)

# --- UTILIZADORES ---

def verify_login(email, password):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Query parametrizada (Segura)
        c.execute("SELECT id, name, role, email, location FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        if user:
            return {'id': user[0], 'name': user[1], 'role': user[2], 'email': user[3], 'location': user[4]}
        return None
    finally:
        conn.close()

def get_all_babysitters():
    conn = get_connection()
    try:
        # Pandas lê SQL diretamente
        query = "SELECT id, name as Nome, rating as Avaliação, price_per_hour as 'Preço/Hora', location as Localização, bio as Bio, photo_url as Foto FROM users WHERE role='Babysitter'"
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()

# --- PEDIDOS ---

def create_booking(client_id, babysitter_data, data_servico):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Obter ID da Babysitter (suporta dict ou pandas series)
        b_id = babysitter_data.get('id') if isinstance(babysitter_data, dict) else babysitter_data['id']

        # Converter objetos de data para string
        d_str = data_servico['data'].strftime('%Y-%m-%d')
        h_str = data_servico['hora'].strftime('%H:%M')
        
        c.execute('''
            INSERT INTO bookings (
                client_id, babysitter_id, service_date, start_time, duration, 
                children_count, children_ages, address, location_city, notes, 
                total_price, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmado')
        ''', (
            client_id, b_id, d_str, h_str, 
            data_servico['duracao'], data_servico['criancas'], data_servico['idades'], 
            data_servico['morada'], "Lisboa", data_servico['obs'], 
            data_servico['calculo']['total']
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Erro SQL: {e}")
        return False
    finally:
        conn.close()

def get_user_bookings(user_id, role):
    conn = get_connection()
    try:
        if role == 'Cliente':
            query = "SELECT b.*, u.name as Babysitter, u.id as babysitter_id, b.status as Status, b.total_price as Valor FROM bookings b JOIN users u ON b.babysitter_id = u.id WHERE b.client_id = ? ORDER BY b.service_date DESC"
        else:
            query = "SELECT b.*, u.name as Cliente, b.status as Status, b.total_price as Valor FROM bookings b JOIN users u ON b.client_id = u.id WHERE b.babysitter_id = ? ORDER BY b.service_date DESC"
            
        df = pd.read_sql_query(query, conn, params=(user_id,))
        
        if not df.empty:
            df['Data'] = pd.to_datetime(df['service_date']).dt.date
            # Tentar converter hora, gerindo erros se formato for diferente
            df['Hora'] = pd.to_datetime(df['start_time'], format='%H:%M', errors='coerce').dt.time
            
        return df
    finally:
        conn.close()