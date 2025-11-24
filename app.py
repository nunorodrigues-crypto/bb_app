import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time as dt_time
import time
import calendar
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from fpdf import FPDF
import base64
import re

# --- LIGAÇÃO AO BACKEND ---
import db_manager as db

# ==============================================================================
# 1. CONFIGURAÇÃO E ESTILOS
# ==============================================================================
st.set_page_config(
    page_title="BabyConnect", 
    page_icon="👶", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div.block-container {padding-top: 2rem;}
    div.stButton > button:first-child { font-weight: bold; }
    div.row-widget.stRadio > div { flex-direction: row; align-items: center; }
    
    button[kind="secondary"] { border: none; background: transparent; }
    
    .payment-option {
        border: 2px solid #e0e0e0; border-radius: 10px; padding: 15px;
        text-align: center; cursor: pointer; transition: all 0.3s;
    }
    .payment-option:hover { border-color: #FF4B4B; background-color: #f0f2f6; }
    
    /* ESTILOS DO CALENDÁRIO */
    .day-cell {
        border: 1px solid #f0f2f6; border-radius: 8px; padding: 8px;
        min-height: 110px; background-color: white; transition: all 0.2s;
    }
    .day-cell:hover { border-color: #FF4B4B; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .day-number { font-weight: bold; font-size: 14px; color: #333; margin-bottom: 5px; display: block; }
    .event-card {
        background-color: #e3f2fd; border-left: 3px solid #2196f3; color: #1565c0;
        padding: 4px; margin-top: 4px; border-radius: 4px; font-size: 11px;
        line-height: 1.2; text-align: left; cursor: pointer;
    }
    .event-card.past { background-color: #f5f5f5; border-left: 3px solid #9e9e9e; color: #616161; }
    .current-day { border: 2px solid #9b59b6 !important; background-color: #fbf6ff; }
    
    /* TABELA DO ADMIN */
    .stDataFrame { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LÓGICA DE NEGÓCIO E UTILITÁRIOS
# ==============================================================================
def validate_address(address):
    geolocator = Nominatim(user_agent="babyconnect_app_vfinal")
    try:
        location = geolocator.geocode(f"{address}, Portugal", timeout=10)
        return location
    except: return None

def get_distance_km(dest_coords):
    try:
        loures_coords = (38.8315, -9.1746)
        return geodesic(loures_coords, dest_coords).km
    except: return None 

def calcular_preco_total(babysitter_data, duracao_horas, location_obj):
    preco_hora = babysitter_data.get('Preço/Hora') if isinstance(babysitter_data, dict) else babysitter_data['Preço/Hora']
    custo_servico = preco_hora * duracao_horas
    
    dest_coords = (location_obj.latitude, location_obj.longitude)
    distancia_ida = get_distance_km(dest_coords)
    if distancia_ida is None: distancia_ida = 15.0 
    
    custo_deslocacao = (distancia_ida * 2) * 0.45
    total = custo_servico + custo_deslocacao
    
    return {
        "custo_servico": custo_servico, "distancia_ida": distancia_ida,
        "custo_deslocacao": custo_deslocacao, "total": total
    }

def calculate_time_remaining(booking_data):
    """Calcula tempo restante e progresso baseando-se no check-in real"""
    if not booking_data.get('check_in_time'): return 0, 0, "Não iniciado"
    
    start = booking_data['check_in_time'] 
    duration_min = (booking_data['duration'] * 60) + booking_data.get('extension_minutes', 0)
    end_time = start + timedelta(minutes=duration_min)
    now = datetime.now()
    
    remaining = end_time - now
    total_seconds = remaining.total_seconds()
    
    if total_seconds <= 0: return 0, 1.0, "Terminado"
    
    minutes_left = int(total_seconds / 60)
    total_duration_sec = duration_min * 60
    progress = 1.0 - (total_seconds / total_duration_sec)
    
    return minutes_left, progress, end_time.strftime('%H:%M')

def create_pdf_invoice(service_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 10, "BabyConnect - Fatura Recibo", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, "Conectando Familias e Babysitters", ln=True, align="C")
    pdf.line(10, 30, 200, 30)
    pdf.ln(20)
    pdf.set_font("Arial", "B", 12)
    baba_nome = service_data.get('Babysitter') or service_data.get('BabysitterName') or "N/A"
    cli_nome = service_data.get('Cliente') or service_data.get('ClientName') or st.session_state.get('user_name')
    
    pdf.cell(0, 10, f"Babysitter: {baba_nome}", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Cliente: {cli_nome}", ln=True)
    
    data_serv = service_data.get('Data') or service_data.get('service_date')
    if not isinstance(data_serv, str): data_serv = data_serv.strftime('%d/%m/%Y')
    
    pdf.cell(0, 10, f"Data do Servico: {data_serv}", ln=True)
    local_str = str(service_data.get('Local', 'N/A')).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, f"Local: {local_str}", ln=True)
    pdf.ln(10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(140, 10, "Descricao", 1, 0, 'L', 1)
    pdf.cell(50, 10, "Valor (EUR)", 1, 1, 'R', 1)
    pdf.cell(140, 10, "Servico de Babysitting + Deslocacao", 1, 0, 'L')
    pdf.cell(50, 10, f"{service_data.get('Valor', 0):.2f}", 1, 1, 'R')
    pdf.set_font("Arial", "B", 12)
    pdf.cell(140, 10, "TOTAL", 1, 0, 'R')
    pdf.cell(50, 10, f"{service_data.get('Valor', 0):.2f} EUR", 1, 1, 'R')
    pdf.ln(20)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, "Obrigado pela preferencia!", ln=True, align="C")
    return pdf.output(dest='S').encode('latin-1')

def check_safety_rules(text, history_context=""):
    full_text = history_context + " " + text
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', full_text):
        return False, "Proibido partilhar emails."
    digits_only = re.sub(r'\D', '', full_text)
    if len(digits_only) >= 9:
        if digits_only[0] in ['9', '2', '3']:
             return False, "Proibido partilhar contactos telefónicos."
    return True, ""

# ==============================================================================
# 3. DADOS E STATE
# ==============================================================================
keys_defaults = [
    ('logged_in', False), ('user_role', None), ('user_name', None), 
    ('user_email', None), ('user_id', None),
    ('current_page', "Dashboard"), ('booking_step', 1), ('temp_booking_data', {}),
    ('active_chat_user', None), ('checkout_data', None), 
    ('cal_year', datetime.now().year), ('cal_month', datetime.now().month),
    ('selected_history_service', None), ('mensagens', [])
]
for k, v in keys_defaults:
    if k not in st.session_state: st.session_state[k] = v

# ==============================================================================
# 4. SISTEMA DE NAVEGAÇÃO
# ==============================================================================
def go_to_page(page_name, reset_step=False):
    st.session_state['current_page'] = page_name
    if reset_step:
        st.session_state['booking_step'] = 1
        st.session_state['temp_booking_data'] = {}
    st.rerun()

def nav_callback():
    new_page = st.session_state['nav_radio']
    st.session_state['current_page'] = new_page
    if new_page == "Dashboard":
        st.session_state['booking_step'] = 1
        st.session_state['temp_booking_data'] = {}

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("👶 BabyConnect")
        st.markdown("### Bem-vindo ao portal")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)
        if submit:
            user_data = db.verify_login(email, password)
            if user_data:
                st.session_state['logged_in'] = True
                st.session_state['user_email'] = user_data['email']
                st.session_state['user_role'] = user_data['role']
                st.session_state['user_name'] = user_data['name']
                st.session_state['user_id'] = user_data['id'] 
                go_to_page("Dashboard", reset_step=True)
            else: st.error("Credenciais inválidas.")

def render_navbar(menu_options):
    with st.container():
        col_nav, col_user = st.columns([3, 1.5]) 
        with col_nav:
            try: idx = menu_options.index(st.session_state['current_page'])
            except ValueError: idx = 0 
            st.radio("Nav", menu_options, horizontal=True, label_visibility="collapsed", key="nav_radio", index=idx, on_change=nav_callback)
        with col_user:
            c_name, c_notif, c_logout = st.columns([2, 1, 1])
            c_name.write(f"👤 **{st.session_state['user_name'].split()[0]}**")
            c_notif.write("")
            if c_logout.button("Sair"): st.session_state['logged_in'] = False; st.rerun()
        st.divider()
    if st.session_state['current_page'] != "Dashboard" and st.session_state['current_page'] not in menu_options:
        if st.button("⬅ Voltar ao Dashboard"): go_to_page("Dashboard", reset_step=True)

# ==============================================================================
# 5. DASHBOARDS (COM TEMPO REAL E EXTENSÕES)
# ==============================================================================
def page_dashboard_cliente():
    st.header(f"Olá, {st.session_state['user_name']}")
    
    # --- O CÓDIGO TEM DE ESTAR ALINHADO AQUI ---
    # VERIFICAR SE HÁ MENSAGENS (Notificação)
    try:
        conn = db.get_connection()
        # A linha que deu erro tem de estar encostada a este nível de indentação
        msgs = pd.read_sql("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 1", conn)
        conn.close()
        
        if not msgs.empty:
            # ... resto da lógica ...
            pass
    except Exception:
        pass
    
    # 1. VERIFICAR SE EXISTE SERVIÇO EM CURSO
    active_job = db.get_upcoming_or_active_booking(st.session_state['user_id'], 'Cliente')
    
    if active_job and active_job['status'] == 'Em Curso':
        mins_left, progress, end_str = calculate_time_remaining(active_job)
        
        # --- CÁLCULOS FINANCEIROS ---
        pending = active_job.get('pending_extension', 0)
        extra_min = active_job.get('extension_minutes', 0)
        total_price = active_job.get('total_price', 0.0)
        
        # Card Principal (Timer)
        with st.container(border=True):
            col_timer, col_actions = st.columns([1.5, 1])
            with col_timer:
                st.subheader("Monitorização em Tempo Real")
                st.markdown(f"<h1 style='color:#FF4B4B; margin:0'>{mins_left} min</h1>", unsafe_allow_html=True)
                st.caption(f"Previsão de fim: {end_str}")
                st.progress(max(0.0, min(1.0, progress)))
                
                # [NOVO] CARD DE CONFIRMAÇÃO DE PAGAMENTO
                # Só aparece se houver extensões aprovadas
                if extra_min > 0:
                    st.markdown("---")
                    st.success(f"✅ **Extensão de +{extra_min} min Confirmada!**")
                    with st.expander("💳 Recibo Atualizado (Débito Automático)", expanded=True):
                        c_a, c_b = st.columns(2)
                        c_a.write("Total Base:")
                        c_b.write(f"€ {(total_price - (extra_min/60)*10):.2f}") # Estimativa base
                        
                        c_a.write(f"**Extra (+{extra_min} min):**")
                        c_b.write(f"**€ {((extra_min/60)*10):.2f}**")
                        
                        st.divider()
                        c_a.write("**TOTAL PAGO:**")
                        c_b.write(f"**€ {total_price:.2f}**")

            with col_actions:
                st.markdown("### Ações")
                
                if st.button("💬 Chat com Babysitter", type="primary", use_container_width=True):
                    st.session_state['active_chat_user'] = active_job['BabysitterEmail']
                    st.session_state['current_page'] = "Mensagens"
                    st.rerun()
                
                st.divider()
                
                # BOTÃO DE PEDIDO
                if pending > 0:
                     st.warning(f"⏳ Aguardando aprovação (+{pending} min)")
                     st.caption("O débito será feito após aceitação.")
                else:
                    st.write("**Precisa de mais tempo?**")
                    preco_hora = active_job.get('price_per_hour', 10.0)
                    custo_15min = preco_hora / 4
                    
                    if st.button(f"➕ Pedir +15 min (+€{custo_15min:.2f})", use_container_width=True):
                        db.request_extension_db(active_job['id'], 15)
                        st.toast("Pedido enviado!")
                        time.sleep(1)
                        st.rerun()

        st.markdown("---")
        
        # AUTO-REFRESH (A cada 10s verifica se a Babysitter aceitou)
        time.sleep(10)
        st.rerun()

    # 2. DASHBOARD NORMAL (Sem serviço ativo)
    else:
        df = db.get_user_bookings(st.session_state['user_id'], 'Cliente')
        if df.empty:
            pedidos_passados = pd.DataFrame(); pedidos_futuros = pd.DataFrame()
            count_passados = 0; count_futuros = 0
        else:
            hoje = datetime.now().date()
            df['Data'] = pd.to_datetime(df['service_date']).dt.date
            pedidos_futuros = df[df['Data'] >= hoje]
            pedidos_passados = df[df['Data'] < hoje]
            count_passados = len(pedidos_passados); count_futuros = len(pedidos_futuros)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Serviços Realizados", count_passados)
        c2.metric("Pedidos Futuros", count_futuros)
        c3.metric("Mensagens", "0") 

        col_new, col_history = st.columns(2)
        with col_new:
            with st.container(border=True):
                st.subheader("➕ Novo Pedido Rápido")
                st.write("Definir data e encontrar babysitter.")
                if st.button("Criar Novo Pedido", use_container_width=True, type="primary"): 
                    go_to_page("Novo Serviço", reset_step=True) 
        
        with col_history:
            with st.container(border=True):
                st.subheader("📜 Histórico Recente")
                if pedidos_passados.empty: st.info("Ainda não tem histórico.")
                else:
                    for idx, row in pedidos_passados.head(3).iterrows():
                        with st.container(border=True):
                            col_info, col_act = st.columns([3, 1])
                            with col_info:
                                st.write(f"**{row['Babysitter']}**")
                                st.caption(f"📅 {row['Data'].strftime('%d/%m/%Y')} | € {row['Valor']:.2f}")
                            with col_act:
                                if st.button("📄", key=f"hist_{idx}"):
                                    st.session_state['selected_history_service'] = row.to_dict()
                                    go_to_page("Detalhes Serviço")
        
        st.markdown("---")
        st.subheader("📅 Próximos Pedidos")
        if pedidos_futuros.empty: st.info("Não tem pedidos agendados.")
        else: st.dataframe(pedidos_futuros[['Data', 'Hora', 'Babysitter', 'Status', 'Valor']], use_container_width=True, hide_index=True)

    # 2. DASHBOARD NORMAL
    df = db.get_user_bookings(st.session_state['user_id'], 'Cliente')
    if df.empty:
        pedidos_passados = pd.DataFrame(); pedidos_futuros = pd.DataFrame()
        count_passados = 0; count_futuros = 0
    else:
        hoje = datetime.now().date()
        df['Data'] = pd.to_datetime(df['service_date']).dt.date
        pedidos_futuros = df[df['Data'] >= hoje]
        pedidos_passados = df[df['Data'] < hoje]
        count_passados = len(pedidos_passados); count_futuros = len(pedidos_futuros)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Serviços Realizados", count_passados)
    c2.metric("Pedidos Futuros", count_futuros)
    c3.metric("Mensagens", "0") 

    col_new, col_history = st.columns(2)
    with col_new:
        with st.container(border=True):
            st.subheader("➕ Novo Pedido Rápido")
            st.write("Definir data e encontrar babysitter.")
            if st.button("Criar Novo Pedido", use_container_width=True, type="primary"): 
                go_to_page("Novo Serviço", reset_step=True) 
    
    with col_history:
        with st.container(border=True):
            st.subheader("📜 Histórico Recente")
            if pedidos_passados.empty: st.info("Ainda não tem histórico.")
            else:
                for idx, row in pedidos_passados.head(3).iterrows():
                    with st.container(border=True):
                        col_info, col_act = st.columns([3, 1])
                        with col_info:
                            st.write(f"**{row['Babysitter']}**")
                            st.caption(f"📅 {row['Data'].strftime('%d/%m/%Y')} | € {row['Valor']:.2f}")
                        with col_act:
                            if st.button("📄 Detalhes", key=f"hist_{idx}"):
                                st.session_state['selected_history_service'] = row.to_dict()
                                go_to_page("Detalhes Serviço")
    
    st.markdown("---")
    st.subheader("📅 Próximos Pedidos")
    if pedidos_futuros.empty: st.info("Não tem pedidos agendados.")
    else: st.dataframe(pedidos_futuros[['Data', 'Hora', 'Babysitter', 'Status', 'Valor']], use_container_width=True, hide_index=True)


def page_dashboard_babysitter():
    st.header(f"🧸 Painel Babysitter: {st.session_state['user_name']}")
    
    conn = db.get_connection()
    msgs = pd.read_sql("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 1", conn)
    conn.close()
    
    if not msgs.empty:
        last_msg_time = pd.to_datetime(msgs.iloc[0]['timestamp'])
        # Se a mensagem tem menos de 2 minutos e não fui eu que enviei
        if (datetime.now() - last_msg_time).total_seconds() < 120 and msgs.iloc[0]['sender_email'] != st.session_state['user_email']:
             st.info(f"📨 **Nova mensagem de {msgs.iloc[0]['sender_email']}!** Vá ao menu Mensagens.")
    # 1. BUSCAR DADOS (Query fresca)
    active_job = db.get_upcoming_or_active_booking(st.session_state['user_id'], 'Babysitter')
    
    if active_job:
        status = active_job['status']
        
        # --- AQUI ESTÁ A CORREÇÃO DO POP-UP ---
        # Verificamos sempre se há pedidos pendentes, independentemente do status
        pending = active_job.get('pending_extension', 0)
        
        if pending > 0:
            # POP-UP VISUAL DE ALERTA
            with st.container(border=True):
                st.error(f"🔔 **PEDIDO URGENTE:** Os pais querem +{pending} minutos!")
                c1, c2 = st.columns(2)
                if c1.button("✅ ACEITAR MUDANÇA", use_container_width=True):
                    custo_extra = (pending / 60) * 10.0
                    db.resolve_extension_db(active_job['id'], True, pending, custo_extra)
                    st.success("Aceite!"); time.sleep(1); st.rerun()
                if c2.button("❌ RECUSAR MUDANÇA", use_container_width=True):
                    db.resolve_extension_db(active_job['id'], False, 0, 0)
                    st.error("Recusado."); time.sleep(1); st.rerun()
        # ---------------------------------------

        # A) PRÉ-SERVIÇO
        if status == 'Confirmado':
            job_dt = datetime.combine(active_job['Data'], active_job['Hora'])
            diff = (job_dt - datetime.now()).total_seconds() / 60 
            
            with st.container(border=True):
                st.subheader("🚀 Próximo Serviço")
                st.write(f"**Cliente:** {active_job.get('ClientName')}")
                st.write(f"**Horário:** {active_job['Hora'].strftime('%H:%M')}")
                
                if diff <= 15: 
                    st.success("Pode iniciar.")
                    with st.form("checkin_form"):
                        febre = st.toggle("Febre?")
                        marcas = st.text_area("Marcas?", placeholder="Descreva...")
                        if st.form_submit_button("▶️ INICIAR", type="primary", use_container_width=True):
                            db.start_service_db(active_job['id'], f"Febre:{febre}|Marcas:{marcas}")
                            st.rerun()
                else: st.warning(f"Check-in brevemente ({int(diff)} min).")
            
            # Refresh lento (30s) enquanto espera
            time.sleep(30)
            st.rerun()

        # B) EM SERVIÇO
        elif status == 'Em Curso':
            mins_left, progress, end_str = calculate_time_remaining(active_job)
            st.markdown(f"""
            <div style="background-color: #e3f2fd; padding: 20px; border-radius: 10px; border: 2px solid #2196f3; text-align: center; margin-bottom: 20px;">
                <h2 style="color: #1565c0; margin:0;">EM SERVIÇO 🟢</h2>
                <h1 style="font-size: 50px; margin: 0;">{mins_left} min</h1>
                <p>Restantes • Termina às {end_str}</p>
            </div>
            """, unsafe_allow_html=True)
            st.progress(max(0.0, min(1.0, progress)))
            
            if st.button("💬 Chat com Pais", use_container_width=True):
                st.session_state['active_chat_user'] = active_job['ClientEmail']
                st.session_state['current_page'] = "Mensagens"
                st.rerun()
            
            st.divider()
            
            # --- CORREÇÃO: REFRESH RÁPIDO (5s) ---
            # Isto garante que ela vê os pedidos de extensão quase logo que acontecem
            time.sleep(5)
            st.rerun()

    # 2. AGENDA
    df = db.get_user_bookings(st.session_state['user_id'], 'Babysitter')
    if df.empty: st.info("Sem agenda.")
    else: 
        cols = [c for c in ['Data', 'Hora', 'Cliente', 'Status', 'Local', 'Valor'] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True)


def page_admin_dashboard():
    st.header("🔐 Painel Admin Global")
    conn = db.get_connection()
    df_users = pd.read_sql("SELECT * FROM users", conn)
    df_bookings = pd.read_sql("SELECT * FROM bookings", conn)
    conn.close()
    
    c1, c2 = st.columns(2)
    c1.metric("Utilizadores Totais", len(df_users))
    c2.metric("Reservas Totais", len(df_bookings))
    
    st.markdown("---")
    st.subheader("Todas as Transações")
    st.dataframe(df_bookings, use_container_width=True)

# ==============================================================================
# 6. WIZARD DE PEDIDOS
# ==============================================================================
def page_novo_servico():
    step = st.session_state['booking_step']
    
    if step == 1:
        st.header(" Passo 1 de 3: Detalhes do Serviço")
        st.progress(33)
        with st.form("form_step1"):
            c1, c2 = st.columns(2)
            with c1: dt = st.date_input("Data de Início", min_value=datetime.now().date()); hr = st.time_input("Hora de Início")
            with c2: dur = st.number_input("Duração Estimada (horas)", min_value=1, value=3, step=1)
            c3, c4 = st.columns(2)
            with c3: kids = st.number_input("Número de Crianças", min_value=1, value=1)
            with c4: idades = st.text_input("Idades das Crianças", placeholder="Ex: 3 anos, 5 anos")
            morada_rua = st.text_input("Local do Serviço (Rua e Número)")
            morada_cidade = st.text_input("Cidade / Localidade", value="Lisboa")
            obs = st.text_area("Observações Adicionais")
            if st.form_submit_button("Validar e Procurar Babysitters ➡", type="primary", use_container_width=True):
                if not morada_rua or not morada_cidade: st.error("Preencha a morada completa.")
                else:
                    full_address = f"{morada_rua}, {morada_cidade}"
                    with st.spinner("A validar morada..."): loc_obj = validate_address(full_address)
                    if loc_obj is None: st.error("❌ Morada inválida.")
                    else:
                        st.session_state['temp_booking_data'] = {'data': dt, 'hora': hr, 'duracao': dur, 'criancas': kids, 'idades': idades, 'morada': full_address, 'obs': obs, 'location_obj': loc_obj}
                        st.session_state['booking_step'] = 2
                        st.rerun()

    elif step == 2:
        data_pedido = st.session_state['temp_booking_data']
        st.header("Passo 2 de 3: Escolher Babysitter")
        st.progress(66)
        if st.button("⬅ Voltar"): st.session_state['booking_step'] = 1; st.rerun()
        st.divider()
        disponiveis = db.get_all_babysitters()
        if disponiveis.empty: st.warning("Não existem babysitters registadas.")
        else:
            for idx, row in disponiveis.iterrows():
                with st.container(border=True):
                    c_img, c_info, c_btn = st.columns([1, 4, 1.5])
                    foto = row['Foto'] if row['Foto'] else "https://via.placeholder.com/150"
                    with c_img: st.image(foto, width=100)
                    with c_info: 
                        primeiro_nome = row['Nome'].split()[0]
                        st.subheader(primeiro_nome); st.write(f"📝 *{row['Bio']}*"); st.caption(f"📍 {row['Localização']} | ⭐ {row['Avaliação']}")
                    with c_btn:
                        st.write(""); st.write("")
                        if st.button("Selecionar ✅", key=f"select_{idx}", type="primary", use_container_width=True):
                            calculo = calcular_preco_total(row.to_dict(), data_pedido['duracao'], data_pedido['location_obj'])
                            st.session_state['checkout_data'] = {'babysitter': row.to_dict(), 'babysitter_primeiro_nome': primeiro_nome, **data_pedido, 'calculo': calculo}
                            st.session_state['booking_step'] = 3
                            st.rerun()

    elif step == 3:
        st.header("Passo 3 de 3: Pagamento Seguro")
        st.progress(100)
        if st.button("⬅ Voltar"): st.session_state['booking_step'] = 2; st.rerun()
        data = st.session_state.get('checkout_data')
        if not data: st.error("Erro de dados."); st.stop()
        calc = data['calculo']
        baba_nome = data['babysitter_primeiro_nome']
        c_res, c_pag = st.columns([1.5, 2])
        with c_res:
            with st.container(border=True):
                st.subheader("Resumo")
                st.write(f"**Babysitter:** {baba_nome}")
                st.write(f"**Data:** {data['data'].strftime('%d/%m/%Y')} às {data['hora'].strftime('%H:%M')}")
                st.write(f"**Local:** {data['morada']}")
                st.divider()
                st.write(f"Serviço: € {calc['custo_servico']:.2f}")
                st.write(f"Deslocação: € {calc['custo_deslocacao']:.2f}")
                st.markdown(f"### Total: € {calc['total']:.2f}")
        with c_pag:
            st.subheader("Pagamento")
            st.radio("Método", ["MBWAY", "Cartão de Crédito"], horizontal=True)
            st.write("")
            if st.button(f"Pagar € {calc['total']:.2f} e Confirmar", type="primary", use_container_width=True):
                with st.spinner("A processar pagamento..."):
                    time.sleep(1) 
                    sucesso = db.create_booking(st.session_state['user_id'], data['babysitter'], data)
                    if sucesso: st.balloons(); st.success("Reserva confirmada!"); time.sleep(2); go_to_page("Dashboard", reset_step=True)
                    else: st.error("Erro ao gravar na base de dados.")

# ==============================================================================
# 7. CALENDÁRIO
# ==============================================================================
def page_calendario():
    c_head, c_btn = st.columns([3, 1])
    role = st.session_state['user_role']
    c_head.title("Calendário")
    df = db.get_user_bookings(st.session_state['user_id'], role)
    if not df.empty: df['Data'] = pd.to_datetime(df['service_date']).dt.date
    
    cal_year = st.session_state['cal_year']
    cal_month = st.session_state['cal_month']
    cal = calendar.monthcalendar(cal_year, cal_month)
    hoje = datetime.now()

    cp, cd, cn = st.columns([1, 6, 1])
    if cp.button("←"): 
        st.session_state['cal_month'] -= 1
        if st.session_state['cal_month'] < 1: st.session_state['cal_month']=12; st.session_state['cal_year']-=1
        st.rerun()
    cd.markdown(f"<h3 style='text-align: center'>{calendar.month_name[cal_month]} {cal_year}</h3>", unsafe_allow_html=True)
    if cn.button("→"):
        st.session_state['cal_month'] += 1
        if st.session_state['cal_month'] > 12: st.session_state['cal_month']=1; st.session_state['cal_year']+=1
        st.rerun()

    cols_header = st.columns(7)
    for i, d in enumerate(["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]): cols_header[i].write(f"**{d}**")

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0: st.markdown("<div style='min-height: 80px;'></div>", unsafe_allow_html=True)
                else:
                    data_atual = datetime(cal_year, cal_month, day).date()
                    eventos_html = ""
                    if not df.empty:
                        eventos_dia = df[df['Data'] == data_atual]
                        for _, evt in eventos_dia.iterrows():
                            nome = evt.get('Babysitter') if role == 'Cliente' else evt.get('Cliente')
                            nome = nome.split()[0] if nome else "Serviço"
                            eventos_html += f"<div class='event-card'>{nome}</div>"
                    st.markdown(f"<div class='day-cell'><span class='day-number'>{day}</span>{eventos_html}</div>", unsafe_allow_html=True)

# ==============================================================================
# 8. MENSAGENS (AGORA LIGADO À BASE DE DADOS)
# ==============================================================================
def page_mensagens():
    st.header("Mensagens")
    col_contacts, col_chat = st.columns([1, 2.5])
    user_email = st.session_state['user_email']
    
    contacts = set()
    if st.session_state['active_chat_user']: 
        contacts.add(st.session_state['active_chat_user'])
    
    with col_contacts:
        with st.container(border=True):
            st.subheader("Conversas")
            if not contacts: st.info("Inicie pelo Dashboard.")
            for c in contacts:
                if st.button(f"📧 {c}", key=c, use_container_width=True): 
                    st.session_state['active_chat_user'] = c; st.rerun()

    with col_chat:
        active = st.session_state['active_chat_user']
        chat_container = st.container(border=True, height=550)
        
        if active:
            # LER DA DB
            historico = db.get_chat_history_db(user_email, active)
            
            with chat_container:
                st.write(f"**A falar com:** {active}")
                if not historico: st.caption("Inicie a conversa...")
                
                for sender, content, ts in historico:
                    align = "user" if sender == user_email else "assistant"
                    with st.chat_message(align): 
                        st.write(content)
                        # Mostra hora (HH:MM)
                        ts_str = str(ts)
                        hora = ts_str[11:16] if len(ts_str) > 16 else ""
                        st.caption(hora)

            # ENVIAR
            if prompt := st.chat_input("Escreva aqui..."):
                safe, err = check_safety_rules(prompt, "")
                if safe:
                    db.send_message_db(user_email, active, prompt)
                    st.rerun()
                else: st.error(err)
            
            # --- CORREÇÃO: AUTO-REFRESH DO CHAT ---
            # Isto faz o chat atualizar sozinho a cada 2 segundos
            time.sleep(2)
            st.rerun()

        else:
            with chat_container:
                st.markdown("<div style='text-align:center;margin-top:100px;color:#ccc'><h3>Selecione uma conversa</h3></div>", unsafe_allow_html=True)
def page_editar_perfil():
    st.header("⚙️ Configurações de Perfil")
    c1, c2 = st.columns(2)
    with c1: st.text_input("Nome", value=st.session_state['user_name']); st.text_input("Email", value=st.session_state['user_email'], disabled=True)
    with c2: st.text_input("Telefone", "+351 ..."); st.button("Guardar Alterações")

# ==============================================================================
# 9. ROUTER
# ==============================================================================
if not st.session_state['logged_in']:
    login_page()
else:
    role = st.session_state['user_role']
    menus = ["Dashboard", "Calendário", "Mensagens", "Editar Perfil"] if role != 'Admin' else ["Dashboard"]
    render_navbar(menus)
    pg = st.session_state['current_page']
    if pg == "Dashboard":
        if role == 'Cliente': page_dashboard_cliente()
        elif role == 'Babysitter': page_dashboard_babysitter()
        else: page_admin_dashboard()
    elif pg == "Novo Serviço": page_novo_servico()
    elif pg == "Detalhes Serviço": page_detalhes_servico()
    elif pg == "Calendário": page_calendario()
    elif pg == "Mensagens": page_mensagens()
    elif pg == "Editar Perfil": page_editar_perfil()