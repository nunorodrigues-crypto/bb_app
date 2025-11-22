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
import re  # Importação para Regex (Segurança do Chat)

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
# 2. LÓGICA DE NEGÓCIO, PDF E SEGURANÇA (BLINDADO)
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
    preco_hora = babysitter_data['Preço/Hora']
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

def get_available_babysitters(date_selected):
    df_agendas = st.session_state['agendamentos']
    df_babas = st.session_state['babysitters']
    ocupadas_no_dia = df_agendas[df_agendas['Data'] == date_selected]['Babysitter'].unique()
    disponiveis = df_babas[~df_babas['Nome'].isin(ocupadas_no_dia)]
    return disponiveis

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
    pdf.cell(0, 10, f"Babysitter: {service_data['Babysitter']}", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Cliente: {service_data['Cliente']}", ln=True)
    pdf.cell(0, 10, f"Data do Servico: {service_data['Data'].strftime('%d/%m/%Y')}", ln=True)
    local_str = str(service_data.get('Local', 'N/A')).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, f"Local: {local_str}", ln=True)
    pdf.ln(10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(140, 10, "Descricao", 1, 0, 'L', 1)
    pdf.cell(50, 10, "Valor (EUR)", 1, 1, 'R', 1)
    pdf.cell(140, 10, "Servico de Babysitting + Deslocacao", 1, 0, 'L')
    pdf.cell(50, 10, f"{service_data['Valor']:.2f}", 1, 1, 'R')
    pdf.set_font("Arial", "B", 12)
    pdf.cell(140, 10, "TOTAL", 1, 0, 'R')
    pdf.cell(50, 10, f"{service_data['Valor']:.2f} EUR", 1, 1, 'R')
    pdf.ln(20)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, "Obrigado pela preferencia!", ln=True, align="C")
    return pdf.output(dest='S').encode('latin-1')

