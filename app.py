import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
import calendar 

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
    
    /* Botões */
    div.stButton > button:first-child { font-weight: bold; }
    
    /* Ajuste menu superior */
    div.row-widget.stRadio > div { flex-direction: row; align-items: center; }
    
    /* Calendário */
    .day-card {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        height: 100px;
        border: 1px solid #e0e0e0;
    }
    
    /* Ajuste do Popover de Notificações para parecer integrado */
    button[kind="secondary"] {
        border: none;
        background: transparent;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. DADOS (MOCK DATABASE)
# ==============================================================================
USERS_DB = {
    "cliente@email.com": {"pass": "123", "role": "Cliente", "nome": "Família Rodrigues"},
    "baba@email.com":    {"pass": "123", "role": "Babysitter", "nome": "Maria Oliveira"},
    "admin@email.com":   {"pass": "admin", "role": "Admin", "nome": "Administrador"}
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['user_name'] = None
    st.session_state['user_email'] = None

if 'current_page' not in st.session_state: st.session_state['current_page'] = "Dashboard"
if 'cal_year' not in st.session_state: st.session_state['cal_year'] = datetime.now().year
if 'cal_month' not in st.session_state: st.session_state['cal_month'] = datetime.now().month
if 'active_chat_user' not in st.session_state: st.session_state['active_chat_user'] = None

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
    st.session_state['agendamentos'] = pd.DataFrame({
        'Data': [datetime.now().date(), datetime.now().date() + timedelta(days=2), datetime.now().date() - timedelta(days=5)],
        'Babysitter': ['Maria Oliveira', 'Ana Silva', 'Joana Santos'],
        'Cliente': ['Família Rodrigues', 'Família Costa', 'Família Rodrigues'],
        'Status': ['Confirmado', 'Pendente', 'Concluído'],
        'Valor': [135.00, 70.00, 90.00]
    })
    st.session_state['mensagens'] = [
        {"from": "cliente@email.com", "to": "baba@email.com", "content": "Olá! Disponível sexta?"},
        {"from": "baba@email.com", "to": "cliente@email.com", "content": "Sim, a partir das 18h."},
    ]
    
    # --- NOTIFICAÇÕES (MOCK) ---
    # Vamos simular que há 2 interações novas ao iniciar
    st.session_state['notifications'] = [
        {"msg": "Maria Oliveira aceitou o seu pedido.", "time": "10 min atrás"},
        {"msg": "Novo pagamento processado.", "time": "1 hora atrás"}
    ]
    
    st.session_state['initialized'] = True

# ==============================================================================
# 3. NAVEGAÇÃO E LOGIN (COM NOTIFICAÇÕES)
# ==============================================================================

def go_to_page(page_name):
    st.session_state['current_page'] = page_name
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
                st.session_state['current_page'] = "Dashboard"
                st.success("Login efetuado!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Credenciais inválidas.")

def render_navbar(menu_options):
    with st.container():
        # Ajuste de colunas para caber o sino
        col_nav, col_user = st.columns([3, 1.5]) 
        
        with col_nav:
            try: idx = menu_options.index(st.session_state['current_page'])
            except ValueError: idx = 0 
            selected = st.radio("Nav", menu_options, horizontal=True, label_visibility="collapsed", key="nav_radio", index=idx)
        
        with col_user:
            # Dividir área do user: Nome | Sino | Sair
            c_name, c_notif, c_logout = st.columns([2, 1, 1])
            
            # 1. Nome
            c_name.write(f"👤 **{st.session_state['user_name'].split()[0]}**") # Só o primeiro nome para poupar espaço
            
            # 2. Sino de Notificações
            notifs = st.session_state.get('notifications', [])
            has_new = len(notifs) > 0
            
            # Se tiver novidades, usa o Alfinete (Fralda) 🧷, senão usa só o sino
            if has_new:
                icon_label = "🔔 🧷" 
                help_text = "Tem novidades na fralda!"
            else:
                icon_label = "🔔"
                help_text = "Sem notificações"

            with c_notif:
                with st.popover(icon_label, use_container_width=True, help=help_text):
                    st.markdown("#### Notificações")
                    if not notifs:
                        st.info("Tudo limpo! Sem notificações.")
                        st.markdown("<div style='text-align:center; color: #ccc; font-size: 40px;'>🔔</div>", unsafe_allow_html=True)
                    else:
                        for n in notifs:
                            st.info(f"**{n['msg']}**\n\n*{n['time']}*")
                        
                        if st.button("Limpar Tudo", key="clear_notifs"):
                            st.session_state['notifications'] = []
                            st.rerun()

            # 3. Botão Sair
            if c_logout.button("Sair", key="logout_btn"):
                st.session_state['logged_in'] = False
                st.rerun()
        st.divider()
    
    # Botão Voltar
    if st.session_state['current_page'] != "Dashboard" and st.session_state['current_page'] not in menu_options:
        if st.button("⬅ Voltar ao Dashboard"): go_to_page("Dashboard")
    return selected

# ==============================================================================
# 4. PÁGINAS - CLIENTE
# ==============================================================================

def page_dashboard_cliente():
    st.header(f"Olá, {st.session_state['user_name']}")
    df = st.session_state['agendamentos']
    meus_pedidos = df[df['Cliente'] == st.session_state['user_name']]
    hoje = datetime.now().date()
    pedidos_futuros = meus_pedidos[meus_pedidos['Data'] >= hoje]
    
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pedidos Futuros", len(pedidos_futuros))
    c2.metric("Mensagens Novas", 2) 
    c3.metric("Total Gasto", f"€ {meus_pedidos['Valor'].sum():.2f}")
    c4.metric("Serviços Completos", len(meus_pedidos[meus_pedidos['Data'] < hoje]))
    st.markdown("---")

    # Cards Ação
    col_new, col_msg = st.columns(2)
    with col_new:
        with st.container(border=True):
            st.subheader("➕ Novo Pedido")
            st.write("Encontre a babá perfeita.")
            if st.button("Criar Novo Pedido", use_container_width=True): go_to_page("Novo Serviço") 
    with col_msg:
        with st.container(border=True):
            st.subheader("💬 Mensagens")
            st.write("Gerir conversas com babás.")
            if st.button("Ler Mensagens", use_container_width=True): go_to_page("Mensagens")
    
    st.markdown("---")
    st.subheader("📅 Próximos Pedidos")
    if pedidos_futuros.empty: st.info("Não tem pedidos agendados.")
    else: st.dataframe(pedidos_futuros[['Data', 'Babysitter', 'Status', 'Valor']], use_container_width=True, hide_index=True)

def page_novo_servico():
    st.header("➕ Novo Pedido")
    with st.form("form_novo_pedido"):
        c1, c2 = st.columns(2)
        with c1: dt = st.date_input("Data"); hr = st.time_input("Hora")
        with c2: st.number_input("Crianças", 1); dur = st.number_input("Duração (h)", 3)
        st.text_input("Morada")
        if st.form_submit_button("Confirmar Pedido"):
            novo = {'Data': dt, 'Babysitter': 'Pendente', 'Cliente': st.session_state['user_name'], 'Status': 'Pendente', 'Valor': dur * 12.5}
            st.session_state['agendamentos'] = pd.concat([st.session_state['agendamentos'], pd.DataFrame([novo])], ignore_index=True)
            
            # Gera notificação para simular interação
            st.session_state['notifications'].append({"msg": "Pedido criado com sucesso!", "time": "Agora mesmo"})
            
            st.success("Pedido criado!"); time.sleep(1); go_to_page("Dashboard")

def page_historico_avaliacoes():
    st.header("⭐ Histórico e Avaliações")
    df = st.session_state['agendamentos']
    passados = df[(df['Cliente'] == st.session_state['user_name']) & (df['Data'] < datetime.now().date())]
    if passados.empty: st.info("Sem histórico disponível.")
    else:
        st.dataframe(passados, use_container_width=True)
        for idx, row in passados.iterrows():
            with st.expander(f"Avaliar: {row['Data']} - {row['Babysitter']}"):
                st.slider(f"Estrelas", 1, 5, 5, key=f"star_{idx}")
                if st.button("Enviar", key=f"btn_rate_{idx}"):
                    st.session_state['notifications'].append({"msg": f"Avaliação enviada para {row['Babysitter']}", "time": "Agora mesmo"})
                    st.rerun()

# ==============================================================================
# 5. PÁGINAS - MENSAGENS (SPLIT SCREEN)
# ==============================================================================
def page_mensagens():
    st.header("Mensagens")
    st.caption("Converse com clientes e babysitters")

    col_contacts, col_chat = st.columns([1, 2.5])
    user_email = st.session_state['user_email']
    
    # Lógica de Contactos Inteligente
    contacts_set = set()
    for m in st.session_state['mensagens']:
        if m['from'] == user_email: contacts_set.add(m['to'])
        elif m['to'] == user_email: contacts_set.add(m['from'])
    name_to_email = {v['nome']: k for k, v in USERS_DB.items()}
    my_agendas = st.session_state['agendamentos']
    target_col = 'Babysitter' if st.session_state['user_role'] == 'Cliente' else 'Cliente'
    if st.session_state['user_role'] in ['Cliente', 'Babysitter']:
        relevant = my_agendas[my_agendas[st.session_state['user_role']] == st.session_state['user_name']]
        for name in relevant[target_col].unique():
            if name in name_to_email: contacts_set.add(name_to_email[name])
    contact_list = list(contacts_set)

    with col_contacts:
        with st.container(border=True):
            st.subheader("💬 Conversas")
            if not contact_list: st.info("Sem conversas.")
            else:
                for contact_email in contact_list:
                    c_name = USERS_DB.get(contact_email, {}).get('nome', contact_email)
                    is_active = (st.session_state['active_chat_user'] == contact_email)
                    if st.button(f"👤 {c_name}", key=f"chat_{contact_email}", use_container_width=True, type="primary" if is_active else "secondary"):
                        st.session_state['active_chat_user'] = contact_email
                        st.rerun()

    with col_chat:
        active_user = st.session_state['active_chat_user']
        chat_container = st.container(border=True, height=550)
        if not active_user:
            with chat_container:
                st.markdown("<div style='text-align: center; margin-top: 150px; color: #ccc;'><h1>💭</h1><h3>Selecione uma conversa</h3></div>", unsafe_allow_html=True)
        else:
            active_name = USERS_DB.get(active_user, {}).get('nome', active_user)
            msgs = [m for m in st.session_state['mensagens'] if (m['from'] == user_email and m['to'] == active_user) or (m['from'] == active_user and m['to'] == user_email)]
            with chat_container:
                st.write(f"**A falar com:** {active_name}")
                st.divider()
                for msg in msgs:
                    with st.chat_message("user" if msg['from'] == user_email else "assistant"):
                        st.write(msg['content'])
            if prompt := st.chat_input(f"Escreva para {active_name}..."):
                st.session_state['mensagens'].append({"from": user_email, "to": active_user, "content": prompt})
                # Notificação automática
                st.session_state['notifications'].append({"msg": f"Mensagem enviada para {active_name}", "time": "Agora mesmo"})
                st.rerun()

# ==============================================================================
# 6. PÁGINAS - CALENDÁRIO (COM VISUAL RESTAURADO)
# ==============================================================================
def page_calendario():
    def change_month(amount):
        st.session_state['cal_month'] += amount
        if st.session_state['cal_month'] > 12: st.session_state['cal_month'] = 1; st.session_state['cal_year'] += 1
        elif st.session_state['cal_month'] < 1: st.session_state['cal_month'] = 12; st.session_state['cal_year'] -= 1

    c_head, c_btn = st.columns([3, 1])
    c_head.title("Calendário"); c_btn.write(""); c_btn.button("➕ Nova Disponibilidade", type="primary", use_container_width=True)
    
    with st.container(border=True):
        cl = st.columns([1, 2, 2, 5])
        cl[1].markdown("🟢 **Disponível**"); cl[2].markdown("🔵 **Serviço**"); cl[3].markdown("🟣 **Dia Atual**")
    st.write("")

    with st.container(border=True):
        cp, cd, cn = st.columns([1, 6, 1])
        if cp.button("← Anterior"): change_month(-1); st.rerun()
        meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        cd.markdown(f"<h3 style='text-align: center; margin: 0;'>{meses[st.session_state['cal_month']]} {st.session_state['cal_year']}</h3>", unsafe_allow_html=True)
        if cn.button("Próximo →"): change_month(1); st.rerun()

    dias = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
    ch = st.columns(7)
    for i, d in enumerate(dias): ch[i].markdown(f"**{d}**", unsafe_allow_html=True)

    cal = calendar.monthcalendar(st.session_state['cal_year'], st.session_state['cal_month'])
    hoje = datetime.now()
    eh_mes_atual = (hoje.year == st.session_state['cal_year'] and hoje.month == st.session_state['cal_month'])

    for week in cal:
        cw = st.columns(7)
        for i, day in enumerate(week):
            with cw[i]:
                if day != 0:
                    border = "2px solid #9b59b6" if (eh_mes_atual and day == hoje.day) else "1px solid #e0e0e0"
                    st.markdown(f"""
                    <div style="border: {border}; border-radius: 8px; height: 100px; background-color: white; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                        <span style="font-size: 18px; font-weight: bold;">{day}</span>
                    </div>
                    """, unsafe_allow_html=True)

# ==============================================================================
# 7. OUTRAS PÁGINAS E ROUTER
# ==============================================================================

def page_dashboard_babysitter():
    st.header(f"🧸 Painel Babysitter"); c1,c2 = st.columns(2); c1.metric("Ganhos", "€ 450"); c2.metric("Jobs", "3")
    st.dataframe(st.session_state['agendamentos'])

def page_admin_dashboard():
    st.header("🔐 Admin"); st.dataframe(st.session_state['agendamentos'])

def page_editar_perfil():
    st.header("⚙️ Perfil"); c1,c2=st.columns(2); c1.text_input("Nome", st.session_state['user_name']); c2.button("Salvar")

# ROUTER PRINCIPAL
if not st.session_state['logged_in']:
    login_page()
else:
    role = st.session_state['user_role']
    if role == 'Cliente': menus = ["Dashboard", "Calendário", "Mensagens", "Avaliações e Histórico", "Editar Perfil"]
    elif role == 'Babysitter': menus = ["Dashboard", "Calendário", "Mensagens", "Editar Perfil"]
    else: menus = ["Dashboard", "Admin Global", "Mensagens"]

    sel = render_navbar(menus)
    if sel != st.session_state['current_page'] and sel in menus: st.session_state['current_page'] = sel; st.rerun()

    pg = st.session_state['current_page']
    if pg == "Dashboard":
        if role == 'Cliente': page_dashboard_cliente()
        elif role == 'Babysitter': page_dashboard_babysitter()
        else: page_admin_dashboard()
    elif pg == "Novo Serviço": page_novo_servico()
    elif pg == "Calendário": page_calendario()
    elif pg == "Mensagens": page_mensagens()