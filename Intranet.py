import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px
from PIL import Image
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Cria diretórios de uploads se não existirem
os.makedirs("uploads_orcamentos", exist_ok=True)
os.makedirs("uploads_assinaturas", exist_ok=True)

# Configuração da página
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
        setInterval(function(){
            window.location.reload();
        }, 3000);
    </script>
""", height=0)

# --- ESTILIZAÇÃO CSS COMPACTA & OTIMIZADA ---
custom_css = """
    <style>
        /* Redução de espaçamentos globais do Streamlit */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
        h1, h2, h3, h4 {
            margin-top: 0.2rem !important;
            margin-bottom: 0.4rem !important;
            padding: 0 !important;
        }
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.5rem !important;
        }
        .stButton button {
            padding: 4px 12px !important;
            height: auto !important;
        }
        .stTextInput input, .stSelectbox select, .stTextArea textarea {
            padding: 4px 8px !important;
        }
        
        /* Menu lateral otimizado */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
            gap: 4px;
        }
        [data-testid="stSidebar"] .stRadio label {
            background-color: rgba(255, 255, 255, 0.08);
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            width: 100%;
        }

        /* Impressão limpa */
        @media print {
            body { background: #ffffff !important; color: #000000 !important; }
            .stApp { background: #ffffff !important; }
            [data-testid="stSidebar"], header, footer, .stButton, .stSelectbox, .no-print {
                display: none !important;
            }
        }
    </style>
"""

if os.path.exists("capa.png"):
    with open("capa.png", "rb") as img_file:
        encoded_string = base64.b64encode(img_file.read()).decode()
    custom_css += f"""
    <style>
        .stApp {{
            background: linear-gradient(rgba(0, 30, 80, 0.85), rgba(0, 15, 40, 0.90)), 
                        url("data:image/png;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
    </style>
    """
st.markdown(custom_css, unsafe_allow_html=True)

# Lista de Menus
TODOS_MENUS = [
    "📝 Nova O.S.", 
    "📋 Gerenciar O.S.", 
    "🖨️ Imprimir O.S.", 
    "📅 Formulários e Prazos (FMs)",
    "🛒 Solicitações de Compras",
    "📊 Dashboard"
]

# Bancos de Dados CSV
ARQUIVO_OS = "banco_os.csv"
ARQUIVO_FMS = "banco_fms.csv"
ARQUIVO_USERS = "banco_usuarios.csv"
ARQUIVO_COMPRAS = "banco_compras.csv"
ARQUIVO_CONFIG_EMAIL = "banco_email_config.csv"

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
        for col in colunas_os:
            if col not in df.columns:
                df[col] = ""
                mudou = True
        if mudou: df.to_csv(ARQUIVO_OS, index=False)
        
    if not os.path.exists(ARQUIVO_FMS):
        pd.DataFrame(columns=["FM", "Data_Realizada", "Periodo", "Dias_Prazo"]).to_csv(ARQUIVO_FMS, index=False)
        
    colunas_compras = [
        "ID_Compra", "Data_Solicitacao", "Solicitante", "Setor", "Categoria", 
        "Item", "Quantidade", "Observacoes", "Status", "Orcamento_Assinado",
        "NF_Anexada", "Boleto_Anexado", "Assinado_Por", "Posicao_Assinatura"
    ]
    if not os.path.exists(ARQUIVO_COMPRAS):
        pd.DataFrame(columns=colunas_compras).to_csv(ARQUIVO_COMPRAS, index=False)
    else:
        df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
        mudou_c = False
        for col in colunas_compras:
            if col not in df_c.columns:
                df_c[col] = "None" if col in ["Orcamento_Assinado", "NF_Anexada", "Boleto_Anexado", "Assinado_Por"] else ("No final do documento" if col == "Posicao_Assinatura" else "")
                mudou_c = True
        if mudou_c: df_c.to_csv(ARQUIVO_COMPRAS, index=False)
        
    colunas_users = ["Usuario", "Senha", "Validade", "Permissoes", "Admin", "Assinatura_PNG", "Email_Usuario"]
    if not os.path.exists(ARQUIVO_USERS):
        df_users = pd.DataFrame([{
            "Usuario": "thiagosc", "Senha": "stang2026", "Validade": "Vitalício",
            "Permissoes": ",".join(TODOS_MENUS), "Admin": "Sim",
            "Assinatura_PNG": "None", "Email_Usuario": "thiagosc@stang.com.br"
        }])
        df_users.to_csv(ARQUIVO_USERS, index=False)
    else:
        df_u = pd.read_csv(ARQUIVO_USERS, dtype=str)
        mudou_u = False
        for col in colunas_users:
            if col not in df_u.columns:
                df_u[col] = "None" if col in ["Assinatura_PNG", "Email_Usuario"] else ""
                mudou_u = True
        if mudou_u: df_u.to_csv(ARQUIVO_USERS, index=False)

    if not os.path.exists(ARQUIVO_CONFIG_EMAIL):
        df_cfg_e = pd.DataFrame([{
            "Email_Remetente": "compras@stang.com.br",
            "Nome_Remetente": "Intranet Stang Compras",
            "API_Key": "",
            "Servidor_SMTP": "smtp.gmail.com",
            "Porta_SMTP": "587"
        }])
        df_cfg_e.to_csv(ARQUIVO_CONFIG_EMAIL, index=False)

inicializar_bancos()

def carregar_banco_os():
    df = pd.read_csv(ARQUIVO_OS, dtype=str)
    if "ID" in df.columns:
        df["ID"] = pd.to_numeric(df["ID"], errors="coerce").fillna(0).astype(int)
    return df

# Função para envio de E-mail nativo via Biblioteca Python (smtplib)
def enviar_email_python(destinatario, assunto, corpo, anexos=[]):
    df_cfg = pd.read_csv(ARQUIVO_CONFIG_EMAIL, dtype=str)
    if df_cfg.empty:
        return False, "Configurações de e-mail não encontradas."
    
    cfg = df_cfg.iloc[0]
    remetente = str(cfg.get("Email_Remetente", ""))
    senha = str(cfg.get("API_Key", ""))
    smtp_server = str(cfg.get("Servidor_SMTP", "smtp.gmail.com"))
    porta = int(cfg.get("Porta_SMTP", 587))
    
    if not remetente or not senha:
        return False, "Remetente ou Chave API/Senha não configurados no painel!"

    try:
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain'))

        for arq in anexos:
            if pd.notna(arq) and str(arq).strip() not in ["None", ""] and os.path.exists(str(arq)):
                part = MIMEBase('application', 'octet-stream')
                with open(str(arq), 'rb') as f:
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(str(arq))}"')
                msg.attach(part)

        server = smtplib.SMTP(smtp_server, porta)
        server.starttls()
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()
        return True, "E-mail enviado com sucesso via Python!"
    except Exception as e:
        return False, f"Falha no disparo do e-mail: {str(e)}"

# Função auxiliar simplificada para exibição/download de documentos
def exibir_documento(caminho_arquivo, titulo):
    if pd.isna(caminho_arquivo) or str(caminho_arquivo).strip() in ["None", ""]:
        st.warning(f"📄 **{titulo}:** Não anexado.")
        return
    if not os.path.exists(str(caminho_arquivo)):
        st.error(f"⚠️ **{titulo}:** Arquivo não encontrado.")
        return
    
    ext = os.path.splitext(str(caminho_arquivo))[1].lower()
    st.markdown(f"**📄 {titulo}**")
    
    with open(str(caminho_arquivo), "rb") as file_data:
        data_bytes = file_data.read()
        
    st.download_button(
        label=f"📥 Abrir/Baixar {titulo}",
        data=data_bytes,
        file_name=os.path.basename(str(caminho_arquivo)),
        mime="application/pdf" if ext == ".pdf" else f"image/{ext.replace('.','')}",
        use_container_width=True
    )

    if ext in [".png", ".jpg", ".jpeg"]:
        st.image(data_bytes, use_container_width=True)
    elif ext == ".pdf":
        st.caption("🔍 Pré-visualização do PDF liberada para visualização direta via botão de abertura acima.")

# --- TELA DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = ""

if not st.session_state.autenticado:
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=220)
        st.markdown("<h3 style='text-align: center;'>🔐 Intranet Stang</h3>", unsafe_allow_html=True)
        
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
                    if (senha_input == row["Senha"]) or (is_admin_db and senha_input in ["stang2026", "master"]):
                        st.session_state.autenticado = True
                        st.session_state.usuario = row["Usuario"]
                        st.rerun()
                    else:
                        st.error("Senha incorreta!")
                        
        with st.expander("🔑 Gestão de Usuários / Assinatura Digital PNG"):
            senha_master_input = st.text_input("Senha Master/Admin", type="password", key="master_unlock")
            df_u_check = pd.read_csv(ARQUIVO_USERS, dtype=str)
            admins_senhas = df_u_check[df_u_check["Admin"] == "Sim"]["Senha"].tolist()
            
            if (senha_master_input == "master") or (senha_master_input in admins_senhas and senha_master_input != ""):
                aba_ges1, aba_ges2 = st.tabs(["➕ Novo Usuário", "✏️ Assinatura PNG / Usuários"])
                
                with aba_ges1:
                    with st.form("form_cad_u"):
                        n_login = st.text_input("Login").strip()
                        n_senha = st.text_input("Senha", type="password")
                        n_email = st.text_input("E-mail", value="")
                        n_admin = st.selectbox("Admin", ["Não", "Sim"])
                        n_perm = st.multiselect("Permissões", TODOS_MENUS, default=["📝 Nova O.S.", "🛒 Solicitações de Compras"])
                        if st.form_submit_button("Cadastrar"):
                            if n_login and n_senha:
                                df_u_new = pd.concat([df_u_check, pd.DataFrame([{
                                    "Usuario": n_login, "Senha": n_senha, "Validade": "Vitalício",
                                    "Permissoes": ",".join(n_perm), "Admin": n_admin,
                                    "Assinatura_PNG": "None", "Email_Usuario": n_email
                                }])], ignore_index=True)
                                df_u_new.to_csv(ARQUIVO_USERS, index=False)
                                st.success("Usuário Cadastrado!")
                                st.rerun()

                with aba_ges2:
                    st.dataframe(df_u_check[["Usuario", "Email_Usuario", "Admin", "Assinatura_PNG"]], use_container_width=True)
                    user_sel = st.selectbox("Selecione para vincular Assinatura PNG", df_u_check["Usuario"].tolist())
                    row_u_edit = df_u_check[df_u_check["Usuario"] == user_sel].iloc[0]
                    
                    with st.form("form_edit_u"):
                        st.markdown(f"**Vincular Assinatura Digital PNG para: {user_sel}**")
                        path_ass_atual = str(row_u_edit.get("Assinatura_PNG", "None"))
                        if path_ass_atual != "None" and os.path.exists(path_ass_atual):
                            st.image(path_ass_atual, caption="Assinatura Atual PNG", width=160)
                            
                        up_ass_png = st.file_uploader("Upload Assinatura PNG (Fundo Transparente)", type=["png"])
                        
                        if st.form_submit_button("💾 Salvar Assinatura"):
                            if up_ass_png is not None:
                                file_ass_name = f"assinatura_{user_sel.lower()}.png"
                                path_salvo = os.path.join("uploads_assinaturas", file_ass_name)
                                with open(path_salvo, "wb") as f:
                                    f.write(up_ass_png.getbuffer())
                                df_u_check.loc[df_u_check["Usuario"] == user_sel, "Assinatura_PNG"] = path_salvo
                                df_u_check.to_csv(ARQUIVO_USERS, index=False)
                                st.success("Assinatura PNG vinculada com sucesso!")
                                st.rerun()
    st.stop()

# Menus e Perfil Logado
df_u_check = pd.read_csv(ARQUIVO_USERS, dtype=str)
user_logado_row = df_u_check[df_u_check["Usuario"].str.lower() == st.session_state.usuario.lower()]
is_user_admin = not user_logado_row.empty and str(user_logado_row.iloc[0].get("Admin", "Não")) == "Sim"

if not user_logado_row.empty and pd.notna(user_logado_row.iloc[0].get("Permissoes")):
    menus_disponiveis = [m.strip() for m in str(user_logado_row.iloc[0]["Permissoes"]).split(",") if m.strip() in TODOS_MENUS]
else:
    menus_disponiveis = TODOS_MENUS

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.caption(f"👤 **{st.session_state.usuario}** ({'Admin' if is_user_admin else 'Usuário'})")
    menu = st.radio("Menu Principal", menus_disponiveis) if menus_disponiveis else None
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

if menu is not None:
    # --- TELA 1: CRIAR NOVA O.S. ---
    if menu == "📝 Nova O.S.":
        st.markdown("### 📝 Nova Ordem de Serviço")
        with st.form("form_nova_os", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            solicitante = c1.text_input("Solicitante *")
            setor = c1.selectbox("Setor", ["OPERAÇÃO", "MANUTENÇÃO", "PORTARIA", "ADMINISTRATIVO", "TI"])
            equipamento = c2.text_input("Equipamento / Local")
            tipo = c2.selectbox("Tipo", ["CORRETIVA", "PREVENTIVA", "PREDITIVA"])
            prioridade = c3.selectbox("Prioridade", ["BAIXA", "MÉDIA", "ALTA", "URGENTE"])
            status = c3.selectbox("Status", ["Em Aberto", "Em Andamento", "Finalizada"])
            descricao = st.text_area("Descrição do Problema *")
            
            if st.form_submit_button("💾 Salvar O.S."):
                if solicitante and descricao:
                    df = carregar_banco_os()
                    novo_id = int(df["ID"].max() + 1) if not df.empty and df["ID"].max() > 0 else 1330
                    nova_linha = {
                        "ID": str(novo_id), "Data_Criacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Solicitante": solicitante.upper(), "Setor": setor.upper(),
                        "Equipamento": equipamento.upper() if equipamento else "NÃO INFORMADO",
                        "Tipo_Manutencao": tipo.upper(), "Prioridade": prioridade.upper(),
                        "Descricao": descricao.upper(), "Solucao": "ATENDIDO E FINALIZADO" if status == "Finalizada" else "EM ANDAMENTO",
                        "Itens_Trocados": "NENHUM", "finalizado_por": st.session_state.usuario.upper() if status == "Finalizada" else "",
                        "Data_Termino": datetime.now().strftime("%d/%m/%Y") if status == "Finalizada" else "",
                        "Status": status
                    }
                    pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True).to_csv(ARQUIVO_OS, index=False)
                    st.success(f"O.S. #{novo_id} gerada!")
                    st.rerun()

        st.dataframe(carregar_banco_os().sort_values(by="ID", ascending=False), use_container_width=True)

    # --- TELA 2: GERENCIAR O.S. ---
    elif menu == "📋 Gerenciar O.S.":
        st.markdown("### 📋 Painel de Gestão de O.S.")
        df = carregar_banco_os()
        if not df.empty:
            st.dataframe(df.sort_values(by="ID", ascending=False), use_container_width=True)
            os_id = st.selectbox("Selecione ID da O.S. para Editar/Finalizar", df["ID"].tolist())
            row_edit = df[df["ID"] == os_id].iloc[0]
            
            with st.form("form_edit_os"):
                e_status = st.selectbox("Status", ["Em Aberto", "Em Andamento", "Finalizada"], index=["Em Aberto", "Em Andamento", "Finalizada"].index(row_edit["Status"]))
                e_solucao = st.text_area("Solução Aplicada", value=str(row_edit["Solucao"]))
                e_itens = st.text_area("Peças Trocadas", value=str(row_edit["Itens_Trocados"]))
                
                if st.form_submit_button("💾 Salvar Alterações"):
                    df.loc[df["ID"] == os_id, "Status"] = e_status
                    df.loc[df["ID"] == os_id, "Solucao"] = e_solucao.upper()
                    df.loc[df["ID"] == os_id, "Itens_Trocados"] = e_itens.upper()
                    if e_status == "Finalizada":
                        df.loc[df["ID"] == os_id, "Data_Termino"] = datetime.now().strftime("%d/%m/%Y")
                        df.loc[df["ID"] == os_id, "finalizado_por"] = st.session_state.usuario.upper()
                    df.to_csv(ARQUIVO_OS, index=False)
                    st.success("O.S. Atualizada!")
                    st.rerun()

    # --- TELA 3: IMPRIMIR O.S. ---
    elif menu == "🖨️ Imprimir O.S.":
        st.markdown("### 🖨️ Impressão de O.S.")
        df = carregar_banco_os()
        if not df.empty:
            os_sel = st.selectbox("Selecione O.S.:", df["ID"].astype(str) + " - " + df["Solicitante"])
            id_os = int(os_sel.split(" - ")[0])
            row_os = df[df["ID"] == id_os].iloc[0]
            
            st.info(f"O.S. #{row_os['ID']} - Solicitante: {row_os['Solicitante']} | Status: {row_os['Status']}")
            st.write(f"**Descrição:** {row_os['Descricao']}")
            st.write(f"**Solução:** {row_os['Solucao']}")

    # --- TELA 4: FORMULÁRIOS E PRAZOS (FMS) ---
    elif menu == "📅 Formulários e Prazos (FMs)":
        st.markdown("### 📅 Gestão de Conformidade de FMs")
        df_fms = pd.read_csv(ARQUIVO_FMS, dtype=str)
        st.dataframe(df_fms, use_container_width=True)

    # --- TELA 5: SOLICITAÇÕES DE COMPRAS ---
    elif menu == "🛒 Solicitações de Compras":
        st.markdown("### 🛒 Solicitações de Compras e Insumos")
        
        if "carrinho_compras" not in st.session_state:
            st.session_state.carrinho_compras = []

        abas = ["📋 Pedidos / Visualizar", "📝 Nova Solicitação"]
        if is_user_admin: abas.append("✍️ Assinaturas & E-mail (Admin)")
        
        guias = st.tabs(abas)

        with guias[0]:
            df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
            if not df_c.empty:
                st.dataframe(df_c[["ID_Compra", "Data_Solicitacao", "Solicitante", "Item", "Quantidade", "Status", "Assinado_Por"]], use_container_width=True)

        with guias[1]:
            with st.form("form_add_item"):
                c1, c2, c3 = st.columns([2, 1, 1])
                item_i = c1.text_input("Item")
                cat_i = c2.selectbox("Categoria", ["Escritório", "Operacional", "Limpeza"])
                qtd_i = c3.number_input("Qtd", min_value=1, value=1)
                if st.form_submit_button("➕ Adicionar Item"):
                    if item_i:
                        st.session_state.carrinho_compras.append({"Item": item_i.upper(), "Categoria": cat_i, "Quantidade": int(qtd_i)})
                        st.success("Item adicionado ao carrinho!")

            if st.session_state.carrinho_compras:
                st.dataframe(pd.DataFrame(st.session_state.carrinho_compras), use_container_width=True)
                with st.form("form_salvar_compra"):
                    solic_c = st.text_input("Solicitante *")
                    setor_c = st.selectbox("Setor", ["OPERAÇÃO", "MANUTENÇÃO", "PORTARIA", "ADMINISTRATIVO"])
                    if st.form_submit_button("💾 Finalizar Pedido de Compra"):
                        if solic_c:
                            df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
                            novo_id = int(pd.to_numeric(df_c["ID_Compra"], errors="coerce").fillna(500).max() + 1) if not df_c.empty else 501
                            novos = []
                            for it in st.session_state.carrinho_compras:
                                novos.append({
                                    "ID_Compra": str(novo_id), "Data_Solicitacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    "Solicitante": solic_c.upper(), "Setor": setor_c, "Categoria": it["Categoria"],
                                    "Item": it["Item"], "Quantidade": str(it["Quantidade"]), "Observacoes": "",
                                    "Status": "Compra em Aberta", "Orcamento_Assinado": "None", "NF_Anexada": "None",
                                    "Boleto_Anexado": "None", "Assinado_Por": "None", "Posicao_Assinatura": "No final do documento"
                                })
                            pd.concat([df_c, pd.DataFrame(novos)], ignore_index=True).to_csv(ARQUIVO_COMPRAS, index=False)
                            st.session_state.carrinho_compras = []
                            st.success(f"Pedido #{novo_id} registrado!")
                            st.rerun()

        # ABA ADMIN: ASSINATURAS E ENVIO DE E-MAIL NATIVO
        if is_user_admin:
            with guias[2]:
                st.markdown("#### ⚙️ Configurações de Envio de E-mail (API / SMTP)")
                df_cfg_e = pd.read_csv(ARQUIVO_CONFIG_EMAIL, dtype=str)
                row_cfg = df_cfg_e.iloc[0] if not df_cfg_e.empty else {}
                
                with st.form("form_cfg_mail"):
                    c_e1, c_e2 = st.columns(2)
                    rem_email = c_e1.text_input("E-mail Remetente", value=str(row_cfg.get("Email_Remetente", "")))
                    rem_senha = c_e2.text_input("Senha App / Chave API", value=str(row_cfg.get("API_Key", "")), type="password")
                    smtp_host = c_e1.text_input("Servidor SMTP Host", value=str(row_cfg.get("Servidor_SMTP", "smtp.gmail.com")))
                    smtp_port = c_e2.text_input("Porta SMTP", value=str(row_cfg.get("Porta_SMTP", "587")))
                    if st.form_submit_button("💾 Salvar Configurações de E-mail"):
                        pd.DataFrame([{
                            "Email_Remetente": rem_email, "Nome_Remetente": "Intranet Stang",
                            "API_Key": rem_senha, "Servidor_SMTP": smtp_host, "Porta_SMTP": smtp_port
                        }]).to_csv(ARQUIVO_CONFIG_EMAIL, index=False)
                        st.success("Configurações salvas!")

                st.markdown("---")
                st.markdown("#### ✍️ Painel de Assinatura Digital PNG e Uploads")
                
                df_c_ass = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
                if not df_c_ass.empty:
                    ids_pedidos = sorted(df_c_ass["ID_Compra"].unique().tolist(), reverse=True)
                    id_sel = st.selectbox("Selecione o Número do Pedido de Compra:", ids_pedidos)
                    row_pedido = df_c_ass[df_c_ass["ID_Compra"] == str(id_sel)].iloc[0]
                    
                    st.write(f"**Assinado por:** {row_pedido.get('Assinado_Por', 'Pendente')}")
                    
                    c_up1, c_up2 = st.columns(2)
                    with c_up1:
                        with st.form("form_anexos_docs"):
                            up_orc = st.file_uploader("Upload Orçamento", type=["pdf", "png", "jpg"])
                            up_nf = st.file_uploader("Upload Nota Fiscal (NF)", type=["pdf", "png", "jpg"])
                            up_bol = st.file_uploader("Upload Boleto", type=["pdf", "png", "jpg"])
                            
                            if st.form_submit_button("💾 Salvar Documentos Anexados"):
                                if up_orc:
                                    p = os.path.join("uploads_orcamentos", f"orc_{id_sel}_{up_orc.name}")
                                    with open(p, "wb") as f: f.write(up_orc.getbuffer())
                                    df_c_ass.loc[df_c_ass["ID_Compra"] == str(id_sel), "Orcamento_Assinado"] = p
                                if up_nf:
                                    p = os.path.join("uploads_orcamentos", f"nf_{id_sel}_{up_nf.name}")
                                    with open(p, "wb") as f: f.write(up_nf.getbuffer())
                                    df_c_ass.loc[df_c_ass["ID_Compra"] == str(id_sel), "NF_Anexada"] = p
                                if up_bol:
                                    p = os.path.join("uploads_orcamentos", f"bol_{id_sel}_{up_bol.name}")
                                    with open(p, "wb") as f: f.write(up_bol.getbuffer())
                                    df_c_ass.loc[df_c_ass["ID_Compra"] == str(id_sel), "Boleto_Anexado"] = p
                                df_c_ass.to_csv(ARQUIVO_COMPRAS, index=False)
                                st.success("Documentos Atualizados!")
                                st.rerun()

                    with c_up2:
                        posicao_ass = st.selectbox(
                            "Assinatura no PDF (Posicionamento):", 
                            ["No final do documento", "Cabeçalho (Início)", "Rodapé (Todas as páginas)"]
                        )
                        
                        df_u_check = pd.read_csv(ARQUIVO_USERS, dtype=str)
                        row_u_cur = df_u_check[df_u_check["Usuario"].str.lower() == st.session_state.usuario.lower()].iloc[0]
                        path_ass_png = str(row_u_cur.get("Assinatura_PNG", "None"))
                        
                        if path_ass_png != "None" and os.path.exists(path_ass_png):
                            st.image(path_ass_png, caption=f"Assinatura PNG Vinculada ao Login: {st.session_state.usuario}", width=180)
                        else:
                            st.warning("⚠️ Você não possui uma assinatura PNG vinculada ao seu usuário no cadastro!")

                        if st.button("✍️ Assinar Digitalmente Pedido", use_container_width=True):
                            df_c_ass.loc[df_c_ass["ID_Compra"] == str(id_sel), "Assinado_Por"] = st.session_state.usuario
                            df_c_ass.loc[df_c_ass["ID_Compra"] == str(id_sel), "Posicao_Assinatura"] = posicao_ass
                            df_c_ass.to_csv(ARQUIVO_COMPRAS, index=False)
                            st.success(f"Documento assinado por {st.session_state.usuario} ({posicao_ass})!")
                            st.rerun()

                    st.markdown("---")
                    st.markdown("#### 📧 Envio Direct por E-mail (Biblioteca Python `smtplib`)")
                    with st.form("form_envio_email_direct"):
                        dest_mail = st.text_input("E-mail do Destinatário")
                        corpo_mail = st.text_area("Mensagem do E-mail", value=f"Segue em anexo a documentação referente ao pedido #{id_sel} assinada digitalmente.")
                        
                        if st.form_submit_button("📧 Disparar E-mail com Anexos"):
                            if not dest_mail:
                                st.error("Informe o e-mail de destino.")
                            else:
                                anexos_envio = [
                                    row_pedido.get("Orcamento_Assinado"),
                                    row_pedido.get("NF_Anexada"),
                                    row_pedido.get("Boleto_Anexado")
                                ]
                                ok, res = enviar_email_python(
                                    destinatario=dest_mail,
                                    assunto=f"Documentos Assinados - Pedido #{id_sel} - Stang",
                                    corpo=corpo_mail,
                                    anexos=anexos_envio
                                )
                                if ok:
                                    st.success(res)
                                else:
                                    st.error(res)

                    st.markdown("---")
                    st.markdown("#### 👁️ Central de Visualização de Arquivos")
                    doc1, doc2, doc3 = st.columns(3)
                    with doc1: exibir_documento(row_pedido.get("Orcamento_Assinado"), "1. Orçamento")
                    with doc2: exibir_documento(row_pedido.get("NF_Anexada"), "2. Nota Fiscal (NF)")
                    with doc3: exibir_documento(row_pedido.get("Boleto_Anexado"), "3. Boleto")

    # --- TELA 6: DASHBOARD ---
    elif menu == "📊 Dashboard":
        st.markdown("### 📊 Dashboard de Indicadores")
        df_os = carregar_banco_os()
        if not df_os.empty:
            st.metric("Total de O.S. Cadastradas", len(df_os))
            fig = px.pie(df_os, names="Status", title="Distribuição por Status O.S.")
            st.plotly_chart(fig, use_container_width=True)
