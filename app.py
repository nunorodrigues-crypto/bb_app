import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="BabyConnect",
    page_icon="👶",
    layout="wide"
)

# --- ESTILOS CSS PERSONALIZADOS (Simples) ---
st.markdown("""
<style>
    .main > div {padding-top: 2rem;}
    .stMetric {background-color: #f0f2f6; padding: 10px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO ESTADO (SIMULAÇÃO DE BANCO DE DADOS) ---
# Isso garante que os dados persistam enquanto o app está aberto
if 'initialized' not in st.session_state:
    # Dados fictícios de Babysitters
    st.session_state['babysitters'] = pd.DataFrame({
        'Nome': ['Ana Silva', 'Maria Oliveira', 'Joana Santos', 'Beatriz Costa'],
        'Avaliação': [4.8, 4.9, 4.5, 5.0],
        'Preço/Hora': [35.0, 45.0, 30.0, 50.0],
        'Localização': ['Lisboa', 'Porto', 'Lisboa', 'Coimbra'],
        'Experiência': ['3 anos', '5 anos', '1 ano', '10 anos'],
        'Foto': ['https://api.dicebear.com/7.x/avataaars/svg?seed=Ana', 
                 'https://api.dicebear.com/7.x/avataaars/svg?seed=Maria',
                 'https://api.dicebear.com/7.x/avataaars/svg?seed=Joana',
                 'https://api.dicebear.com/7.x/avataaars/svg?seed=Beatriz']
    })

    # Dados fictícios de Agendamentos
    st.session_state['agendamentos'] = pd.DataFrame({
        'Data': [datetime.now().date(), datetime.now().date() + timedelta(days=2)],
        'Babysitter': ['Maria Oliveira', 'Ana Silva'],
        'Cliente': ['Família Rodrigues', 'Família Costa'],
        'Status': ['Confirmado', 'Pendente'],
        'Valor': [135.00, 70.00]
    })

    # Dados fictícios de Mensagens
    st.session_state['mensagens'] = [
        {"role": "user", "content": "Olá! Você está disponível para sexta-feira?"},
        {"role": "assistant", "content": "Olá! Sim, estou disponível a partir das 18h."},
    ]
    
    # Dados de Pagamentos
    st.session_state['pagamentos'] = pd.DataFrame({
        'ID': ['#001', '#002', '#003'],
        'Data': ['2023-10-01', '2023-10-05', '2023-10-10'],
        'Valor': [100.0, 50.0, 120.0],
        'Status': ['Pago', 'Pago', 'Pendente']
    })

    st.session_state['initialized'] = True

# --- MENU LATERAL (SIDEBAR) ---
st.sidebar.title("👶 BabyConnect")
st.sidebar.write("Conectando famílias e babás.")

menu_options = [
    "Dashboard_Cliente",
    "Dashboard_Babysitter",
    "NovoServico",
    "PesquisarBabysitters",
    "Mensagens",
    "TodasNotificacoes",
    "PerfilBabysitter",
    "EditarPerfil",
    "Calendario",
    "Pagamentos",
    "Ganhos"
]

choice = st.sidebar.radio("Navegação", menu_options)

# --- FUNÇÕES DAS PÁGINAS ---

def page_dashboard_cliente():
    st.title("🏠 Dashboard do Cliente")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Agendamentos Ativos", len(st.session_state['agendamentos']))
    col2.metric("Total Gasto (Mês)", "€ 450,00")
    col3.metric("Babysitter Favorita", "Maria O.")
    
    st.subheader("📅 Próximos Serviços")
    st.dataframe(st.session_state['agendamentos'], use_container_width=True)

def page_dashboard_babysitter():
    st.title("🧸 Dashboard da Babysitter")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Próximos Trabalhos", "3")
    col2.metric("Ganhos (Mês)", "€ 850,00", "+12%")
    col3.metric("Avaliação Média", "4.9 ⭐")
    
    st.subheader("🗓️ Minha Agenda")
    st.dataframe(st.session_state['agendamentos'][['Data', 'Cliente', 'Status', 'Valor']], use_container_width=True)

def page_novo_servico():
    st.title("➕ Solicitar Nova Babá")
    
    with st.form("form_novo_servico"):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data do Serviço")
            hora_inicio = st.time_input("Hora de Início")
        with col2:
            duracao = st.number_input("Duração (horas)", min_value=1, value=4)
            qtd_criancas = st.number_input("Quantidade de Crianças", min_value=1, value=1)
            
        local = st.text_input("Endereço Completo")
        obs = st.text_area("Observações (Alergias, rotinas, etc.)")
        
        submitted = st.form_submit_button("🔍 Buscar e Solicitar")
        
        if submitted:
            # Simula a adição de um novo agendamento
            novo_servico = pd.DataFrame([{
                'Data': data,
                'Babysitter': 'Pendente',
                'Cliente': 'Você',
                'Status': 'Solicitado',
                'Valor': duracao * 35.0  # Preço base fictício
            }])
            st.session_state['agendamentos'] = pd.concat([st.session_state['agendamentos'], novo_servico], ignore_index=True)
            st.success("Solicitação enviada com sucesso! As babás serão notificadas.")

def page_pesquisar_babysitters():
    st.title("🔍 Encontrar Babysitter")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        cidade = st.selectbox("Cidade", ["Todas", "Lisboa", "Porto", "Coimbra"])
    with col2:
        preco_max = st.slider("Preço Máximo por Hora (€)", 20, 100, 50)
    
    # Lógica de Filtro
    df = st.session_state['babysitters']
    if cidade != "Todas":
        df = df[df['Localização'] == cidade]
    df = df[df['Preço/Hora'] <= preco_max]
    
    # Exibição dos Cards
    for index, row in df.iterrows():
        with st.container():
            c1, c2, c3 = st.columns([1, 3, 1])
            with c1:
                st.image(row['Foto'], width=80)
            with c2:
                st.subheader(row['Nome'])
                st.write(f"📍 {row['Localização']} | ⭐ {row['Avaliação']} | 💼 {row['Experiência']}")
            with c3:
                st.metric("Valor/Hora", f"€ {row['Preço/Hora']}")
                st.button("Ver Perfil", key=f"btn_{index}")
            st.divider()

def page_mensagens():
    st.title("💬 Mensagens")
    
    st.info("Conversando com: Maria Oliveira (Babá)")

    # Exibe histórico
    for msg in st.session_state['mensagens']:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Input de nova mensagem
    if prompt := st.chat_input("Digite sua mensagem..."):
        # Adiciona msg do usuário
        st.session_state['mensagens'].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        # Simula resposta automática
        time.sleep(1)
        resposta = "Obrigada! Confirmado então."
        st.session_state['mensagens'].append({"role": "assistant", "content": resposta})
        with st.chat_message("assistant"):
            st.write(resposta)

def page_notificacoes():
    st.title("🔔 Notificações")
    
    st.success("✅ Seu pagamento de €50,00 foi confirmado.")
    st.info("ℹ️ Lembrete: Babá agendada para amanhã às 19h.")
    st.warning("⚠️ Atualize seu perfil para aumentar a segurança.")
    st.error("❌ Um agendamento antigo foi cancelado.")

def page_perfil_babysitter():
    st.title("👤 Perfil Profissional")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://api.dicebear.com/7.x/avataaars/svg?seed=Maria", width=200)
    with col2:
        st.header("Maria Oliveira")
        st.write("**Bio:** Olá! Sou pedagoga e adoro crianças. Tenho curso de primeiros socorros.")
        st.write("**Idade:** 28 anos")
        st.write("**Experiência:** 5 anos")
        st.write("**Certificações:** Primeiros Socorros, Educação Infantil")
        
    st.subheader("Avaliações Recentes")
    st.write("⭐⭐⭐⭐⭐ 'Excelente profissional, meus filhos adoraram!' - *Ana P.*")
    st.write("⭐⭐⭐⭐⭐ 'Muito pontual e atenciosa.' - *Carlos M.*")

def page_editar_perfil():
    st.title("⚙️ Configurações do Perfil")
    
    tab1, tab2 = st.tabs(["Dados Pessoais", "Segurança"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Nome Completo", "Nuno Rodrigues")
            st.text_input("Email", "nuno@email.com")
        with col2:
            st.text_input("Telefone", "+351 912 345 678")
            st.text_input("Cidade", "Lisboa")
        st.button("Salvar Alterações")
        
    with tab2:
        st.text_input("Senha Atual", type="password")
        st.text_input("Nova Senha", type="password")
        st.button("Alterar Senha")

def page_calendario():
    st.title("🗓️ Calendário de Agendamentos")
    
    data_selecionada = st.date_input("Verificar disponibilidade no dia:", datetime.now())
    
    st.write(f"### Agendamentos para {data_selecionada.strftime('%d/%m/%Y')}")
    
    # Filtra agendamentos do dia (conversão simples para demo)
    df = st.session_state['agendamentos']
    # Nota: Em produção, converteríamos colunas de data corretamente
    # Aqui apenas mostramos a tabela geral para ilustração
    st.dataframe(df, use_container_width=True)

def page_pagamentos():
    st.title("💳 Histórico de Pagamentos")
    
    df = st.session_state['pagamentos']
    
    # Função para colorir o status
    def color_status(val):
        color = 'green' if val == 'Pago' else 'red'
        return f'color: {color}'

    st.dataframe(df.style.map(color_status, subset=['Status']), use_container_width=True)

def page_ganhos():
    st.title("📈 Meus Ganhos (Babysitter)")
    
    # Dados fictícios para o gráfico
    dados_ganhos = pd.DataFrame({
        'Mês': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
        'Ganhos (€)': [450, 600, 550, 800, 750, 900]
    })
    
    # Gráfico Plotly
    fig = px.bar(dados_ganhos, x='Mês', y='Ganhos (€)', title="Faturamento Semestral",
                 text_auto=True, color='Ganhos (€)', color_continuous_scale='Blues')
    
    st.plotly_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    col1.metric("Média Mensal", "€ 675,00")
    col2.metric("Melhor Mês", "Junho")

# --- ROTEAMENTO DAS PÁGINAS ---
if choice == "Dashboard_Cliente":
    page_dashboard_cliente()
elif choice == "Dashboard_Babysitter":
    page_dashboard_babysitter()
elif choice == "NovoServico":
    page_novo_servico()
elif choice == "PesquisarBabysitters":
    page_pesquisar_babysitters()
elif choice == "Mensagens":
    page_mensagens()
elif choice == "TodasNotificacoes":
    page_notificacoes()
elif choice == "PerfilBabysitter":
    page_perfil_babysitter()
elif choice == "EditarPerfil":
    page_editar_perfil()
elif choice == "Calendario":
    page_calendario()
elif choice == "Pagamentos":
    page_pagamentos()
elif choice == "Ganhos":
    page_ganhos()