def check_safety_rules(text, history_context=""):
    """
    Verificação de Segurança Agressiva.
    Analisa o texto atual + histórico recente para detetar padrões de contacto fragmentados.
    """
    # 1. Combina texto atual com histórico recente
    full_text = history_context + " " + text
    
    # 2. Emails
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', full_text):
        return False, "Proibido partilhar emails."
    
    # 3. Detetor de Números (MODO AGRESSIVO)
    # Remove TUDO o que não é dígito (espaços, pontos, letras, emojis)
    # Ex: "9 . 1 . 2" vira "912"
    digits_only = re.sub(r'\D', '', full_text)
    
    # Se no total acumulado existirem 9 ou mais dígitos, e começar por 9, 2 ou 3 (indicativos PT), bloqueia.
    # Isto apanha alguém que escreva um número dígito a dígito ao longo de 9 mensagens.
    if len(digits_only) >= 9:
        # Verifica se parece um número de telefone PT (Começa por 9 ou 2)
        # Se tivermos 9 digitos acumulados e o primeiro for 9 ou 2, é quase certo que é telefone.
        if digits_only[0] in ['9', '2', '3']:
             return False, "Proibido partilhar contactos telefónicos (detetado padrão numérico)."
    
    # 4. Números por extenso (Lógica de Texto)
    normalized = re.sub(r'[^\w\s]', '', full_text.lower())
    numeros_extenso = ["zero", "um", "dois", "tres", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
    
    words = normalized.split()
    count_seq = 0
    for w in words:
        if w in numeros_extenso:
            count_seq += 1
        elif len(w) > 2: 
             count_seq = 0 # Reset apenas se for palavra relevante não numérica
        
        # Se detetar 3 números por extenso seguidos ("nove um dois"), bloqueia
        if count_seq >= 3: 
            return False, "Proibido partilhar sequências numéricas por extenso."
            
    return True, ""

# ==============================================================================
# 3. DADOS E STATE
# ==============================================================================
USERS_DB = {
    "cliente@email.com": {"pass": "123", "role": "Cliente", "nome": "Família Rodrigues"},
    "baba@email.com":    {"pass": "123", "role": "Babysitter", "nome": "Maria Oliveira"},
    "admin@email.com":   {"pass": "admin", "role": "Admin", "nome": "Administrador"}
}

keys_defaults = [
    ('logged_in', False), ('user_role', None), ('user_name', None), ('user_email', None), 
    ('current_page', "Dashboard"), ('booking_step', 1), ('temp_booking_data', {}),
    ('active_chat_user', None), ('checkout_data', None), 
    ('cal_year', datetime.now().year), ('cal_month', datetime.now().month),
    ('selected_history_service', None)
]
for k, v in keys_defaults:
    if k not in st.session_state: st.session_state[k] = v

if 'initialized' not in st.session_state:
    st.session_state['babysitters'] = pd.DataFrame({
        'Nome': ['Ana Silva', 'Maria Oliveira', 'Joana Santos', 'Beatriz Costa'],
        'Avaliação': [4.8, 4.9, 4.5, 5.0],
        'Preço/Hora': [35.0, 45.0, 30.0, 50.0],
        'Localização': ['Lisboa', 'Porto', 'Lisboa', 'Coimbra'],
        'Bio': [
            "Educadora de infância com 5 anos de experiência.",
            "Enfermeira pediátrica com curso de primeiros socorros.",
            "Estudante de psicologia, muito paciente.",
            "Mãe experiente em recém-nascidos."
        ],
        'Foto': ['https://api.dicebear.com/7.x/avataaars/svg?seed=Ana', 
                 'https://api.dicebear.com/7.x/avataaars/svg?seed=Maria',
                 'https://api.dicebear.com/7.x/avataaars/svg?seed=Joana',
                 'https://api.dicebear.com/7.x/avataaars/svg?seed=Beatriz']
    })
    
    hoje = datetime.now().date()
    st.session_state['agendamentos'] = pd.DataFrame({
        'Data': [hoje, hoje + timedelta(days=2), hoje - timedelta(days=5)],
        'Hora': [dt_time(14, 0), dt_time(18, 30), dt_time(9, 0)],
        'Local': ['Av. da Liberdade, Lisboa', 'Rua do Ouro, Porto', 'Parque das Nações, Lisboa'],
        'Babysitter': ['Maria Oliveira', 'Ana Silva', 'Joana Santos'],
        'Cliente': ['Família Rodrigues', 'Família Costa', 'Família Rodrigues'],
        'Status': ['Confirmado', 'Pendente', 'Concluído'],
        'Valor': [135.00, 70.00, 90.00]
    })
    
    st.session_state['mensagens'] = [
        {"from": "cliente@email.com", "to": "baba@email.com", "content": "Olá! Disponível sexta?"},
        {"from": "baba@email.com", "to": "cliente@email.com", "content": "Sim, a partir das 18h."}
    ]
    
    st.session_state['notifications'] = [
        {"msg": "Maria Oliveira aceitou o seu pedido.", "time": "10 min atrás"}
    ]
    st.session_state['initialized'] = True

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
            if email in USERS_DB and USERS_DB[email]["pass"] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_email'] = email
                st.session_state['user_role'] = USERS_DB[email]["role"]
                st.session_state['user_name'] = USERS_DB[email]["nome"]
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
            notifs = st.session_state.get('notifications', [])
            has_new = len(notifs) > 0
            icon_label = "🔔 🧷" if has_new else "🔔"
            with c_notif:
                with st.popover(icon_label, use_container_width=True):
                    st.markdown("#### Notificações")
                    if not notifs: st.info("Tudo limpo!")
                    else:
                        for n in notifs: st.info(f"**{n['msg']}**\n\n*{n['time']}*")
                        if st.button("Limpar Tudo"): st.session_state['notifications'] = []; st.rerun()
            if c_logout.button("Sair"): st.session_state['logged_in'] = False; st.rerun()
        st.divider()
    if st.session_state['current_page'] != "Dashboard" and st.session_state['current_page'] not in menu_options:
        if st.button("⬅ Voltar ao Dashboard"): go_to_page("Dashboard", reset_step=True)

# ==============================================================================
# 5. DASHBOARD CLIENTE
# ==============================================================================
def page_dashboard_cliente():
    st.header(f"Olá, {st.session_state['user_name']}")
    df = st.session_state['agendamentos']
    meus_pedidos = df[df['Cliente'] == st.session_state['user_name']]
    hoje = datetime.now().date()
    pedidos_futuros = meus_pedidos[meus_pedidos['Data'] >= hoje]
    pedidos_passados = meus_pedidos[meus_pedidos['Data'] < hoje].sort_values(by='Data', ascending=False)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Serviços Realizados", len(pedidos_passados))
    c2.metric("Pedidos Futuros", len(pedidos_futuros))
    c3.metric("Mensagens Novas", 2) 
    st.markdown("---")

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
                                st.session_state['selected_history_service'] = row
                                go_to_page("Detalhes Serviço")
                if len(pedidos_passados) > 3: st.caption("Mostrando os 3 mais recentes.")
    
    st.markdown("---")
    st.subheader("📅 Próximos Pedidos")
    if pedidos_futuros.empty: st.info("Não tem pedidos agendados.")
    else: st.dataframe(pedidos_futuros[['Data', 'Hora', 'Babysitter', 'Status', 'Valor']], use_container_width=True, hide_index=True)

# ==============================================================================
# 5.1. DETALHES DO SERVIÇO (COM PDF)
# ==============================================================================
def page_detalhes_servico():
    st.title("Detalhes do Serviço")
    servico = st.session_state.get('selected_history_service')
    if servico is None: st.error("Nenhum serviço selecionado."); return

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Informação do Profissional")
            st.write(f"**Babysitter:** {servico['Babysitter']}")
            st.write(f"**Status:** {servico['Status']}")
        with c2:
            st.subheader("Detalhes do Agendamento")
            st.write(f"**Data:** {servico['Data'].strftime('%d/%m/%Y')}")
            hora_str = servico['Hora'].strftime('%H:%M') if isinstance(servico.get('Hora'), dt_time) else "N/A"
            st.write(f"**Hora:** {hora_str}")
            st.write(f"**Local:** {servico.get('Local', 'N/A')}")
        st.divider()
        st.markdown(f"### Valor Total: € {servico['Valor']:.2f}")
        st.write("")
        
        if st.button("📄 Gerar Fatura (PDF)", type="primary"):
            pdf_bytes = create_pdf_invoice(servico)
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="Fatura.pdf">Clique aqui para descarregar o PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

# ==============================================================================
# 6. WIZARD DE PEDIDOS
# ==============================================================================
def page_novo_servico():
    step = st.session_state['booking_step']
    
    if step == 1:
        st.header(" Passo 1 de 3: Detalhes do Serviço")
        st.progress(33)
        with st.form("form_step1"):
            st.subheader("Quando e Quanto Tempo?")
            c1, c2 = st.columns(2)
            with c1: dt = st.date_input("Data de Início", min_value=datetime.now().date()); hr = st.time_input("Hora de Início")
            with c2: dur = st.number_input("Duração Estimada (horas)", min_value=1, value=3, step=1)
            st.subheader("Quem vamos cuidar?")
            c3, c4 = st.columns(2)
            with c3: kids = st.number_input("Número de Crianças", min_value=1, value=1)
            with c4: idades = st.text_input("Idades das Crianças", placeholder="Ex: 3 anos, 5 anos")
            st.subheader("Onde?")
            st.info("⚠️ A morada deve ser válida para calcular a taxa de deslocação.")
            morada_rua = st.text_input("Local do Serviço (Rua e Número)")
            morada_cidade = st.text_input("Cidade / Localidade", value="Lisboa")
            obs = st.text_area("Observações Adicionais", placeholder="Rotinas, alergias, etc.")
            submit_step1 = st.form_submit_button("Validar e Procurar Babysitters ➡", type="primary", use_container_width=True)
            if submit_step1:
                if not morada_rua or not morada_cidade: st.error("Preencha a morada completa.")
                else:
                    full_address = f"{morada_rua}, {morada_cidade}"
                    with st.spinner("A validar morada..."):
                        loc_obj = validate_address(full_address)
                    if loc_obj is None: st.error("❌ Morada não encontrada ou inválida.")
                    else:
                        st.success("✅ Morada validada com sucesso!")
                        time.sleep(0.5)
                        st.session_state['temp_booking_data'] = {'data': dt, 'hora': hr, 'duracao': dur, 'criancas': kids, 'idades': idades, 'morada': full_address, 'obs': obs, 'location_obj': loc_obj}
                        st.session_state['booking_step'] = 2
                        st.rerun()

    elif step == 2:
        data_pedido = st.session_state['temp_booking_data']
        st.header("Passo 2 de 3: Escolher Babysitter")
        st.progress(66)
        if st.button("⬅ Voltar"): st.session_state['booking_step'] = 1; st.rerun()
        st.divider()
        disponiveis = get_available_babysitters(data_pedido['data'])
        if disponiveis.empty: st.warning("Não existem babysitters disponíveis para esta data.")
        else:
            for idx, row in disponiveis.iterrows():
                with st.container(border=True):
                    c_img, c_info, c_btn = st.columns([1, 4, 1.5])
                    with c_img: st.image(row['Foto'], width=100)
                    with c_info: 
                        primeiro_nome = row['Nome'].split()[0]
                        st.subheader(primeiro_nome)
                        st.write(f"📝 *{row['Bio']}*")
                        st.caption(f"📍 {row['Localização']} | ⭐ {row['Avaliação']}")
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
        if st.button("⬅ Voltar à seleção"): st.session_state['booking_step'] = 2; st.rerun()
        data = st.session_state.get('checkout_data')
        if not data: st.error("Erro de dados."); st.stop()
        calc = data['calculo']
        baba_nome = data['babysitter_primeiro_nome']
        c_resumo, c_pagamento = st.columns([1.5, 2])
        with c_resumo:
            with st.container(border=True):
                st.subheader("Resumo do Serviço")
                st.write(f"**Babysitter:** {baba_nome}")
                st.write(f"**Data:** {data['data'].strftime('%d/%m/%Y')} às {data['hora'].strftime('%H:%M')}")
                st.write(f"**Local:** {data['morada']}")
                st.divider()
                st.write(f"Serviço: € {calc['custo_servico']:.2f}")
                st.write(f"Deslocação: € {calc['custo_deslocacao']:.2f}")
                st.markdown(f"### Total a Pagar: € {calc['total']:.2f}")
        with c_pagamento:
            st.subheader("Escolha o Método")
            metodo = st.radio("Método", ["MBWAY", "Cartão de Crédito", "Revolut"], horizontal=True)
            if metodo == "MBWAY": st.text_input("Nº Telemóvel", placeholder="91xxxxxxx")
            elif metodo == "Cartão de Crédito": st.text_input("Nº Cartão"); st.columns(2)[0].text_input("Validade"); st.columns(2)[1].text_input("CVV")
            elif metodo == "Revolut": st.info("Utilize o Revolut Pay na próxima janela.")
            st.write("")
            if st.button(f"Pagar € {calc['total']:.2f} e Confirmar", type="primary", use_container_width=True):
                with st.spinner("A processar pagamento..."):
                    time.sleep(2) 
                    novo = {'Data': data['data'], 'Hora': data['hora'], 'Local': data['morada'], 'Babysitter': data['babysitter']['Nome'], 'Cliente': st.session_state['user_name'], 'Status': 'Confirmado', 'Valor': calc['total']}
                    st.session_state['agendamentos'] = pd.concat([st.session_state['agendamentos'], pd.DataFrame([novo])], ignore_index=True)
                    st.toast(f"📧 Email de confirmação enviado para {st.session_state['user_email']}")
                    st.balloons(); st.success("Reserva confirmada com sucesso!"); time.sleep(3)
                    go_to_page("Dashboard", reset_step=True)

# ==============================================================================
# 7. CALENDÁRIO
# ==============================================================================
def page_calendario():
    def change_month(amount):
        st.session_state['cal_month'] += amount
        if st.session_state['cal_month'] > 12: st.session_state['cal_month'] = 1; st.session_state['cal_year'] += 1
        elif st.session_state['cal_month'] < 1: st.session_state['cal_month'] = 12; st.session_state['cal_year'] -= 1

    c_head, c_btn = st.columns([3, 1])
    role = st.session_state['user_role']
    if role == 'Cliente':
        c_head.title("Meus Pedidos")
        c_btn.write(""); 
        if c_btn.button("➕ Novo Pedido", type="primary", use_container_width=True): go_to_page("Novo Serviço", reset_step=True)
    else:
        c_head.title("Minha Agenda")
        c_btn.write(""); 
        if c_btn.button("➕ Nova Disponibilidade", type="primary", use_container_width=True): st.toast("Mock")

    with st.container(border=True):
        if role == 'Cliente':
            cl = st.columns([2, 2, 5]); cl[0].markdown("🟦 **Serviço Agendado**"); cl[1].markdown("🟣 **Dia Atual**")
        else:
            cl = st.columns([1, 2, 2, 5]); cl[0].markdown("🟢 **Disponível**"); cl[1].markdown("🟦 **Serviço Agendado**"); cl[2].markdown("🟣 **Dia Atual**")
    st.write("")

    with st.container(border=True):
        cp, cd, cn = st.columns([1, 6, 1])
        if cp.button("← Anterior"): change_month(-1); st.rerun()
        meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        cd.markdown(f"<h3 style='text-align: center; margin: 0;'>{meses[st.session_state['cal_month']]} {st.session_state['cal_year']}</h3>", unsafe_allow_html=True)
        if cn.button("Próximo →"): change_month(1); st.rerun()

    dias_semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
    cols_header = st.columns(7)
    for i, dia in enumerate(dias_semana): cols_header[i].markdown(f"**{dia}**", unsafe_allow_html=True)

    cal = calendar.monthcalendar(st.session_state['cal_year'], st.session_state['cal_month'])
    hoje = datetime.now()
    eh_mes_atual = (hoje.year == st.session_state['cal_year'] and hoje.month == st.session_state['cal_month'])
    
    df = st.session_state['agendamentos']
    if role == 'Cliente': meus_jobs = df[df['Cliente'] == st.session_state['user_name']]
    else: meus_jobs = df[df['Babysitter'].apply(lambda x: st.session_state['user_name'] in x)]

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0: st.markdown("<div style='min-height: 110px;'></div>", unsafe_allow_html=True)
                else:
                    is_today = (eh_mes_atual and day == hoje.day)
                    dia_class = "day-cell current-day" if is_today else "day-cell"
                    data_atual = datetime(st.session_state['cal_year'], st.session_state['cal_month'], day).date()
                    eventos_dia = meus_jobs[meus_jobs['Data'] == data_atual]
                    
                    events_html = ""
                    for _, evt in eventos_dia.iterrows():
                        css_class = "event-card past" if data_atual < hoje.date() else "event-card"
                        hora_str = evt['Hora'].strftime('%H:%M') if isinstance(evt['Hora'], dt_time) else ""
                        nome_display = evt['Babysitter'].split()[0] if role == 'Cliente' else evt['Cliente'].split()[0]
                        events_html += f"<div class='{css_class}'><strong>{hora_str}</strong> {nome_display}<br><span style='font-size:9px; opacity:0.8;'>📍 {str(evt['Local'])[:10]}...</span></div>"
                    st.markdown(f"<div class='{dia_class}'><span class='day-number'>{day}</span>{events_html}</div>", unsafe_allow_html=True)

# ==============================================================================
# 8. PÁGINA: MENSAGENS (COM FILTRO E BLOQUEIO REFORÇADO)
# ==============================================================================
def page_mensagens():
    st.header("Mensagens")
    col_contacts, col_chat = st.columns([1, 2.5])
    user_email = st.session_state['user_email']
    user_name = st.session_state['user_name']
    hoje = datetime.now().date()
    
    contacts_set = set()
    for m in st.session_state['mensagens']:
        if m['from'] == user_email: contacts_set.add(m['to'])
        elif m['to'] == user_email: contacts_set.add(m['from'])
    contact_list = list(contacts_set)

    with col_contacts:
        with st.expander("➕ Nova Conversa", expanded=False):
            df_agendas = st.session_state['agendamentos']
            if st.session_state['user_role'] == 'Cliente':
                futuros = df_agendas[(df_agendas['Cliente'] == user_name) & (df_agendas['Data'] >= hoje) & (df_agendas['Status'] != 'Concluído')]
                opcoes = futuros['Babysitter'].unique()
                mapa_nomes = {v['nome']: k for k, v in USERS_DB.items() if v['role'] == 'Babysitter'}
            else:
                futuros = df_agendas[(df_agendas['Babysitter'].apply(lambda x: user_name in x)) & (df_agendas['Data'] >= hoje)]
                opcoes = futuros['Cliente'].unique()
                mapa_nomes = {v['nome']: k for k, v in USERS_DB.items() if v['role'] == 'Cliente'}

            selected_partner = st.selectbox("Escolha o destinatário:", opcoes, index=None, placeholder="Selecione...")
            
            if selected_partner:
                partner_email = mapa_nomes.get(selected_partner)
                if partner_email and st.button("Iniciar Conversa", type="primary"):
                    st.session_state['active_chat_user'] = partner_email
                    st.rerun()
            elif len(opcoes) == 0:
                st.caption("Não tem serviços futuros agendados.")

        with st.container(border=True):
            st.subheader("💬 Conversas")
            if not contact_list: st.info("Sem histórico.")
            else:
                for contact_email in contact_list:
                    c_name = USERS_DB.get(contact_email, {}).get('nome', contact_email)
                    if st.button(f"👤 {c_name}", key=f"chat_{contact_email}", use_container_width=True):
                        st.session_state['active_chat_user'] = contact_email
                        st.rerun()

    with col_chat:
        active_user = st.session_state['active_chat_user']
        chat_container = st.container(border=True, height=550)
        
        if not active_user:
            with chat_container: st.markdown("<div style='text-align: center; margin-top: 150px; color: #ccc;'><h1>💭</h1><h3>Selecione uma conversa</h3></div>", unsafe_allow_html=True)
        else:
            can_send_message = False
            active_name = USERS_DB.get(active_user, {}).get('nome', active_user)
            df = st.session_state['agendamentos']
            
            if st.session_state['user_role'] == 'Cliente':
                servico_valido = df[
                    (df['Cliente'] == user_name) & 
                    (df['Babysitter'] == active_name) & 
                    (df['Data'] >= hoje) &
                    (df['Status'] != 'Concluído')
                ]
            else:
                servico_valido = df[
                    (df['Babysitter'].apply(lambda x: user_name in x)) & 
                    (df['Cliente'] == active_name) & 
                    (df['Data'] >= hoje) &
                    (df['Status'] != 'Concluído')
                ]
                
            if not servico_valido.empty: can_send_message = True
            
            msgs = [m for m in st.session_state['mensagens'] if (m['from'] == user_email and m['to'] == active_user) or (m['from'] == active_user and m['to'] == user_email)]
            
            with chat_container:
                st.write(f"**A falar com:** {active_name}")
                if not can_send_message: st.warning("🔒 Serviço terminado ou inexistente. Conversa em modo de leitura.")
                st.divider()
                for msg in msgs:
                    with st.chat_message("user" if msg['from'] == user_email else "assistant"): st.write(msg['content'])
            
            if can_send_message:
                if prompt := st.chat_input(f"Escreva para {active_name}..."):
                    my_recent_msgs = [m['content'] for m in st.session_state['mensagens'] 
                                      if m['from'] == user_email and m['to'] == active_user]
                    history_txt = " ".join(my_recent_msgs[-20:]) if my_recent_msgs else "" # CONTEXTO AUMENTADO PARA 20
                    
                    is_safe, error_msg = check_safety_rules(prompt, history_txt)
                    
                    if is_safe:
                        st.session_state['mensagens'].append({"from": user_email, "to": active_user, "content": prompt})
                        st.rerun()
                    else:
                        st.error(f"🚫 Mensagem bloqueada: {error_msg}")

def page_editar_perfil():
    st.header("⚙️ Configurações de Perfil")
    c1, c2 = st.columns(2)
    with c1: st.text_input("Nome", value=st.session_state['user_name']); st.text_input("Email", value=st.session_state['user_email'], disabled=True)
    with c2: st.text_input("Telefone", "+351 ..."); st.button("Guardar Alterações")

def page_dashboard_babysitter():
    st.header(f"🧸 Painel Babysitter: {st.session_state['user_name']}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Próximos Trabalhos", "3"); col2.metric("Ganhos (Mês)", "€ 450,00"); col3.metric("Avaliação Média", "4.9 ⭐")
    st.divider()
    st.subheader("🗓️ Minha Agenda")
    st.dataframe(st.session_state['agendamentos'], use_container_width=True)

def page_admin_dashboard():
    st.header("🔐 Painel Admin Global")
    c1, c2 = st.columns(2); c1.metric("Utilizadores Totais", len(USERS_DB)); c2.metric("Receita Total", "€ 1.250,00")
    st.markdown("---")
    st.subheader("Todas as Transações")
    st.dataframe(st.session_state['agendamentos'], use_container_width=True)

# ==============================================================================
# 9. ROUTER
# ==============================================================================
if not st.session_state['logged_in']:
    login_page()
else:
    role = st.session_state['user_role']
    if role == 'Cliente': menus = ["Dashboard", "Calendário", "Mensagens", "Editar Perfil"]
    elif role == 'Babysitter': menus = ["Dashboard", "Calendário", "Mensagens", "Editar Perfil"]
    else: menus = ["Dashboard", "Admin Global", "Mensagens"]

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
    elif pg == "Admin Global": page_admin_dashboard()