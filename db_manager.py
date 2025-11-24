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

def get_upcoming_or_active_booking(user_id, role):
    conn = get_connection()
    try:
        # Adicionei 'pending_extension' e 'u.email' às queries
        if role == 'Babysitter':
            query = """
            SELECT b.*, u.name as ClientName, u.email as ClientEmail, u.photo_url as ClientPhoto 
            FROM bookings b 
            JOIN users u ON b.client_id = u.id 
            WHERE b.babysitter_id = ? 
            AND b.status IN ('Confirmado', 'Em Curso')
            ORDER BY b.service_date ASC, b.start_time ASC LIMIT 1
            """
        else: # Cliente
            query = """
            SELECT b.*, u.name as BabysitterName, u.email as BabysitterEmail, u.price_per_hour, u.photo_url as BabysitterPhoto
            FROM bookings b 
            JOIN users u ON b.babysitter_id = u.id 
            WHERE b.client_id = ? 
            AND b.status IN ('Confirmado', 'Em Curso')
            ORDER BY b.service_date ASC, b.start_time ASC LIMIT 1
            """
        
        df = pd.read_sql_query(query, conn, params=(user_id,))
        if not df.empty:
            row = df.iloc[0].to_dict()
            row['Data'] = pd.to_datetime(row['service_date']).date()
            row['Hora'] = pd.to_datetime(row['start_time'], format='%H:%M').time()
            if row['check_in_time']:
                row['check_in_time'] = pd.to_datetime(row['check_in_time'])
            return row
        return None
    finally:
        conn.close()

# --- NOVAS FUNÇÕES DE EXTENSÃO ---

def request_extension_db(booking_id, minutes):
    """Pais pedem extensão (fica pendente)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE bookings SET pending_extension = ? WHERE id=?", (minutes, booking_id))
        conn.commit()
        return True
    finally:
        conn.close()

def resolve_extension_db(booking_id, decision, extra_minutes, cost_increase):
    """Babysitter decide: decision=True (Aceita) ou False (Recusa)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        if decision:
            # Aceitou: Soma ao tempo oficial, soma ao preço e limpa o pendente
            c.execute("""
                UPDATE bookings 
                SET extension_minutes = extension_minutes + ?, 
                    total_price = total_price + ?,
                    pending_extension = 0
                WHERE id=?
            """, (extra_minutes, cost_increase, booking_id))
        else:
            # Recusou: Apenas limpa o pendente
            c.execute("UPDATE bookings SET pending_extension = 0 WHERE id=?", (booking_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def get_user_bookings(user_id, role):
    conn = get_connection()
    try:
        # Garante que usamos aliases SQL para facilitar o display no frontend
        if role == 'Cliente':
            query = """
                SELECT b.service_date as Data, b.start_time as Hora, 
                       u.name as Babysitter, b.status as Status, 
                       b.total_price as Valor, b.address as Local
                FROM bookings b 
                JOIN users u ON b.babysitter_id = u.id 
                WHERE b.client_id = ? 
                ORDER BY b.service_date DESC, b.start_time DESC
            """
        else:
            query = """
                SELECT b.service_date as Data, b.start_time as Hora, 
                       u.name as Cliente, b.status as Status, 
                       b.total_price as Valor, b.address as Local
                FROM bookings b 
                JOIN users u ON b.client_id = u.id 
                WHERE b.babysitter_id = ? 
                ORDER BY b.service_date DESC, b.start_time DESC
            """
            
        df = pd.read_sql_query(query, conn, params=(user_id,))
        
        if not df.empty:
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            df['Hora'] = pd.to_datetime(df['Hora'], format='%H:%M', errors='coerce').dt.time
            
        return df
    finally:
        conn.close()

def start_service_db(booking_id, health_report):
    """A Babysitter dá início ao serviço"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        c.execute("""
            UPDATE bookings 
            SET status='Em Curso', check_in_time=?, health_report=? 
            WHERE id=?
        """, (now, health_report, booking_id))
        conn.commit()
        return True
    except Exception as e:
        print(e); return False
    finally:
        conn.close()

def extend_service_db(booking_id, extra_minutes, cost_increase):
    """O Cliente adiciona tempo extra"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE bookings 
            SET extension_minutes = extension_minutes + ?, 
                total_price = total_price + ? 
            WHERE id=?
        """, (extra_minutes, cost_increase, booking_id))
        conn.commit()
        return True
    except Exception as e:
        print(e); return False
    finally:
        conn.close()

# --- FUNÇÕES DE CHAT (NOVO) ---
def send_message_db(sender, receiver, content):
    """Grava mensagem na base de dados"""
    conn = get_connection()
    try:
        conn.execute("INSERT INTO messages (sender_email, receiver_email, content) VALUES (?, ?, ?)", 
                     (sender, receiver, content))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro chat: {e}")
        return False
    finally:
        conn.close()

def get_chat_history_db(user1, user2):
    """Recupera conversa entre duas pessoas"""
    conn = get_connection()
    try:
        query = """
            SELECT sender_email, content, timestamp 
            FROM messages 
            WHERE (sender_email = ? AND receiver_email = ?) 
               OR (sender_email = ? AND receiver_email = ?)
            ORDER BY timestamp ASC
        """
        cursor = conn.execute(query, (user1, user2, user2, user1))
        return cursor.fetchall()
    finally:
        conn.close()

# --- FUNÇÕES DE EXTENSÃO DE TEMPO (NOVO) ---
def request_extension_db(booking_id, minutes):
    """Cliente pede tempo"""
    conn = get_connection()
    try:
        conn.execute("UPDATE bookings SET pending_extension = ? WHERE id=?", (minutes, booking_id))
        conn.commit()
    finally:
        conn.close()

def resolve_extension_db(booking_id, decision, extra_minutes, cost_increase):
    """Babysitter aceita (True) ou recusa (False)"""
    conn = get_connection()
    try:
        if decision:
            # Aceitou: Atualiza tempo, preço e limpa o pendente
            conn.execute("""
                UPDATE bookings 
                SET extension_minutes = extension_minutes + ?, 
                    total_price = total_price + ?,
                    pending_extension = 0
                WHERE id=?
            """, (extra_minutes, cost_increase, booking_id))
        else:
            # Recusou: Só limpa o pendente
            conn.execute("UPDATE bookings SET pending_extension = 0 WHERE id=?", (booking_id,))
        conn.commit()
    finally:
        conn.close()