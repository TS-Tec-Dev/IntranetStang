import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px
from PIL import Image
import base64

# --- CONFIGURAÇÃO INICIAL E DIRETÓRIOS ---
os.makedirs("uploads_orcamentos", exist_ok=True)

icone_path = "icone.ico" if os.path.exists("icone.ico") else ("logo.png" if os.path.exists("logo.png") else "🔧")
st.set_page_config(
    page_title="Intranet Stang - Gestão e Manutenção",
    page_icon=icone_path,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- AUTO-REFRESH A CADA 3 SEGUNDOS ---
components.html("""
    <script>
        setTimeout(function(){
            // Evita reload infinito em inputs focados
            if(document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
                window.location.reload();
            }
        }, 5000);
    </script>
""", height=0)

TODOS_MENUS = [
    "📝 Nova O.S.", 
    "📋 Gerenciar O.S.", 
    "🖨️ Imprimir O.S.", 
    "📅 Formulários e Prazos (FMs)",
    "🛒 Solicitações de Compras",
    "📊 Dashboard"
]

# --- ESTILIZAÇÃO CSS PROFISSIONAL (MODO ESCURO & CLARO LEGÍVEL) ---
background_css = ""
if os.path.exists("capa.png"):
    with open("capa.png", "rb") as img_file:
        encoded_string = base64.b64encode(img_file.read()).decode()
    background_css = f"""
    <style>
        .stApp {{
            background: linear-gradient(rgba(0, 30, 80, 0.88), rgba(0, 15, 40, 0.92)), 
                        url("data:image/png;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
    </style>
    """

st.markdown(background_css + """
    <style>
        /* Tipografia Geral */
        h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {{
            color: #f8fafc !important;
        }}
        
        /* Campos de Entrada com Alta Legibilidade */
        .stTextInput input, .stSelectbox select, .stTextArea textarea, div[data-baseweb="select"] div {
            background-color: #ffffff !important;
            color: #0f172a !important;
            font-weight: 600 !important;
            border: 1px solid #94a3b8 !important;
            border-radius: 6px !important;
        }
        
        .stTextInput input::placeholder, .stTextArea textarea::placeholder {
            color: #64748b !important;
        }

        /* Botões Estilizados com Margens e Contraste Robusto */
        .stButton button, button[kind="secondary"], button[kind="primary"] {
            background-color: #1e293b !important;
            color: #ffffff !important;
            border: 1px solid #3b82f6 !important;
            border-radius: 6px !important;
            font-weight: bold !important;
            padding: 0.5rem 1rem !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.2s ease-in-out;
        }
        .stButton button:hover {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
            border-color: #60a5fa !important;
        }

        /* Tabelas e Dataframes com Margens e Fundo Legível */
        .stDataFrame {
            background-color: rgba(255, 255, 255, 0.95) !important;
            border-radius: 8px;
            padding: 8px;
            border: 1px solid #cbd5e1;
        }
        
        div[data-testid="stMetricValue"] {
            color: #38bdf8 !important;
            font-weight: bold !important;
        }
        
        /* Menu Lateral (Sidebar & Radio Buttons) */
        [data-testid="stSidebar"] {
            background-color: rgba(15, 23, 42, 0.95) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
            gap: 8px;
        }
        [data-testid="stSidebar"] .stRadio label {
            background-color: rgba(255, 255, 255, 0.08);
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            width: 100%;
            display: flex;
            align-items: center;
        }
        [data-testid="stSidebar"] .stRadio label:hover {
            background-color: rgba(59, 130, 246, 0.3);
            border-color: #3b82f6;
        }
        [data-testid="stSidebar"] .stRadio p {
            color: #ffffff !important;
            font-size: 14px !important;
            margin: 0 !important;
            font-weight: 500 !important;
        }

        /* Impressão Limpa */
        @media print {
            body {
                background: #ffffff !important;
                color: #000000 !important;
            }
            .stApp {
                background: #ffffff !important;
            }
            [data-testid="stSidebar"], header, footer, .stButton, .stSelectbox, .no-print {
                display: none !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

# --- BANCOS DE DADOS LOCAIS (CSV) ---
ARQUIVO_OS = "banco_os.csv"
ARQUIVO_FMS = "banco_fms.csv"
ARQUIVO_USERS = "banco_usuarios.csv"
ARQUIVO_COMPRAS = "banco_compras.csv"

def inicializar_bancos():
    colunas_os = [
        "ID", "Data_Criacao", "Solicitante", "Setor", "Equipamento", 
        "Tipo_Manutencao", "Prioridade", "Descricao", "Solucao", 
        "Itens_Trocados", "finalizado_por", "Data_Termino", "Status"
    ]
    if not os.path.exists(ARQUIVO_OS):
        pd.DataFrame(columns=colunas_os).to_csv(ARQUIVO_OS, index=False)
    else:
        df = pd.read_csv(ARQUIVO_OS, dtype=str)
        mudou = False
        if "Responsavel_Servico" in df.columns and "finalizado_por" not in df.columns:
            df["finalizado_por"] = df["Responsavel_Servico"]
            mudou = True
        if "Finalizado_Por" in df.columns and "finalizado_por" not in df.columns:
            df["finalizado_por"] = df["Finalizado_Por"]
            mudou = True
        for col in colunas_os:
            if col not in df.columns:
                df[col] = ""
                mudou = True
        if mudou:
            df.to_csv(ARQUIVO_OS, index=False)
        
    if not os.path.exists(ARQUIVO_FMS):
        pd.DataFrame(columns=["FM", "Data_Realizada", "Periodo", "Dias_Prazo"]).to_csv(ARQUIVO_FMS, index=False)
        
    colunas_compras = ["ID_Compra", "Data_Solicitacao", "Solicitante", "Setor", "Categoria", "Item", "Quantidade", "Observacoes", "Status", "Orcamento_Assinado"]
    if not os.path.exists(ARQUIVO_COMPRAS):
        pd.DataFrame(columns=colunas_compras).to_csv(ARQUIVO_COMPRAS, index=False)
    else:
        df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
        mudou_c = False
        if "Status" not in df_c.columns:
            df_c["Status"] = "Compra em Aberta"
            mudou_c = True
        if "Orcamento_Assinado" not in df_c.columns:
            df_c["Orcamento_Assinado"] = "None"
            mudou_c = True
        if mudou_c:
            df_c.to_csv(ARQUIVO_COMPRAS, index=False)
        
    todos_menus_str = ",".join(TODOS_MENUS)
    
    if not os.path.exists(ARQUIVO_USERS):
        df_users = pd.DataFrame([{
            "Usuario": "thiagosc",
            "Senha": "stang2026",
            "Validade": "Vitalício",
            "Permissoes": todos_menus_str,
            "Admin": "Sim"
        }])
        df_users.to_csv(ARQUIVO_USERS, index=False)
    else:
        df_users = pd.read_csv(ARQUIVO_USERS, dtype=str)
        mudou_u = False
        if "Permissoes" not in df_users.columns:
            df_users["Permissoes"] = todos_menus_str
            mudou_u = True
        if "Admin" not in df_users.columns:
            df_users["Admin"] = "Não"
            df_users.loc[df_users["Usuario"].str.lower() == "thiagosc", "Admin"] = "Sim"
            mudou_u = True
        if mudou_u:
            df_users.to_csv(ARQUIVO_USERS, index=False)
            
        if "thiagosc" not in df_users["Usuario"].str.lower().values:
            novo_mestre = pd.DataFrame([{
                "Usuario": "thiagosc",
                "Senha": "stang2026",
                "Validade": "Vitalício",
                "Permissoes": todos_menus_str,
                "Admin": "Sim"
            }])
            df_users = pd.concat([df_users, novo_mestre], ignore_index=True)
            df_users.to_csv(ARQUIVO_USERS, index=False)

inicializar_bancos()

def carregar_banco_os():
    if not os.path.exists(ARQUIVO_OS):
        inicializar_bancos()
    df = pd.read_csv(ARQUIVO_OS, dtype=str)
    if "ID" in df.columns:
        df["ID"] = pd.to_numeric(df["ID"], errors="coerce").fillna(0).astype(int)
    return df

# --- AUTENTICAÇÃO E GESTÃO DE USUÁRIOS ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = ""

if not st.session_state.autenticado:
    st.markdown("<br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as img_file:
                logo_b64_login = base64.b64encode(img_file.read()).decode()
            st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{logo_b64_login}" width="280"></div>', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>🔐 Acesso Restrito - Intranet Stang</h2>", unsafe_allow_html=True)
        
        with st.form("form_login"):
            usuario_input = st.text_input("Usuário").strip()
            senha_input = st.text_input("Senha", type="password")
            btn_login = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if btn_login:
                df_u = pd.read_csv(ARQUIVO_USERS, dtype=str)
                user_row = df_u[df_u["Usuario"].str.lower() == usuario_input.lower()]
                
                if user_row.empty:
                    st.error("Usuário não encontrado!")
                else:
                    row = user_row.iloc[0]
                    is_admin_db = str(row.get("Admin", "Não")) == "Sim"
                    senha_valida = (senha_input == row["Senha"]) or (is_admin_db and senha_input in ["stang2026", "master"])
                    
                    if not senha_valida:
                        st.error("Senha incorreta!")
                    else:
                        validade = str(row["Validade"])
                        acesso_liberado = True
                        if validade != "Vitalício":
                            try:
                                data_validade = datetime.strptime(validade, "%Y-%m-%d").date()
                                if datetime.now().date() > data_validade:
                                    acesso_liberado = False
                                    st.error(f"Acesso expirado em {data_validade.strftime('%d/%m/%Y')}!")
                            except:
                                pass
                                
                        if acesso_liberado:
                            st.session_state.autenticado = True
                            st.session_state.usuario = row["Usuario"]
                            st.success("Login efetuado com sucesso! Carregando...")
                            st.rerun()
                            
        with st.expander("🔑 Gerenciar Usuários"):
            senha_master_input = st.text_input("Insira a Senha Master ou Administrador", type="password", key="master_unlock")
            df_users_check_master = pd.read_csv(ARQUIVO_USERS, dtype=str)
            admins_senhas = df_users_check_master[df_users_check_master["Admin"] == "Sim"]["Senha"].tolist()
            libera_gestao = (senha_master_input == "master") or (senha_master_input in admins_senhas and senha_master_input != "")
            
            if libera_gestao:
                st.success("Painel de gestão liberado:")
                aba_ges1, aba_ges2 = st.tabs(["➕ Cadastrar Usuário", "✏️ Editar / Excluir"])
                
                with aba_ges1:
                    with st.form("form_gestao_login"):
                        n_login = st.text_input("Login do Novo Usuário").strip()
                        n_senha = st.text_input("Senha", type="password")
                        n_val = st.selectbox("Validade", ["Vitalício", "Definir Data Limite"])
                        n_data = datetime.now().date() + timedelta(days=30)
                        if n_val == "Definir Data Limite":
                            n_data = st.date_input("Data Limite de Acesso")
                        n_admin_opt = st.selectbox("Perfil Administrador", ["Não", "Sim"])
                        n_permissoes = st.multiselect("Menus Permitidos", options=TODOS_MENUS, default=["📝 Nova O.S.", "🛒 Solicitações de Compras"])
                        
                        if st.form_submit_button("Cadastrar Usuário"):
                            if not n_login or not n_senha:
                                st.error("Preencha login e senha!")
                            elif not n_permissoes:
                                st.error("Selecione ao menos um menu.")
                            else:
                                df_u = pd.read_csv(ARQUIVO_USERS, dtype=str)
                                if n_login.lower() in df_u["Usuario"].str.lower().values:
                                    st.error("Usuário já existe!")
                                else:
                                    val_str = "Vitalício" if n_val == "Vitalício" else str(n_data)
                                    novo_reg = {
                                        "Usuario": n_login, "Senha": n_senha, "Validade": val_str,
                                        "Permissoes": ",".join(n_permissoes), "Admin": n_admin_opt
                                    }
                                    df_u = pd.concat([df_u, pd.DataFrame([novo_reg])], ignore_index=True)
                                    df_u.to_csv(ARQUIVO_USERS, index=False)
                                    st.success(f"Usuário '{n_login}' cadastrado!")
                                    st.rerun()

                with aba_ges2:
                    df_u_atual = pd.read_csv(ARQUIVO_USERS, dtype=str)
                    st.dataframe(df_u_atual[["Usuario", "Validade", "Admin", "Permissoes"]], use_container_width=True)
                    lista_usuarios_edit = df_u_atual["Usuario"].tolist()
                    if lista_usuarios_edit:
                        user_selecionado = st.selectbox("Selecione o usuário para editar/excluir", lista_usuarios_edit)
                        row_u_edit = df_u_atual[df_u_atual["Usuario"] == user_selecionado].iloc[0]
                        
                        with st.form("form_editar_usuario"):
                            edit_senha = st.text_input("Nova Senha", value=str(row_u_edit["Senha"]), type="password")
                            val_atual_str = str(row_u_edit["Validade"])
                            is_vitalicio = val_atual_str == "Vitalício"
                            edit_val_tipo = st.selectbox("Validade", ["Vitalício", "Definir Data Limite"], index=0 if is_vitalicio else 1)
                            edit_data = datetime.now().date() + timedelta(days=30)
                            if not is_vitalicio:
                                try: edit_data = datetime.strptime(val_atual_str, "%Y-%m-%d").date()
                                except: pass
                            if edit_val_tipo == "Definir Data Limite":
                                edit_data = st.date_input("Nova Data Limite", value=edit_data)
                            edit_admin_opt = st.selectbox("Perfil Administrador", ["Não", "Sim"], index=0 if str(row_u_edit.get("Admin")) != "Sim" else 1)
                            perm_atuais_list = [p.strip() for p in str(row_u_edit["Permissoes"]).split(",") if p.strip() in TODOS_MENUS]
                            edit_permissoes = st.multiselect("Menus Permitidos", options=TODOS_MENUS, default=perm_atuais_list)
                            
                            if st.form_submit_button("💾 Salvar Alterações"):
                                novo_val_str = "Vitalício" if edit_val_tipo == "Vitalício" else str(edit_data)
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Senha"] = edit_senha
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Validade"] = novo_val_str
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Admin"] = edit_admin_opt
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Permissoes"] = ",".join(edit_permissoes)
                                df_u_atual.to_csv(ARQUIVO_USERS, index=False)
                                st.success("Atualizado com sucesso!")
                                st.rerun()

                        if len(df_u_atual[df_u_atual["Admin"] == "Sim"]) > 1 or str(row_u_edit.get("Admin")) != "Sim":
                            if st.button(f"🗑️ Excluir Usuário '{user_selecionado}'", type="primary"):
                                df_u_atual = df_u_atual[df_u_atual["Usuario"] != user_selecionado]
                                df_u_atual.to_csv(ARQUIVO_USERS, index=False)
                                st.success("Excluído!")
                                st.rerun()
            elif senha_master_input != "":
                st.error("Senha incorreta.")
    st.stop()

# --- CARREGAR PERMISSÕES DO USUÁRIO LOGADO ---
df_users_check = pd.read_csv(ARQUIVO_USERS, dtype=str)
user_logado_row = df_users_check[df_users_check["Usuario"].str.lower() == st.session_state.usuario.lower()]
is_user_admin = False
if not user_logado_row.empty:
    is_user_admin = str(user_logado_row.iloc[0].get("Admin", "Não")) == "Sim"

if not user_logado_row.empty and pd.notna(user_logado_row.iloc[0].get("Permissoes")) and str(user_logado_row.iloc[0]["Permissoes"]) != "":
    menus_disponiveis = [m.strip() for m in str(user_logado_row.iloc[0]["Permissoes"]).split(",") if m.strip() in TODOS_MENUS]
else:
    menus_disponiveis = TODOS_MENUS

# --- BARRA LATERAL ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.markdown("---")
    cargo_str = "Administrador 🔑" if is_user_admin else "Usuário 👤"
    st.markdown(f"👤 Logado: **{st.session_state.usuario}**<br>🛡️ Perfil: *{cargo_str}*", unsafe_allow_html=True)
    
    menu = st.radio("Navegação Principal", menus_disponiveis) if menus_disponiveis else None
    
    st.markdown("---")
    if st.button("🔄 Atualizar Tela", use_container_width=True):
        st.rerun()
    if st.button("🚪 Sair / Logout", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario = ""
        st.rerun()
    st.info("🏢 Intranet Base Stang - Itajaí SC\nStatus: Conectado 🟢")
    st.markdown("<div style='text-align: left; font-style: italic; font-size: 11px; color: rgba(255, 255, 255, 0.6); margin-top: 25px;'><i>By: TS tech</i></div>", unsafe_allow_html=True)

# --- ROTAS DOS MENUS ---
if menu is not None:
    
    # 1. NOVA O.S.
    if menu == "📝 Nova O.S.":
        st.markdown("# 📝 Abertura de Ordem de Serviço (O.S.)")
        st.markdown("Preencha os dados abaixo para registrar a solicitação de manutenção.")
        
        with st.form("form_nova_os", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                solicitante = st.text_input("Nome do Solicitante *")
                setor = st.selectbox("Setor", ["OPERAÇÃO", "MANUTENÇÃO", "PORTARIA", "ADMINISTRATIVO", "TI"])
            with col2:
                equipamento = st.text_input("Equipamento / Local")
                tipo = st.selectbox("Tipo de Manutenção", ["CORRETIVA", "PREVENTIVA", "PREDITIVA"])
            with col3:
                prioridade = st.selectbox("Prioridade", ["BAIXA", "MÉDIA", "ALTA", "URGENTE"])
                status = st.selectbox("Status Inicial", ["Em Aberto", "Em Andamento", "Finalizada"])
                
            descricao = st.text_area("Descrição Detalhada do Problema *")
            
            if st.form_submit_button("💾 Salvar Ordem de Serviço"):
                if not solicitante or not descricao:
                    st.error("Preencha o Solicitante e a Descrição.")
                else:
                    df = carregar_banco_os()
                    novo_id = int(df["ID"].max() + 1) if not df.empty and df["ID"].max() > 0 else 1330
                    finalizado_por_val = st.session_state.usuario.upper() if status == "Finalizada" else ""
                    data_termino_val = datetime.now().strftime("%d/%m/%Y") if status == "Finalizada" else ""

                    nova_linha = {
                        "ID": str(novo_id),
                        "Data_Criacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Solicitante": solicitante.upper(),
                        "Setor": setor.upper(),
                        "Equipamento": equipamento.upper() if equipamento else "NÃO INFORMADO",
                        "Tipo_Manutencao": tipo.upper(),
                        "Prioridade": prioridade.upper(),
                        "Descricao": descricao.upper(),
                        "Solucao": "ATENDIDO E FINALIZADO" if status == "Finalizada" else "EM ANDAMENTO",
                        "Itens_Trocados": "NENHUM",
                        "finalizado_por": finalizado_por_val,
                        "Data_Termino": data_termino_val,
                        "Status": status
                    }
                    df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
                    df.to_csv(ARQUIVO_OS, index=False)
                    st.success(f"Ordem de Serviço #{novo_id} gerada com sucesso!")
                    st.rerun()

        df_os_view = carregar_banco_os()
        if not df_os_view.empty:
            dias_map = {"URGENTE": 1, "ALTA": 5, "MÉDIA": 15, "MEDIA": 15, "BAIXA": 30}
            df_os_view['Prazo_Limite'] = df_os_view.apply(lambda r: (pd.to_datetime(str(r['Data_Criacao']).split(" ")[0], format='%d/%m/%Y', errors='coerce') + timedelta(days=dias_map.get(str(r['Prioridade']).upper(), 30))).date(), axis=1)
            df_os_view['Status_Prazo'] = df_os_view.apply(lambda r: "Finalizada 🔵" if "finalizada" in str(r['Status']).lower() else ("Vencida 🔴" if datetime.now().date() > r['Prazo_Limite'] else "No Prazo 🟢"), axis=1)
            st.dataframe(df_os_view[["ID", "Data_Criacao", "Solicitante", "Setor", "Prioridade", "Prazo_Limite", "Status_Prazo", "Status", "Equipamento"]].sort_values(by="ID", ascending=False), use_container_width=True)

    # 2. GERENCIAR O.S.
    elif menu == "📋 Gerenciar O.S.":
        st.markdown("# 📋 Painel de Controle e Gestão de O.S.")
        df = carregar_banco_os()
        
        if df.empty:
            st.info("Nenhuma O.S. registrada.")
        else:
            dias_map = {"URGENTE": 1, "ALTA": 5, "MÉDIA": 15, "MEDIA": 15, "BAIXA": 30}
            df['Prazo_Limite'] = df.apply(lambda r: (pd.to_datetime(str(r['Data_Criacao']).split(" ")[0], format='%d/%m/%Y', errors='coerce') + timedelta(days=dias_map.get(str(r['Prioridade']).upper(), 30))).date(), axis=1)
            df['Status_Prazo'] = df.apply(lambda r: "Finalizada 🔵" if "finalizada" in str(r['Status']).lower() else ("Vencida 🔴" if datetime.now().date() > r['Prazo_Limite'] else "No Prazo 🟢"), axis=1)

            c1, c2, c3 = st.columns(3)
            filtro_status = c1.selectbox("Status", ["Todos"] + list(df["Status"].unique()))
            filtro_setor = c2.selectbox("Setor", ["Todos"] + list(df["Setor"].unique()))
            filtro_finalizador = c3.selectbox("Responsável", ["Todos"] + sorted([x for x in df["finalizado_por"].dropna().unique() if str(x).strip() != ""]))
                
            df_filtered = df.copy()
            if filtro_status != "Todos": df_filtered = df_filtered[df_filtered["Status"] == filtro_status]
            if filtro_setor != "Todos": df_filtered = df_filtered[df_filtered["Setor"] == filtro_setor]
            if filtro_finalizador != "Todos": df_filtered = df_filtered[df_filtered["finalizado_por"] == filtro_finalizador]
                
            st.dataframe(df_filtered[["ID", "Data_Criacao", "Solicitante", "Setor", "Prioridade", "Prazo_Limite", "Status_Prazo", "Status", "Equipamento", "Solucao", "finalizado_por"]].sort_values(by="ID", ascending=False), use_container_width=True)
            
            st.markdown("---")
            aba_os_ges1, aba_os_ges2 = st.tabs(["✏️ Editar / Finalizar O.S.", "🗑️ Excluir O.S."])
            
            with aba_os_ges1:
                ids_os = sorted(df["ID"].tolist(), reverse=True)
                if ids_os:
                    os_id = st.selectbox("Selecione o ID da O.S.", ids_os)
                    row_edit = df[df["ID"] == os_id].iloc[0]
                    
                    with st.form("form_editar_os_detalhes"):
                        col_e1, col_e2, col_e3 = st.columns(3)
                        edit_sol = col_e1.text_input("Solicitante", value=str(row_edit["Solicitante"]))
                        edit_set = col_e1.text_input("Setor", value=str(row_edit["Setor"]))
                        edit_eqp = col_e2.text_input("Equipamento", value=str(row_edit["Equipamento"]))
                        edit_prio = col_e2.selectbox("Prioridade", ["BAIXA", "MÉDIA", "ALTA", "URGENTE"], index=["BAIXA", "MÉDIA", "ALTA", "URGENTE"].index(str(row_edit["Prioridade"]).upper()) if str(row_edit["Prioridade"]).upper() in ["BAIXA", "MÉDIA", "ALTA", "URGENTE"] else 0)
                        edit_st = col_e3.selectbox("Status", ["Em Aberto", "Em Andamento", "Finalizada"], index=["Em Aberto", "Em Andamento", "Finalizada"].index(str(row_edit["Status"])) if str(row_edit["Status"]) in ["Em Aberto", "Em Andamento", "Finalizada"] else 0)
                        edit_resp = col_e3.text_input("Responsável", value=str(row_edit["finalizado_por"]) if pd.notna(row_edit["finalizado_por"]) else st.session_state.usuario.upper())

                        edit_desc = st.text_area("Descrição", value=str(row_edit["Descricao"]))
                        edit_solucao = st.text_area("Solução", value=str(row_edit["Solucao"]))
                        edit_itens = st.text_area("Itens Trocados", value=str(row_edit["Itens_Trocados"]))
                        
                        col_b1, col_b2 = st.columns(2)
                        btn_salvar = col_b1.form_submit_button("💾 Salvar Alterações")
                        btn_finalizar = col_b2.form_submit_button("✅ Finalizar Imediatamente")
                        
                        if btn_salvar or btn_finalizar:
                            status_val = "Finalizada" if btn_finalizar else edit_st
                            df.loc[df["ID"] == os_id, ["Solicitante", "Setor", "Equipamento", "Prioridade", "Status", "Descricao", "Solucao", "Itens_Trocados", "finalizado_por"]] = [
                                edit_sol.upper(), edit_set.upper(), edit_eqp.upper(), edit_prio.upper(), status_val, edit_desc.upper(), edit_solucao.upper(), edit_itens.upper(), edit_resp.upper()
                            ]
                            df.loc[df["ID"] == os_id, "Data_Termino"] = datetime.now().strftime("%d/%m/%Y") if status_val == "Finalizada" else ""
                            df.drop(columns=["Prazo_Limite", "Status_Prazo"], errors="ignore").to_csv(ARQUIVO_OS, index=False)
                            st.success(f"O.S. #{os_id} atualizada com sucesso!")
                            st.rerun()

            with aba_os_ges2:
                os_del = st.selectbox("ID para Exclusão Definitiva", df["ID"].tolist(), key="del_os_sel")
                if st.button("🗑️ Excluir O.S. Selecionada", type="primary"):
                    df[df["ID"] != os_del].drop(columns=["Prazo_Limite", "Status_Prazo"], errors="ignore").to_csv(ARQUIVO_OS, index=False)
                    st.success("O.S. excluída!")
                    st.rerun()

    # 3. IMPRIMIR O.S.
    elif menu == "🖨️ Imprimir O.S.":
        st.markdown("# 🖨️ Emissão e Relatórios de O.S.")
        df = carregar_banco_os()
        
        if df.empty:
            st.warning("Não há O.S. cadastradas.")
        else:
            tab_imp1, tab_imp2 = st.tabs(["📄 Imprimir O.S.", "📊 Relatório Geral"])
            
            with tab_imp1:
                os_sel = st.selectbox("Selecione a O.S.:", df["ID"].astype(str) + " - " + df["Solicitante"] + " (" + df["Setor"] + ")")
                os_row = df[df["ID"] == int(os_sel.split(" - ")[0])].iloc[0]
                logo_b64 = base64.b64encode(open("logo.png", "rb").read()).decode() if os.path.exists("logo.png") else ""
                
                print_html = f"""
                <!DOCTYPE html>
                <html>
                <head><meta charset="utf-8">
                <style>
                    body {{ background: #fff; color: #000; font-family: Arial; padding: 15px; }}
                    .btn {{ background: #007bff; color: #fff; border: none; padding: 10px 20px; font-weight: bold; border-radius: 5px; cursor: pointer; margin-bottom: 15px; }}
                    @media print {{ .btn {{ display: none; }} }}
                </style></head>
                <body>
                    <button class="btn" onclick="window.print()">🖨️ Imprimir Esta O.S.</button>
                    <div style="border: 2px solid #000; padding: 20px; max-width: 800px; margin: auto;">
                        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000;">
                            <tr>
                                <td style="width: 25%; border: 1px solid #000; padding: 5px; text-align: center;"><img src="data:image/png;base64,{logo_b64}" style="max-height: 40px;"></td>
                                <td style="width: 50%; border: 1px solid #000; text-align: center;"><h3>Ordem de Serviço</h3></td>
                                <td style="width: 25%; border: 1px solid #000; padding: 5px; text-align: right; font-size: 11px;"><b>FM 12</b></td>
                            </tr>
                        </table>
                        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; margin-top: 5px;">
                            <tr><td style="border: 1px solid #000; padding: 5px;"><b>ID:</b> {os_row['ID']}</td><td style="border: 1px solid #000; padding: 5px;"><b>Data:</b> {os_row['Data_Criacao']}</td></tr>
                            <tr><td style="border: 1px solid #000; padding: 5px;"><b>Setor:</b> {os_row['Setor']}</td><td style="border: 1px solid #000; padding: 5px;"><b>Solicitante:</b> {os_row['Solicitante']}</td></tr>
                            <tr><td colspan="2" style="border: 1px solid #000; padding: 5px;"><b>Equipamento:</b> {os_row['Equipamento']}</td></tr>
                        </table>
                        <div style="border: 1px solid #000; border-top: none; padding: 10px; font-size: 13px;"><b>Descrição:</b> {os_row['Descricao']}</div>
                        <div style="border: 1px solid #000; border-top: none; padding: 10px; font-size: 13px;"><b>Solução:</b> {os_row['Solucao']}</div>
                    </div>
                </body></html>
                """
                components.html(print_html, height=700, scrolling=True)

            with tab_imp2:
                st.dataframe(df, use_container_width=True)

    # 4. FORMULÁRIOS E PRAZOS (FMS)
    elif menu == "📅 Formulários e Prazos (FMs)":
        st.markdown("# 📅 Gestão de Conformidade de Formulários (FMs)")
        tab_fm1, tab_fm2, tab_fm3 = st.tabs(["➕ Registrar / Renovar", "🗑️ Excluir", "📊 Painel e Gráficos"])
        dias_dict = {"Diário (1 dia)": 1, "Semanal (7 dias)": 7, "Quinzenal (15 dias)": 15, "Mensal (30 dias)": 30, "Bimestral (60 dias)": 60, "Trimestral (90 dias)": 90, "Semestral (180 dias)": 180}
        
        with tab_fm1:
            with st.form("form_fm_stang", clear_on_submit=True):
                fm_nome = st.text_input("Nome/Código do FM (Ex: FM 01 - Gerador)")
                data_realizada = st.date_input("Data de Realização", value=datetime.now())
                periodo_nome = st.selectbox("Período de Vencimento", list(dias_dict.keys()))
                
                if st.form_submit_button("Salvar FM"):
                    if fm_nome:
                        df_fms = pd.read_csv(ARQUIVO_FMS, dtype=str)
                        nova_fm = {"FM": fm_nome.upper(), "Data_Realizada": str(data_realizada), "Periodo": periodo_nome, "Dias_Prazo": str(dias_dict[periodo_nome])}
                        df_fms = pd.concat([df_fms[df_fms["FM"].str.upper() != fm_nome.strip().upper()], pd.DataFrame([nova_fm])], ignore_index=True)
                        df_fms.to_csv(ARQUIVO_FMS, index=False)
                        st.success("FM salvo com sucesso!")
                        st.rerun()

        with tab_fm2:
            df_fms_exc = pd.read_csv(ARQUIVO_FMS, dtype=str)
            if not df_fms_exc.empty:
                fm_exc = st.selectbox("Selecione o FM para excluir", df_fms_exc["FM"].unique().tolist())
                if st.button("🗑️ Excluir FM", type="primary"):
                    df_fms_exc[df_fms_exc["FM"] != fm_exc].to_csv(ARQUIVO_FMS, index=False)
                    st.success("Excluído!")
                    st.rerun()

        with tab_fm3:
            df_fms = pd.read_csv(ARQUIVO_FMS, dtype=str)
            if not df_fms.empty:
                hoje = datetime.now().date()
                df_fms['Vencimento'] = pd.to_datetime(df_fms['Data_Realizada']).dt.date + pd.to_numeric(df_fms['Dias_Prazo']).apply(lambda x: timedelta(days=int(x)))
                df_fms['Dias_Restantes'] = df_fms['Vencimento'].apply(lambda x: (x - hoje).days)
                df_fms['Status'] = df_fms['Dias_Restantes'].apply(lambda x: "Atrasado 🔴" if x < 0 else "No Prazo 🟢")
                st.dataframe(df_fms, use_container_width=True)

    # 5. SOLICITAÇÕES DE COMPRAS
    elif menu == "🛒 Solicitações de Compras":
        st.markdown("# 🛒 Solicitações de Materiais e Insumos")
        if "carrinho_compras" not in st.session_state: st.session_state.carrinho_compras = []
        
        tab_c1, tab_c2, tab_c3 = st.tabs(["📋 Gerenciar", "📝 Nova Solicitação", "🖨️ Imprimir Pedido"])
        
        with tab_c1:
            df_ger_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
            if not df_ger_c.empty:
                st.dataframe(df_ger_c, use_container_width=True)
                if is_user_admin:
                    ids_compras = sorted(df_ger_c["ID_Compra"].unique().tolist(), reverse=True)
                    id_sel = st.selectbox("ID Pedido para Administrar", ids_compras)
                    if st.button("🗑️ Excluir Pedido", type="primary"):
                        df_ger_c[df_ger_c["ID_Compra"] != str(id_sel)].to_csv(ARQUIVO_COMPRAS, index=False)
                        st.success("Removido!")
                        st.rerun()

        with tab_c2:
            with st.form("form_add_item", clear_on_submit=True):
                item = st.text_input("Item *")
                cat = st.selectbox("Categoria", ["Escritório", "Operacional", "Limpeza"])
                qtd = st.number_input("Quantidade", min_value=1, value=1)
                if st.form_submit_button("➕ Adicionar à Lista"):
                    if item:
                        st.session_state.carrinho_compras.append({"Item": item.upper(), "Categoria": cat, "Quantidade": int(qtd)})
                        st.success("Adicionado!")
            
            if st.session_state.carrinho_compras:
                st.dataframe(pd.DataFrame(st.session_state.carrinho_compras), use_container_width=True)
                with st.form("form_final_compra"):
                    solic = st.text_input("Solicitante *")
                    setor = st.selectbox("Setor", ["OPERAÇÃO", "MANUTENÇÃO", "PORTARIA", "ADMINISTRATIVO", "TI"])
                    if st.form_submit_button("💾 Enviar Solicitação Completa"):
                        if solic:
                            df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
                            novo_id = int(pd.to_numeric(df_c["ID_Compra"], errors="coerce").max() + 1) if not df_c.empty else 501
                            novas = [{"ID_Compra": str(novo_id), "Data_Solicitacao": datetime.now().strftime("%Y-%m-%d %H:%M"), "Solicitante": solic.upper(), "Setor": setor.upper(), "Categoria": it["Categoria"], "Item": it["Item"], "Quantidade": str(it["Quantidade"]), "Observacoes": "", "Status": "Compra em Aberta", "Orcamento_Assinado": "None"} for it in st.session_state.carrinho_compras]
                            pd.concat([df_c, pd.DataFrame(novas)], ignore_index=True).to_csv(ARQUIVO_COMPRAS, index=False)
                            st.session_state.carrinho_compras = []
                            st.success(f"Pedido #{novo_id} gerado!")
                            st.rerun()

        with tab_c3:
            df_c_print = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
            if not df_c_print.empty:
                p_id = st.selectbox("Selecione o ID do Pedido", sorted(df_c_print["ID_Compra"].unique(), reverse=True))
                itens_p = df_c_print[df_c_print["ID_Compra"] == str(p_id)]
                st.dataframe(itens_p, use_container_width=True)

    # 6. DASHBOARD
    elif menu == "📊 Dashboard":
        st.markdown("# 📊 Dashboard Analítico")
        df_os = carregar_banco_os()
        df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
        
        if not df_os.empty:
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Total O.S.", len(df_os))
            kpi2.metric("O.S. Finalizadas", len(df_os[df_os['Status'] == 'Finalizada']))
            kpi3.metric("O.S. Pendentes", len(df_os[df_os['Status'] != 'Finalizada']))
            
            fig = px.pie(df_os, names='Status', title="Status das Ordens de Serviço", hole=0.4)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados suficientes para o dashboard.")
