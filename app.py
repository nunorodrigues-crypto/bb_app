import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
import calendar
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

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
    .day-card {
        background-color: #ffffff; padding: 10px; border-radius: 5px;
        text-align: center; height: 100px; border: 1px solid #e0e0e0;
    }
    button[kind="secondary"] { border: none; background: transparent; }
    
    .payment-option {
        border: 2px solid #e0e0e0; border-radius: 10px; padding: 15px;
        text-align: center; cursor: pointer; transition: all 0.3s;
    }
    .payment-option:hover { border-color: #FF4B4B; background-color: #f0f2f6; }
    
    /* Card de Babysitter na Seleção */
    .baba-card-select {
        border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LÓGICA DE CÁLCULO E GEOCODING
# ==============================================================================
def get_distance_km(address_destination):
    geolocator = Nominatim(user_agent="babyconnect_app")
    try:
        loures_coords = (38.8315, -9.1746)
        location = geolocator.geocode(f"{address_destination}, Portugal", timeout=10)
        if location:
            dest_coords = (location.latitude, location.longitude)
            return geodesic(loures_coords, dest_coords).km
        else: return None 
    except Exception as e: return None 

def calcular_preco_total(babysitter_data, duracao_horas, morada_cliente):
    preco_hora = babysitter_data['Preço/Hora']
    custo_servico = preco_hora * duracao_horas
    distancia_ida = get_distance_km(morada_cliente)
    
    if distancia_ida is None:
        distancia_ida = 15.0 
        st.warning("Distância estimada (morada não exata).")
    
    custo_deslocacao = (distancia_ida * 2) * 0.45
    total = custo_servico + custo_deslocacao
    
    return {
        "custo_servico": custo_servico,
        "distancia_ida": distancia_ida,
        "custo_deslocacao": custo_deslocacao,
        "total": total
    }

def get_available_babysitters(date_selected, start_time, duration):
    """Filtra babysitters que NÃO têm agendamento no dia selecionado"""
    df_agendas = st.session_state['agendamentos']
    df_babas = st.session_state['babysitters']
    
    # 1. Encontrar quem está ocupado nesse dia (Simplificação: se tem job no dia, está ocupado)
    ocupadas_no_dia = df_agendas[df_agendas['Data'] == date_selected]['Babysitter'].unique()
    
    # 2. Filtrar DataFrame de Babysitters
    disponiveis = df_babas[~df_babas['Nome'].isin(ocupadas_no_dia)]
    
    return disponiveis

# ==============================================================================
# 3. DADOS E STATE
# ==============================================================================
USERS_DB = {
    "cliente@email.com": {"pass": "123", "role": "Cliente", "nome": "Família Rodrigues"},
    "baba@email.com":    {"pass": "123", "role": "Babysitter", "nome": "Maria Oliveira"},
    "admin@email.com":   {"pass": "admin", "role": "Admin", "nome": "Administrador"}
}

keys = [('logged_in', False), ('user_role', None), ('user_name', None), ('user_email', None), 
        ('current_page', "Dashboard"), ('booking_step', 1), ('temp_booking_data', {}),
        ('active_chat_user', None), ('checkout_data', None), 
        ('cal_year', datetime.now().year), ('cal_month', datetime.now().month)]

for k, v in keys:
    if k not in st.session_state: st.session_state[k] = v

if 'initialized' not in st.session_state:
    st.session_state['babysitters'] = pd.DataFrame({
        'Nome': ['Ana Silva', 'Maria Oliveira', 'Joana Santos', 'Beatriz Costa'],
        'Avaliação': [4.8, 4.9, 4.5, 5.0],
        'Preço/Hora': [35.0, 45.0, 30.0, 50.0],
        'Localização': ['Lisboa', 'Porto', 'Lisboa', 'Coimbra'],
        'Foto': ['https://api.dicebear.com/7.x/avataaars/svg?seed=Ana', 
                 'https://api.dicebear.com/7.x/avataaars/svg?seed=Maria',
                 'https://api.dicebear.com/7.x/avataaars/svg?seed=Joana',
                 'https://api.dicebear.com/7.x/avataaars/svg?seed=Beatriz']
    })
    hoje = datetime.now().date()
    st.session_state['agendamentos'] = pd.DataFrame({
        'Data': [hoje, hoje + timedelta(days=2), hoje - timedelta(days=5)],
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
        {"msg": "Maria Oliveira aceitou o seu pedido.", "time": "10 min atrás"},
        {"msg": "Novo pagamento processado.", "time": "1 hora atrás"}
    ]
    st.session_state['initialized'] = True

# ==============================================================================
# 4. NAVEGAÇÃO
# ==============================================================================
def go_to_page(page_name, reset_step=False):
    st.session_state['current_page'] = page_name
    if reset_step:
        st.session_state['booking_step'] = 1
        st.session_state['temp_booking_data'] = {}
    st.rerun()

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

# --- FUNÇÃO DE CALLBACK PARA O MENU ---
def nav_callback():
    """Chamada quando o utilizador clica no menu"""
    new_page = st.session_state['nav_radio']
    st.session_state['current_page'] = new_page
    # Reset steps se voltar ao dashboard
    if new_page == "Dashboard":
        st.session_state['booking_step'] = 1
        st.session_state['temp_booking_data'] = {}

def render_navbar(menu_options):
    with st.container():
        col_nav, col_user = st.columns([3, 1.5]) 
        with col_nav:
            # Determina o índice do menu baseado na página atual
            try: idx = menu_options.index(st.session_state['current_page'])
            except ValueError: idx = 0 # Se for página oculta (ex: Novo Serviço), seleciona o 1º (Dashboard)
            
            st.radio(
                "Nav", 
                menu_options, 
                horizontal=True, 
                label_visibility="collapsed", 
                key="nav_radio", 
                index=idx,
                on_change=nav_callback # USA CALLBACK PARA MUDAR PÁGINA
            )
            
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
    
    # Botão Voltar Inteligente
    if st.session_state['current_page'] != "Dashboard" and st.session_state['current_page'] not in menu_options:
        if st.button("⬅ Voltar ao Dashboard"): go_to_page("Dashboard", reset_step=True)

# ==============================================================================
# 5. PÁGINAS - CLIENTE (DASHBOARD)
# ==============================================================================
def page_dashboard_cliente():
    st.header(f"Olá, {st.session_state['user_name']}")
    df = st.session_state['agendamentos']
    meus_pedidos = df[df['Cliente'] == st.session_state['user_name']]
    hoje = datetime.now().date()
    pedidos_futuros = meus_pedidos[meus_pedidos['Data'] >= hoje]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pedidos Futuros", len(pedidos_futuros))
    c2.metric("Mensagens Novas", 2) 
    c3.metric("Total Gasto", f"€ {meus_pedidos['Valor'].sum():.2f}")
    c4.metric("Serviços Completos", len(meus_pedidos[meus_pedidos['Data'] < hoje]))
    st.markdown("---")

    col_new, col_search = st.columns(2)
    with col_new:
        with st.container(border=True):
            st.subheader("➕ Novo Pedido Rápido")
            st.write("Definir data e encontrar babysitter.")
            # O BOTÃO CHAMA A FUNÇÃO GO_TO_PAGE QUE ALTERA O STATE
            if st.button("Criar Novo Pedido", use_container_width=True, type="primary"): 
                go_to_page("Novo Serviço", reset_step=True) 
    with col_search:
        with st.container(border=True):
            st.subheader("🔍 Pesquisa Livre")
            st.write("Ver todas as babysitters.")
            if st.button("Pesquisar", use_container_width=True): go_to_page("Pesquisar Babás")
    
    st.markdown("---")
    st.subheader("📅 Próximos Pedidos")
    if pedidos_futuros.empty: st.info("Não tem pedidos agendados.")
    else: st.dataframe(pedidos_futuros[['Data', 'Babysitter', 'Status', 'Valor']], use_container_width=True, hide_index=True)

# ==============================================================================
# 6. WIZARD DE PEDIDOS (FORMULÁRIO)
# ==============================================================================
def page_novo_servico():
    step = st.session_state['booking_step']
    
    # --- PASSO 1: FORMULÁRIO DE DETALHES ---
    if step == 1:
        st.header(" Passo 1 de 2: Detalhes do Serviço")
        st.progress(50)
        
        with st.form("form_step1"):
            st.subheader("Quando e Quanto Tempo?")
            c1, c2 = st.columns(2)
            with c1: 
                dt = st.date_input("Data de Início", min_value=datetime.now().date())
                hr = st.time_input("Hora de Início")
            with c2: 
                dur = st.number_input("Duração Estimada (horas)", min_value=1, value=3, step=1)
                # Mock hora fim apenas visual
                # st.text_input("Hora de Fim", value=..., disabled=True)
            
            st.subheader("Quem vamos cuidar?")
            c3, c4 = st.columns(2)
            with c3:
                kids = st.number_input("Número de Crianças", min_value=1, value=1)
            with c4:
                idades = st.text_input("Idades das Crianças", placeholder="Ex: 3 anos, 5 anos")

            st.subheader("Onde?")
            morada_rua = st.text_input("Local do Serviço (Rua e Número)")
            morada_cidade = st.text_input("Cidade / Localidade", value="Lisboa")
            
            st.subheader("Outros Detalhes")
            obs = st.text_area("Observações Adicionais", placeholder="Informações importantes sobre as crianças, rotinas, alergias, etc.")
            
            submit_step1 = st.form_submit_button("Ver Profissionais Disponíveis ➡", type="primary", use_container_width=True)
            
            if submit_step1:
                if not morada_rua or not morada_cidade:
                    st.error("Preencha a morada completa.")
                else:
                    st.session_state['temp_booking_data'] = {
                        'data': dt, 'hora': hr, 'duracao': dur, 'criancas': kids, 'idades': idades,
                        'morada': f"{morada_rua}, {morada_cidade}", 'obs': obs
                    }
                    st.session_state['booking_step'] = 2
                    st.rerun()

    # --- PASSO 2: ESCOLHER BABYSITTER (Disponibilidade Filtrada) ---
    elif step == 2:
        data_pedido = st.session_state['temp_booking_data']
        st.header("Passo 2 de 2: Escolher Babysitter")
        st.caption(f"Mostrando profissionais disponíveis para **{data_pedido['data'].strftime('%d/%m/%Y')}** às **{data_pedido['hora'].strftime('%H:%M')}**")
        st.progress(100)
        
        if st.button("⬅ Voltar e Editar Dados"):
            st.session_state['booking_step'] = 1
            st.rerun()
        
        st.divider()
        
        # Buscar babysitters disponíveis
        disponiveis = get_available_babysitters(data_pedido['data'], data_pedido['hora'], data_pedido['duracao'])
        
        if disponiveis.empty:
            st.warning("Não existem babysitters disponíveis para esta data exata. Tente outro dia.")
        else:
            for idx, row in disponiveis.iterrows():
                with st.container(border=True):
                    c_img, c_info, c_price, c_btn = st.columns([1, 3, 1.5, 1.5])
                    with c_img: st.image(row['Foto'], width=80)
                    with c_info: 
                        st.subheader(row['Nome'])
                        st.write(f"⭐ {row['Avaliação']} | {row['Localização']}")
                    with c_price:
                        st.write("")
                        st.write(f"**€ {row['Preço/Hora']:.2f} / hora**")
                    with c_btn:
                        st.write("")
                        if st.button("Selecionar ✅", key=f"select_{idx}", type="primary", use_container_width=True):
                            with st.spinner("A calcular orçamento final..."):
                                calculo = calcular_preco_total(row.to_dict(), data_pedido['duracao'], data_pedido['morada'])
                                
                                if calculo['distancia_ida'] is None:
                                    st.error("Erro na morada. Volte ao passo 1.")
                                else:
                                    st.session_state['checkout_data'] = {
                                        'babysitter': row.to_dict(),
                                        **data_pedido, 
                                        'calculo': calculo
                                    }
                                    go_to_page("Checkout")

def page_checkout():
    st.header("💳 Checkout e Pagamento")
    data = st.session_state.get('checkout_data')
    if not data:
        st.error("Sessão expirada.")
        if st.button("Reiniciar"): go_to_page("Dashboard", reset_step=True)
        return

    calc = data['calculo']
    baba = data['babysitter']

    c_resumo, c_pagamento = st.columns([1.5, 2])
    with c_resumo:
        with st.container(border=True):
            st.subheader("Resumo do Pedido")
            st.write(f"**Profissional:** {baba['Nome']}")
            st.write(f"**Data:** {data['data'].strftime('%d/%m/%Y')} às {data['hora'].strftime('%H:%M')}")
            st.write(f"**Local:** {data['morada']}")
            st.write(f"**Crianças:** {data['criancas']} ({data.get('idades', 'N/A')})")
            st.divider()
            st.write(f"Serviço: € {calc['custo_servico']:.2f}")
            st.write(f"Deslocação: € {calc['custo_deslocacao']:.2f}")
            st.markdown(f"### Total: € {calc['total']:.2f}")

    with c_pagamento:
        st.subheader("Pagamento")
        st.radio("Método", ["Cartão", "MBWay", "Revolut"], horizontal=True)
        st.text_input("Dados de Pagamento (Mock)")
        
        st.divider()
        if st.button(f"Pagar € {calc['total']:.2f}", type="primary", use_container_width=True):
            time.sleep(1.5)
            novo = {'Data': data['data'], 'Babysitter': baba['Nome'], 'Cliente': st.session_state['user_name'], 'Status': 'Confirmado', 'Valor': calc['total']}
            st.session_state['agendamentos'] = pd.concat([st.session_state['agendamentos'], pd.DataFrame([novo])], ignore_index=True)
            st.session_state['notifications'].append({"msg": f"Serviço confirmado com {baba['Nome']}", "time": "Agora"})
            st.balloons()
            st.success("Sucesso!")
            time.sleep(2)
            go_to_page("Dashboard", reset_step=True)

# ==============================================================================
# 7. OUTRAS PÁGINAS E ROUTER
# ==============================================================================
def page_pesquisar_babas():
    st.header("🔍 Todas as Babysitters")
    st.write("Lista completa sem filtro de data.")
    df = st.session_state['babysitters']
    for idx, row in df.iterrows():
        with st.container(border=True):
            c1,c2 = st.columns([1,5])
            with c1: st.image(row['Foto'], width=80)
            with c2: st.write(f"**{row['Nome']}** | {row['Localização']} | €{row['Preço/Hora']}/h")

def page_mensagens():
    st.header("Mensagens"); st.info("Chat disponível em breve.")
def page_calendario():
    st.header("Calendário"); st.info("Calendário em breve.")
def page_editar_perfil():
    st.header("Perfil"); st.info("Editar perfil em breve.")
def page_dashboard_babysitter():
    st.header("Área Babysitter"); st.dataframe(st.session_state['agendamentos'])
def page_admin_dashboard():
    st.header("Admin"); st.dataframe(st.session_state['agendamentos'])

# ROUTER
if not st.session_state['logged_in']:
    login_page()
else:
    role = st.session_state['user_role']
    if role == 'Cliente': menus = ["Dashboard", "Pesquisar Babás", "Calendário", "Mensagens", "Editar Perfil"]
    elif role == 'Babysitter': menus = ["Dashboard", "Calendário", "Mensagens", "Editar Perfil"]
    else: menus = ["Dashboard", "Admin Global", "Mensagens"]

    # RENDERIZA O MENU (NAVBAR)
    render_navbar(menus)

    # ROTEADOR DE PÁGINAS
    pg = st.session_state['current_page']
    if pg == "Dashboard":
        if role == 'Cliente': page_dashboard_cliente()
        elif role == 'Babysitter': page_dashboard_babysitter()
        else: page_admin_dashboard()
    elif pg == "Novo Serviço": page_novo_servico()
    elif pg == "Checkout": page_checkout()
    elif pg == "Pesquisar Babás": page_pesquisar_babas()
    elif pg == "Calendário": page_calendario()
    elif pg == "Mensagens": page_mensagens()
    elif pg == "Editar Perfil": page_editar_perfil()
    elif pg == "Admin Global": page_admin_dashboard()