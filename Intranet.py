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
import io

# Tenta importar bibliotecas para manipulação e carimbo de PDFs
try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    HAS_PDF_LIBS = True
except ImportError:
    HAS_PDF_LIBS = False

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

# --- AUTO-REFRESH / LOOPING A CADA 3 SEGUNDOS ---
components.html("""
    <script>
        setInterval(function(){
            window.location.reload();
        }, 3000);
    </script>
""", height=0)

hide_streamlit_style = """
    <style>
    </style>
    """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Lista completa de menus disponíveis no sistema
TODOS_MENUS = [
    "📝 Nova O.S.", 
    "📋 Gerenciar O.S.", 
    "🖨️ Imprimir O.S.", 
    "📅 Formulários e Prazos (FMs)",
    "🛒 Solicitações de Compras",
    "📊 Dashboard"
]

# --- ESTILIZAÇÃO CSS PROFISSIONAL & SUPORTE A TEMAS (CLARO/ESCURO) ---
background_css = ""
if os.path.exists("capa.png"):
    with open("capa.png", "rb") as img_file:
        encoded_string = base64.b64encode(img_file.read()).decode()
    background_css = f"""
    <style>
        .stApp {{
            background: linear-gradient(rgba(0, 30, 80, 0.85), rgba(0, 15, 40, 0.90)), 
                        url("data:image/png;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        .stTextInput input, .stSelectbox select, .stTextArea textarea {{
            background-color: rgba(255, 255, 255, 0.9) !important;
            color: #000000 !important;
            font-weight: 500;
        }}
        .stDataFrame {{
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 8px;
            padding: 5px;
        }}
        div[data-testid="stMetricValue"] {{
            color: #00ffcc !important;
        }}
        
        /* CORREÇÃO DO MENU LATERAL (RADIO BUTTONS) COM SUPORTE A TEMA */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {{
            gap: 8px;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            background-color: rgba(255, 255, 255, 0.08);
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            width: 100%;
            display: flex;
            align-items: center;
        }}
        [data-testid="stSidebar"] .stRadio label:hover {{
            background-color: rgba(255, 255, 255, 0.2);
        }}

        /* REGRAS PARA IMPRESSÃO LIMPA */
        @media print {{
            body {{
                background: #ffffff !important;
                color: #000000 !important;
            }}
            .stApp {{
                background: #ffffff !important;
            }}
            [data-testid="stSidebar"], header, footer, .stButton, .stSelectbox, .no-print {{
                display: none !important;
            }}
        }}
    </style>
    """
st.markdown(background_css, unsafe_allow_html=True)

# Bancos de Dados locais CSV
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
        
    colunas_compras = [
        "ID_Compra", "Data_Solicitacao", "Solicitante", "Setor", "Categoria", 
        "Item", "Quantidade", "Observacoes", "Status", "Orcamento_Assinado",
        "NF_Anexada", "Boleto_Anexado", "Assinado_Por"
    ]
    if not os.path.exists(ARQUIVO_COMPRAS):
        pd.DataFrame(columns=colunas_compras).to_csv(ARQUIVO_COMPRAS, index=False)
    else:
        df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
        mudou_c = False
        for col in colunas_compras:
            if col not in df_c.columns:
                df_c[col] = "None" if col in ["Orcamento_Assinado", "NF_Anexada", "Boleto_Anexado", "Assinado_Por"] else ""
                mudou_c = True
        if mudou_c:
            df_c.to_csv(ARQUIVO_COMPRAS, index=False)
        
    todos_menus_str = ",".join(TODOS_MENUS)
    colunas_users = ["Usuario", "Senha", "Validade", "Permissoes", "Admin", "Assinatura_PNG", "Email_Usuario"]
    
    if not os.path.exists(ARQUIVO_USERS):
        df_users = pd.DataFrame([{
            "Usuario": "thiagosc",
            "Senha": "stang2026",
            "Validade": "Vitalício",
            "Permissoes": todos_menus_str,
            "Admin": "Sim",
            "Assinatura_PNG": "None",
            "Email_Usuario": "thiagosc@stang.com.br"
        }])
        df_users.to_csv(ARQUIVO_USERS, index=False)
    else:
        df_users = pd.read_csv(ARQUIVO_USERS, dtype=str)
        mudou_u = False
        for col in colunas_users:
            if col not in df_users.columns:
                df_users[col] = "None" if col in ["Assinatura_PNG", "Email_Usuario"] else ""
                mudou_u = True
        if mudou_u:
            df_users.to_csv(ARQUIVO_USERS, index=False)
            
        if "thiagosc" not in df_users["Usuario"].str.lower().values:
            novo_mestre = pd.DataFrame([{
                "Usuario": "thiagosc",
                "Senha": "stang2026",
                "Validade": "Vitalício",
                "Permissoes": todos_menus_str,
                "Admin": "Sim",
                "Assinatura_PNG": "None",
                "Email_Usuario": "thiagosc@stang.com.br"
            }])
            df_users = pd.concat([df_users, novo_mestre], ignore_index=True)
            df_users.to_csv(ARQUIVO_USERS, index=False)

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
    if not os.path.exists(ARQUIVO_OS):
        inicializar_bancos()
    df = pd.read_csv(ARQUIVO_OS, dtype=str)
    if "ID" in df.columns:
        df["ID"] = pd.to_numeric(df["ID"], errors="coerce").fillna(0).astype(int)
    return df

# Função auxiliar para renderizar arquivos (Imagens / PDFs em Base64 para evitar bloqueio Chrome HTTP)
def exibir_documento(caminho_arquivo, titulo):
    if pd.isna(caminho_arquivo) or str(caminho_arquivo).strip() in ["None", ""]:
        st.warning(f"📄 **{titulo}:** Não anexado.")
        return
    if not os.path.exists(str(caminho_arquivo)):
        st.error(f"⚠️ **{titulo}:** Arquivo não encontrado no servidor.")
        return
    
    st.markdown(f"#### 📄 {titulo}")
    ext = os.path.splitext(str(caminho_arquivo))[1].lower()
    
    if ext in [".png", ".jpg", ".jpeg"]:
        st.image(str(caminho_arquivo), caption=titulo, use_container_width=True)
    elif ext == ".pdf":
        with open(str(caminho_arquivo), "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            
            st.download_button(
                label=f"📥 Baixar/Abrir {titulo} (PDF)",
                data=pdf_bytes,
                file_name=os.path.basename(str(caminho_arquivo)),
                mime="application/pdf",
                use_container_width=True
            )
            
            # Renderização de PDF puramente em Base64 Data URI sem protocolos HTTP/Inseguros
            pdf_display = f'''
                <object data="data:application/pdf;base64,{base64_pdf}" type="application/pdf" width="100%" height="450px">
                    <embed src="data:application/pdf;base64,{base64_pdf}" type="application/pdf" width="100%" height="450px"/>
                    <p style="font-size: 12px; color: #666;">Se o seu navegador não exibir o PDF acima automaticamente, <a href="data:application/pdf;base64,{base64_pdf}" download="{os.path.basename(str(caminho_arquivo))}">clique aqui para baixar diretamente em formato seguro Base64</a>.</p>
                </object>
            '''
            st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        with open(str(caminho_arquivo), "rb") as gen_file:
            st.download_button(
                label=f"📥 Baixar {titulo}",
                data=gen_file.read(),
                file_name=os.path.basename(str(caminho_arquivo)),
                use_container_width=True
            )

# --- FUNÇÃO PARA APLICAR A ASSINATURA DIGITAL NO FINAL DO DOCUMENTO ---
def carimbar_assinatura_no_documento(caminho_doc, caminho_assinatura_png, nome_usuario):
    if not os.path.exists(caminho_doc) or not os.path.exists(caminho_assinatura_png):
        return False
    
    ext = os.path.splitext(caminho_doc)[1].lower()
    
    if ext == ".pdf" and HAS_PDF_LIBS:
        try:
            reader = PdfReader(caminho_doc)
            writer = PdfWriter()
            num_pages = len(reader.pages)
            
            # Pega a última página para calcular as dimensões
            ultima_pagina = reader.pages[-1]
            largura = float(ultima_pagina.mediabox.width)
            altura = float(ultima_pagina.mediabox.height)
            
            # Cria um PDF temporário em memória contendo o carimbo da assinatura na parte inferior
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(largura, altura))
            
            # Posição da assinatura (canto inferior direito)
            width_img = 160
            height_img = 60
            x = largura - width_img - 40
            y = 40
            
            can.drawImage(caminho_assinatura_png, x, y, width=width_img, height=height_img, mask='auto', preserveAspectRatio=True)
            can.setFont("Helvetica-Bold", 8)
            can.drawString(x, y - 10, f"Assinado digitalmente por: {nome_usuario}")
            can.drawString(x, y - 20, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            can.save()
            
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            overlay_page = overlay_pdf.pages[0]
            
            for i, page in enumerate(reader.pages):
                if i == num_pages - 1:
                    page.merge_page(overlay_page)
                writer.add_page(page)
                
            temp_path = caminho_doc + ".signed.pdf"
            with open(temp_path, "wb") as f_out:
                writer.write(f_out)
                
            os.replace(temp_path, caminho_doc)
            return True
        except Exception as e:
            st.error(f"Erro ao aplicar carimbo no PDF: {e}")
            return False
            
    elif ext in [".png", ".jpg", ".jpeg"]:
        try:
            doc_img = Image.open(caminho_doc).convert("RGBA")
            ass_img = Image.open(caminho_assinatura_png).convert("RGBA")
            
            # Redimensiona a assinatura para tamanho proporcional ao documento
            ass_width = int(doc_img.width * 0.25)
            w_percent = (ass_width / float(ass_img.width))
            ass_height = int((float(ass_img.height) * float(w_percent)))
            ass_img = ass_img.resize((ass_width, ass_height), Image.Resampling.LANCZOS)
            
            # Posiciona no canto inferior direito
            pos_x = doc_img.width - ass_width - 20
            pos_y = doc_img.height - ass_height - 20
            
            doc_img.paste(ass_img, (pos_x, pos_y), ass_img)
            doc_img.convert("RGB").save(caminho_doc)
            return True
        except Exception as e:
            st.error(f"Erro ao aplicar carimbo na Imagem: {e}")
            return False
            
    return True

# --- FUNÇÃO PARA ENVIO REAL DE E-MAIL VIA SMTP ---
def enviar_email_real(destinatario, assunto, corpo, anexos, config):
    try:
        remetente = config.get("Email_Remetente", "")
        senha_app = config.get("API_Key", "")
        servidor_smtp = config.get("Servidor_SMTP", "smtp.gmail.com")
        porta_smtp = int(config.get("Porta_SMTP", "587"))
        
        if not remetente or not senha_app:
            return False, "E-mail remetente ou Senha/Chave API não configurados nas configurações de E-mail!"
            
        msg = MIMEMultipart()
        msg['From'] = f"{config.get('Nome_Remetente', 'Intranet Stang')} <{remetente}>"
        msg['To'] = destinatario
        msg['Subject'] = assunto
        
        msg.attach(MIMEText(corpo, 'plain'))
        
        for file_path in anexos:
            if file_path and str(file_path) != "None" and os.path.exists(str(file_path)):
                with open(file_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                filename = os.path.basename(file_path)
                part.add_header("Content-Disposition", f"attachment; filename= {filename}")
                msg.attach(part)
                
        server = smtplib.SMTP(servidor_smtp, porta_smtp)
        server.starttls()
        server.login(remetente, senha_app)
        text = msg.as_string()
        server.sendmail(remetente, destinatario, text)
        server.quit()
        
        return True, "E-mail enviado com sucesso!"
    except Exception as e:
        return False, f"Falha no envio de e-mail: {str(e)}"

# --- SISTEMA DE AUTENTICAÇÃO E GERENCIAMENTO NA TELA DE LOGIN ---
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
                            
        with st.expander("🔑 Gerenciar Usuários e Assinatura Digital"):
            senha_master_input = st.text_input("Insira a Senha Master ou Senha de Administrador", type="password", key="master_unlock")
            
            df_users_check_master = pd.read_csv(ARQUIVO_USERS, dtype=str)
            admins_senhas = df_users_check_master[df_users_check_master["Admin"] == "Sim"]["Senha"].tolist()
            
            libera_gestao = (senha_master_input == "master") or (senha_master_input in admins_senhas and senha_master_input != "")
            
            if libera_gestao:
                st.success("Painel de gestão de usuários liberado com sucesso:")
                
                aba_ges1, aba_ges2 = st.tabs(["➕ Cadastrar Novo Usuário", "✏️ Editar / ✍️ Assinatura PNG / 🗑️ Excluir"])
                
                with aba_ges1:
                    with st.form("form_gestao_login"):
                        st.markdown("<b>Novo Usuário a Cadastrar:</b>", unsafe_allow_html=True)
                        n_login = st.text_input("Login do Novo Usuário").strip()
                        n_senha = st.text_input("Senha do Novo Usuário", type="password")
                        n_email = st.text_input("E-mail do Usuário", value="")
                        n_val = st.selectbox("Validade", ["Vitalício", "Definir Data Limite"])
                        
                        n_data = datetime.now().date() + timedelta(days=30)
                        if n_val == "Definir Data Limite":
                            n_data = st.date_input("Data Limite de Acesso")
                            
                        n_admin_opt = st.selectbox("Perfil de Administrador (Acesso total / Gestão)", ["Não", "Sim"])
                            
                        st.markdown("<b>Permissões de Acesso aos Menus:</b>", unsafe_allow_html=True)
                        n_permissoes = st.multiselect(
                            "Selecione as opções que este usuário poderá acessar:",
                            options=TODOS_MENUS,
                            default=["📝 Nova O.S.", "🛒 Solicitações de Compras"]
                        )
                            
                        btn_cad_login = st.form_submit_button("Cadastrar Novo Usuário")
                        
                        if btn_cad_login:
                            if not n_login or not n_senha:
                                st.error("Preencha o login e a senha do novo usuário!")
                            elif not n_permissoes:
                                st.error("Selecione pelo menos uma permissão de menu para o usuário.")
                            else:
                                df_u = pd.read_csv(ARQUIVO_USERS, dtype=str)
                                if n_login.lower() in df_u["Usuario"].str.lower().values:
                                    st.error("Este usuário já existe!")
                                else:
                                    val_str = "Vitalício" if n_val == "Vitalício" else str(n_data)
                                    perm_str = ",".join(n_permissoes)
                                    novo_reg = {
                                        "Usuario": n_login, 
                                        "Senha": n_senha, 
                                        "Validade": val_str,
                                        "Permissoes": perm_str,
                                        "Admin": n_admin_opt,
                                        "Assinatura_PNG": "None",
                                        "Email_Usuario": n_email
                                    }
                                    df_u = pd.concat([df_u, pd.DataFrame([novo_reg])], ignore_index=True)
                                    df_u.to_csv(ARQUIVO_USERS, index=False)
                                    st.success(f"Usuário '{n_login}' cadastrado com sucesso!")
                                    st.rerun()

                with aba_ges2:
                    df_u_atual = pd.read_csv(ARQUIVO_USERS, dtype=str)
                    st.markdown("<b>Usuários Ativos, Permissões e Perfis:</b>", unsafe_allow_html=True)
                    st.dataframe(df_u_atual[["Usuario", "Email_Usuario", "Validade", "Admin", "Assinatura_PNG"]], use_container_width=True)
                    
                    lista_usuarios_edit = df_u_atual["Usuario"].tolist()
                    if lista_usuarios_edit:
                        st.markdown("---")
                        user_selecionado = st.selectbox("Selecione o usuário para Editar / Vincular Assinatura PNG", lista_usuarios_edit)
                        row_u_edit = df_u_atual[df_u_atual["Usuario"] == user_selecionado].iloc[0]
                        
                        with st.form("form_editar_usuario"):
                            st.subheader(f"Editando Usuário: {user_selecionado}")
                            edit_senha = st.text_input("Nova Senha (deixe a atual ou digite nova)", value=str(row_u_edit["Senha"]), type="password")
                            edit_email = st.text_input("E-mail do Usuário", value=str(row_u_edit.get("Email_Usuario", "")))
                            
                            val_atual_str = str(row_u_edit["Validade"])
                            is_vitalicio = val_atual_str == "Vitalício"
                            edit_val_tipo = st.selectbox("Validade", ["Vitalício", "Definir Data Limite"], index=0 if is_vitalicio else 1)
                            
                            edit_data = datetime.now().date() + timedelta(days=30)
                            if not is_vitalicio:
                                try:
                                    edit_data = datetime.strptime(val_atual_str, "%Y-%m-%d").date()
                                except:
                                    pass
                            if edit_val_tipo == "Definir Data Limite":
                                edit_data = st.date_input("Nova Data Limite de Acesso", value=edit_data)
                                
                            admin_atual_str = str(row_u_edit.get("Admin", "Não"))
                            edit_admin_opt = st.selectbox("Perfil de Administrador (Acesso total / Gestão)", ["Não", "Sim"], index=0 if admin_atual_str != "Sim" else 1)
                                
                            perm_atuais_list = [p.strip() for p in str(row_u_edit["Permissoes"]).split(",") if p.strip() in TODOS_MENUS]
                            edit_permissoes = st.multiselect(
                                "Permissões de Acesso aos Menus:",
                                options=TODOS_MENUS,
                                default=perm_atuais_list
                            )
                            
                            st.markdown("---")
                            st.markdown("✍️ **Assinatura Digital em PNG:**")
                            path_ass_atual = str(row_u_edit.get("Assinatura_PNG", "None"))
                            if path_ass_atual != "None" and os.path.exists(path_ass_atual):
                                st.image(path_ass_atual, caption=f"Assinatura Atual de {user_selecionado}", width=200)
                            else:
                                st.caption("Nenhuma assinatura digital em PNG cadastrada para este usuário.")
                                
                            up_assinatura_png = st.file_uploader(f"Upload da Assinatura PNG para {user_selecionado}", type=["png"])
                            
                            btn_salvar_edicao = st.form_submit_button("💾 Salvar Alterações e Vincular Assinatura PNG")
                            
                            if btn_salvar_edicao:
                                if not edit_permissoes:
                                    st.error("Selecione pelo menos uma permissão de menu.")
                                else:
                                    novo_val_str = "Vitalício" if edit_val_tipo == "Vitalício" else str(edit_data)
                                    nova_perm_str = ",".join(edit_permissoes)
                                    
                                    path_salvo = path_ass_atual
                                    if up_assinatura_png is not None:
                                        file_ass_name = f"assinatura_{user_selecionado.lower()}.png"
                                        path_salvo = os.path.join("uploads_assinaturas", file_ass_name)
                                        with open(path_salvo, "wb") as f:
                                            f.write(up_assinatura_png.getbuffer())
                                            
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Senha"] = edit_senha
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Email_Usuario"] = edit_email
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Validade"] = novo_val_str
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Admin"] = edit_admin_opt
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Permissoes"] = nova_perm_str
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Assinatura_PNG"] = path_salvo
                                    
                                    df_u_atual.to_csv(ARQUIVO_USERS, index=False)
                                    st.success(f"Usuário '{user_selecionado}' e Assinatura PNG vinculada com sucesso!")
                                    st.rerun()

                        total_admins = len(df_u_atual[df_u_atual["Admin"] == "Sim"])
                        is_este_admin = str(row_u_edit.get("Admin")) == "Sim"
                        
                        if total_admins <= 1 and is_este_admin:
                            st.info("⚠️ Este é o único usuário administrador ativo e não pode ser excluído.")
                        else:
                            if st.button(f"🗑️ Excluir Definitivamente o Usuário '{user_selecionado}'", type="primary"):
                                df_u_atual = df_u_atual[df_u_atual["Usuario"] != user_selecionado]
                                df_u_atual.to_csv(ARQUIVO_USERS, index=False)
                                st.success(f"Usuário '{user_selecionado}' removido com sucesso!")
                                st.rerun()
            elif senha_master_input != "":
                st.error("Senha Master ou Administrador incorreta.")
                    
    st.stop()

# --- DETERMINAR MENUS PERMITIDOS PARA O USUÁRIO LOGADO ---
df_users_check = pd.read_csv(ARQUIVO_USERS, dtype=str)
user_logado_row = df_users_check[df_users_check["Usuario"].str.lower() == st.session_state.usuario.lower()]

is_user_admin = False
if not user_logado_row.empty:
    is_user_admin = str(user_logado_row.iloc[0].get("Admin", "Não")) == "Sim"

if not user_logado_row.empty and pd.notna(user_logado_row.iloc[0].get("Permissoes")) and str(user_logado_row.iloc[0]["Permissoes"]) != "":
    menus_disponiveis = [m.strip() for m in str(user_logado_row.iloc[0]["Permissoes"]).split(",") if m.strip() in TODOS_MENUS]
else:
    menus_disponiveis = TODOS_MENUS

# --- BARRA LATERAL (MENU) COM LOGO STANG ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.markdown("---")
    cargo_str = "Administrador 🔑" if is_user_admin else "Usuário 👤"
    st.markdown(f"👤 Logado como: **{st.session_state.usuario}**<br>🛡️ Perfil: *{cargo_str}*", unsafe_allow_html=True)
    
    if menus_disponiveis:
        menu = st.radio("Navegação Principal", menus_disponiveis)
    else:
        st.warning("⚠️ Você não possui permissão para acessar nenhum menu. Contate o administrador.")
        menu = None
    
    st.markdown("---")
    
    if st.button("🔄 Atualizar Dados da Tela", use_container_width=True):
        st.rerun()
        
    if st.button("🚪 Sair / Logout", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario = ""
        st.rerun()
    st.info("🏢 Intranet Base Stang - Itajaí SC\nStatus: Conectado 🟢")
    
    st.markdown("<div style='text-align: left; font-style: italic; font-size: 11px; opacity: 0.7; margin-top: 25px;'><i>By: TS tech</i></div>", unsafe_allow_html=True)

if menu is not None:
    # --- TELA 1: CRIAR NOVA O.S. ---
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
            
            submit = st.form_submit_button("💾 Salvar Ordem de Serviço")
            
            if submit:
                if not solicitante or not descricao:
                    st.error("Por favor, preencha o Solicitante e a Descrição do Problema.")
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
                    st.success(f"Ordem de Serviço #{novo_id} gerada com sucesso no sistema Stang!")
                    st.rerun()

        df_os_view = carregar_banco_os()
        if df_os_view.empty:
            st.info("Nenhuma Ordem de Serviço registrada até o momento.")
        else:
            dias_prioridade_map = {"URGENTE": 1, "ALTA": 5, "MÉDIA": 15, "MEDIA": 15, "BAIXA": 30}
            
            def calcular_vencimento_os_view(row):
                try:
                    prio = str(row['Prioridade']).upper()
                    dias = dias_prioridade_map.get(prio, 30)
                    dt_criacao = pd.to_datetime(str(row['Data_Criacao']).split(" ")[0], format='%d/%m/%Y', errors='coerce')
                    if pd.isna(dt_criacao):
                        dt_criacao = pd.to_datetime(str(row['Data_Criacao']), errors='coerce')
                    if pd.isna(dt_criacao):
                        return datetime.now().date()
                    return (dt_criacao + timedelta(days=dias)).date()
                except:
                    return datetime.now().date()

            def determinar_status_prazo_view(row):
                status_atual = str(row['Status']).lower()
                if "finalizada" in status_atual or "concluída" in status_atual:
                    return "Finalizada 🔵"
                venc = row['Prazo_Limite']
                hoje = datetime.now().date()
                if hoje > venc:
                    return "Vencida 🔴"
                else:
                    return "No Prazo 🟢"

            df_os_view['Prazo_Limite'] = df_os_view.apply(calcular_vencimento_os_view, axis=1)
            df_os_view['Status_Prazo'] = df_os_view.apply(determinar_status_prazo_view, axis=1)

            cols_exibicao = ["ID", "Data_Criacao", "Solicitante", "Setor", "Prioridade", "Prazo_Limite", "Status_Prazo", "Status", "Equipamento", "Descricao", "finalizado_por"]
            st.dataframe(df_os_view[cols_exibicao].sort_values(by="ID", ascending=False), use_container_width=True)

    # --- TELA 2: GERENCIAR, EDITAR, FINALIZAR E EXCLUIR O.S. ---
    elif menu == "📋 Gerenciar O.S.":
        st.markdown("# 📋 Painel de Controle e Gestão de O.S.")
        df = carregar_banco_os()
        
        if df.empty:
            st.info("Nenhuma O.S. registrada no momento.")
        else:
            dias_prioridade_map = {"URGENTE": 1, "ALTA": 5, "MÉDIA": 15, "MEDIA": 15, "BAIXA": 30}
            
            def calcular_vencimento_os(row):
                try:
                    prio = str(row['Prioridade']).upper()
                    dias = dias_prioridade_map.get(prio, 30)
                    dt_criacao = pd.to_datetime(str(row['Data_Criacao']).split(" ")[0], format='%d/%m/%Y', errors='coerce')
                    if pd.isna(dt_criacao):
                        dt_criacao = pd.to_datetime(str(row['Data_Criacao']), errors='coerce')
                    if pd.isna(dt_criacao):
                        return datetime.now().date()
                    return (dt_criacao + timedelta(days=dias)).date()
                except:
                    return datetime.now().date()

            def determinar_status_prazo(row):
                status_atual = str(row['Status']).lower()
                if "finalizada" in status_atual or "concluída" in status_atual:
                    return "Finalizada 🔵"
                venc = row['Prazo_Limite']
                hoje = datetime.now().date()
                if hoje > venc:
                    return "Vencida 🔴"
                else:
                    return "No Prazo 🟢"

            df['Prazo_Limite'] = df.apply(calcular_vencimento_os, axis=1)
            df['Status_Prazo'] = df.apply(determinar_status_prazo, axis=1)

            c1, c2, c3 = st.columns(3)
            with c1:
                filtro_status = st.selectbox("Filtrar por Status", ["Todos"] + list(df["Status"].unique()))
            with c2:
                filtro_setor = st.selectbox("Filtrar por Setor", ["Todos"] + list(df["Setor"].unique()))
            with c3:
                lista_finalizado_por_opts = ["Todos"] + sorted([x for x in df["finalizado_por"].dropna().unique().tolist() if str(x).strip() != ""])
                filtro_finalizador = st.selectbox("Filtrar por Quem Efetuou o Serviço", lista_finalizado_por_opts)
                
            df_filtered = df.copy()
            if filtro_status != "Todos":
                df_filtered = df_filtered[df_filtered["Status"] == filtro_status]
            if filtro_setor != "Todos":
                df_filtered = df_filtered[df_filtered["Setor"] == filtro_setor]
            if filtro_finalizador != "Todos":
                df_filtered = df_filtered[df_filtered["finalizado_por"] == filtro_finalizador]
                
            cols_exibicao = ["ID", "Data_Criacao", "Solicitante", "Setor", "Prioridade", "Prazo_Limite", "Status_Prazo", "Status", "Equipamento", "Solucao", "Itens_Trocados", "finalizado_por"]
            st.dataframe(df_filtered[cols_exibicao].sort_values(by="ID", ascending=False), use_container_width=True)
            
            st.markdown("---")
            
            aba_os_ges1, aba_os_ges2 = st.tabs(["✏️ Editar / Finalizar O.S.", "🗑️ Excluir O.S."])
            
            with aba_os_ges1:
                ids_os_lista = sorted(df["ID"].tolist(), reverse=True)
                if ids_os_lista:
                    os_selecionada_id = st.selectbox("Selecione o ID da O.S. para Editar ou Finalizar", ids_os_lista)
                    row_edit_os = df[df["ID"] == os_selecionada_id].iloc[0]
                    
                    with st.form("form_editar_os_detalhes"):
                        st.subheader(f"Editando Ordem de Serviço #{os_selecionada_id}")
                        
                        col_e1, col_e2, col_e3 = st.columns(3)
                        with col_e1:
                            edit_solicitante = st.text_input("Solicitante", value=str(row_edit_os["Solicitante"]))
                            edit_setor = st.text_input("Setor", value=str(row_edit_os["Setor"]))
                        with col_e2:
                            edit_equip = st.text_input("Equipamento", value=str(row_edit_os["Equipamento"]))
                            
                            prio_atual = str(row_edit_os["Prioridade"]).upper()
                            idx_prio = ["BAIXA", "MÉDIA", "ALTA", "URGENTE"].index(prio_atual) if prio_atual in ["BAIXA", "MÉDIA", "ALTA", "URGENTE"] else 0
                            edit_prio = st.selectbox("Prioridade (Urgente:1d, Alta:5d, Média:15d, Baixa:30d)", ["BAIXA", "MÉDIA", "ALTA", "URGENTE"], index=idx_prio)
                        with col_e3:
                            status_atual_str = str(row_edit_os["Status"])
                            status_opcoes = ["Em Aberto", "Em Andamento", "Finalizada"]
                            idx_st = status_opcoes.index(status_atual_str) if status_atual_str in status_opcoes else 0
                            edit_status = st.selectbox("Status", status_opcoes, index=idx_st)
                            
                            finalizado_por_ant = str(row_edit_os["finalizado_por"]) if pd.notna(row_edit_os["finalizado_por"]) and str(row_edit_os["finalizado_por"]).strip() != "" else st.session_state.usuario.upper()
                            edit_finalizado_por = st.text_input("Quem efetuou o serviço (Responsável)", value=finalizado_por_ant)

                        edit_desc = st.text_area("Descrição do Problema", value=str(row_edit_os["Descricao"]))
                        
                        col_e4, col_e5 = st.columns(2)
                        with col_e4:
                            sol_ant = str(row_edit_os["Solucao"]) if pd.notna(row_edit_os["Solucao"]) else ""
                            edit_solucao = st.text_area("Solução Aplicada", value=sol_ant)
                        with col_e5:
                            itens_ant = str(row_edit_os["Itens_Trocados"]) if pd.notna(row_edit_os["Itens_Trocados"]) else ""
                            edit_itens = st.text_area("Itens / Peças Trocadas", value=itens_ant)
                            
                        col_b_f1, col_b_f2 = st.columns(2)
                        with col_b_f1:
                            btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações da O.S.")
                        with col_b_f2:
                            btn_finalizar_direto = st.form_submit_button("✅ Finalizar O.S. Imediatamente")
                            
                        if btn_salvar_alt:
                            df.loc[df["ID"] == os_selecionada_id, "Solicitante"] = edit_solicitante.upper()
                            df.loc[df["ID"] == os_selecionada_id, "Setor"] = edit_setor.upper()
                            df.loc[df["ID"] == os_selecionada_id, "Equipamento"] = edit_equip.upper()
                            df.loc[df["ID"] == os_selecionada_id, "Prioridade"] = edit_prio.upper()
                            df.loc[df["ID"] == os_selecionada_id, "Status"] = edit_status
                            df.loc[df["ID"] == os_selecionada_id, "Descricao"] = edit_desc.upper()
                            df.loc[df["ID"] == os_selecionada_id, "Solucao"] = edit_solucao.upper()
                            df.loc[df["ID"] == os_selecionada_id, "Itens_Trocados"] = edit_itens.upper()
                            df.loc[df["ID"] == os_selecionada_id, "finalizado_por"] = edit_finalizado_por.upper()
                            
                            if edit_status == "Finalizada":
                                df.loc[df["ID"] == os_selecionada_id, "Data_Termino"] = datetime.now().strftime("%d/%m/%Y")
                            else:
                                df.loc[df["ID"] == os_selecionada_id, "Data_Termino"] = ""
                            
                            df_to_save = df.drop(columns=["Prazo_Limite", "Status_Prazo"], errors="ignore")
                            df_to_save.to_csv(ARQUIVO_OS, index=False)
                            st.success(f"Ordem de Serviço #{os_selecionada_id} atualizada com sucesso!")
                            st.rerun()
                            
                        if btn_finalizar_direto:
                            df.loc[df["ID"] == os_selecionada_id, "Status"] = "Finalizada"
                            df.loc[df["ID"] == os_selecionada_id, "Data_Termino"] = datetime.now().strftime("%d/%m/%Y")
                            df.loc[df["ID"] == os_selecionada_id, "finalizado_por"] = edit_finalizado_por.upper()
                            if str(df.loc[df["ID"] == os_selecionada_id, "Solucao"].values[0]) in ["", "EM ANDAMENTO", "nan"]:
                                df.loc[df["ID"] == os_selecionada_id, "Solucao"] = "ATENDIDO E FINALIZADO"
                                
                            df_to_save = df.drop(columns=["Prazo_Limite", "Status_Prazo"], errors="ignore")
                            df_to_save.to_csv(ARQUIVO_OS, index=False)
                            st.success(f"Ordem de Serviço #{os_selecionada_id} finalizada com sucesso!")
                            st.rerun()
            
            with aba_os_ges2:
                col_del1, col_del2 = st.columns([2, 1])
                with col_del1:
                    os_para_excluir = st.selectbox("Selecione o ID da O.S. para Exclusão Definitiva", df["ID"].tolist(), key="select_del_os")
                with col_del2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Excluir O.S. Selecionada", type="primary"):
                        df = df[df["ID"] != os_para_excluir]
                        df_to_save = df.drop(columns=["Prazo_Limite", "Status_Prazo"], errors="ignore")
                        df_to_save.to_csv(ARQUIVO_OS, index=False)
                        st.success(f"Ordem de Serviço #{os_para_excluir} excluída com sucesso!")
                        st.rerun()

    # --- TELA 3: IMPRIMIR O.S. E RELATÓRIO DE O.S. ---
    elif menu == "🖨️ Imprimir O.S.":
        st.markdown("# 🖨️ Emissão e Relatórios de O.S.")
        df = carregar_banco_os()
        
        if df.empty:
            st.warning("Não há O.S. cadastradas para impressão.")
        else:
            tab_imp1, tab_imp2 = st.tabs(["📄 Imprimir O.S.", "📊 Relatório Geral de O.S."])
            
            with tab_imp1:
                lista_os = df["ID"].astype(str) + " - " + df["Solicitante"] + " (" + df["Setor"] + ")"
                os_selecionada = st.selectbox("Selecione a O.S. desejada:", lista_os)
                
                id_selecionado = int(os_selecionada.split(" - ")[0])
                os_row = df[df["ID"] == id_selecionado].iloc[0]
                
                st.markdown("---")
                
                equipamento_val = os_row['Equipamento'] if pd.notna(os_row.get('Equipamento')) else 'N/A'
                solucao_val = os_row['Solucao'] if pd.notna(os_row.get('Solucao')) else ''
                itens_val = os_row['Itens_Trocados'] if pd.notna(os_row.get('Itens_Trocados')) else ''
                finalizador_val = os_row['finalizado_por'] if pd.notna(os_row.get('finalizado_por')) else ''
                data_criacao_val = str(os_row['Data_Criacao'])
                
                logo_base64 = ""
                if os.path.exists("logo.png"):
                    with open("logo.png", "rb") as img_file:
                        logo_base64 = base64.b64encode(img_file.read()).decode()
                
                print_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ background-color: #ffffff; color: #000000; margin: 0; padding: 10px; font-family: Arial, sans-serif; }}
        .print-btn-container {{ text-align: center; margin-bottom: 20px; }}
        .btn-imprimir {{ background-color: #007bff; color: white; border: none; padding: 12px 25px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; }}
        @media print {{ .print-btn-container {{ display: none !important; }} body {{ padding: 0; }} }}
    </style>
</head>
<body>
    <div class="print-btn-container">
        <button class="btn-imprimir" onclick="window.print()">🖨️ Clique Aqui para Imprimir Apenas esta O.S.</button>
    </div>
    <div style="background-color: #ffffff; color: #000000; padding: 20px; border: 2px solid #000; max-width: 800px; margin: auto;">
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000;">
            <tr>
                <td style="width: 28%; border: 1px solid #000; padding: 5px; text-align: center; vertical-align: middle;">
                    <img src="data:image/png;base64,{logo_base64}" style="max-height: 45px; max-width: 100%;">
                </td>
                <td style="width: 44%; border: 1px solid #000; text-align: center; vertical-align: middle;">
                    <h3 style="margin: 0; color: #000 !important; font-size: 15px;">Solicitação de Manutenção - Ordem de Serviço</h3>
                </td>
                <td style="width: 28%; border: 1px solid #000; padding: 5px; font-size: 11px; text-align: right; color: #000 !important; vertical-align: middle;">
                    <b>FM 12</b><br>Revisão: 02/2024
                </td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; color: #000 !important;">
            <tr>
                <td style="border: 1px solid #000; padding: 5px; width: 33%;"><b>Número:</b> {os_row['ID']}</td>
                <td style="border: 1px solid #000; padding: 5px; width: 34%;"><b>Data:</b> {data_criacao_val.split(' ')[0]}</td>
                <td style="border: 1px solid #000; padding: 5px; width: 33%;"><b>Hora:</b> {data_criacao_val.split(' ')[1] if len(data_criacao_val.split(' ')) > 1 else '17:00'}</td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; text-align: center; color: #000 !important;">
            <tr>
                <td style="border: 1px solid #000; background-color: #e0e0e0; padding: 4px; width: 50%;"><b>Tipo de Manutenção</b></td>
                <td style="border: 1px solid #000; background-color: #e0e0e0; padding: 4px; width: 50%;"><b>Prioridade de Manutenção</b></td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; font-size: 14px; font-weight: bold;">{os_row['Tipo_Manutencao']}</td>
                <td style="border: 1px solid #000; padding: 10px; font-size: 14px; font-weight: bold;">{os_row['Prioridade']}</td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; color: #000 !important;">
            <tr>
                <td style="border: 1px solid #000; padding: 5px; width: 50%;"><b>SETOR:</b> {os_row['Setor']}</td>
                <td style="border: 1px solid #000; padding: 5px; width: 50%;"><b>SOLICITANTE:</b> {os_row['Solicitante']}</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 5px;" colspan="2"><b>Equipamento:</b> {equipamento_val}</td>
            </tr>
        </table>
        <div style="border: 1px solid #000; border-top: none;">
            <div style="background-color: #e0e0e0; text-align: center; font-size: 12px; font-weight: bold; border-bottom: 1px solid #000; padding: 4px; color: #000 !important;">Descrição do Problema</div>
            <div style="padding: 10px; min-height: 70px; font-size: 13px; color: #000 !important;">{os_row['Descricao']}</div>
        </div>
        <div style="border: 1px solid #000; border-top: none;">
            <div style="background-color: #e0e0e0; text-align: center; font-size: 12px; font-weight: bold; border-bottom: 1px solid #000; padding: 4px; color: #000 !important;">Descrição da Solução</div>
            <div style="padding: 10px; min-height: 50px; font-size: 13px; color: #000 !important;">{solucao_val}</div>
        </div>
        <div style="border: 1px solid #000; border-top: none;">
            <div style="background-color: #e0e0e0; text-align: center; font-size: 12px; font-weight: bold; border-bottom: 1px solid #000; padding: 4px; color: #000 !important;">Itens Trocados</div>
            <div style="padding: 10px; min-height: 40px; font-size: 13px; color: #000 !important;">{itens_val}</div>
        </div>
        <table style="width: 100%; margin-top: 35px; font-size: 12px; border-collapse: collapse; color: #000 !important;">
            <tr>
                <td style="text-align: center; width: 50%;">__________________________________________________<br><b>Manutenção</b></td>
                <td style="text-align: center; width: 50%;">__________________________________________________<br><b>Responsável pelo Serviço / Executante ({finalizador_val})</b></td>
            </tr>
        </table>
    </div>
</body>
</html>
"""
                components.html(print_html, height=920, scrolling=True)

            with tab_imp2:
                st.subheader("Filtros para o Relatório de Ordens de Serviço (O.S.)")
                df_rel_os = df.copy()
                df_rel_os['Dt_Parsed'] = pd.to_datetime(df_rel_os['Data_Criacao'], format='%d/%m/%Y %H:%M', errors='coerce')
                if df_rel_os['Dt_Parsed'].isna().all():
                    df_rel_os['Dt_Parsed'] = pd.to_datetime(df_rel_os['Data_Criacao'], errors='coerce')
                
                df_rel_os['Ano'] = df_rel_os['Dt_Parsed'].dt.year
                df_rel_os['Mes_Ano'] = df_rel_os['Dt_Parsed'].dt.strftime('%m/%Y')
                df_rel_os['Dia'] = df_rel_os['Dt_Parsed'].dt.date
                
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                with col_f1:
                    status_opts = ["Todos"] + sorted(df_rel_os['Status'].dropna().unique().tolist())
                    filtro_status_rep = st.selectbox("Status", status_opts, key="rep_status")
                with col_f2:
                    anos_opts = ["Todos"] + sorted([str(int(a)) for a in df_rel_os['Ano'].dropna().unique() if pd.notna(a)])
                    filtro_ano_rep = st.selectbox("Ano", anos_opts, key="rep_ano")
                with col_f3:
                    meses_opts = ["Todos"] + sorted(df_rel_os['Mes_Ano'].dropna().unique().tolist())
                    filtro_mes_rep = st.selectbox("Mês/Ano", meses_opts, key="rep_mes")
                with col_f4:
                    dias_opts = ["Todos"] + sorted(df_rel_os['Dia'].astype(str).dropna().unique().tolist())
                    filtro_dia_rep = st.selectbox("Dia Exato", dias_opts, key="rep_dia")
                
                df_f_rep = df_rel_os.copy()
                if filtro_status_rep != "Todos":
                    df_f_rep = df_f_rep[df_f_rep['Status'] == filtro_status_rep]
                if filtro_ano_rep != "Todos":
                    df_f_rep = df_f_rep[df_f_rep['Ano'].astype(str) == filtro_ano_rep]
                if filtro_mes_rep != "Todos":
                    df_f_rep = df_f_rep[df_f_rep['Mes_Ano'] == filtro_mes_rep]
                if filtro_dia_rep != "Todos":
                    df_f_rep = df_f_rep[df_f_rep['Dia'].astype(str) == filtro_dia_rep]
                
                st.markdown("---")
                st.markdown(f"**Total de O.S. encontradas com os filtros selecionados:** {len(df_f_rep)}")
                
                if df_f_rep.empty:
                    st.warning("Nenhuma Ordem de Serviço encontrada com os filtros informados.")
                else:
                    st.dataframe(df_f_rep[["ID", "Data_Criacao", "Solicitante", "Setor", "Equipamento", "Tipo_Manutencao", "Prioridade", "Status", "Solucao", "finalizado_por"]], use_container_width=True)
                    
                    logo_base64_rep = ""
                    if os.path.exists("logo.png"):
                        with open("logo.png", "rb") as img_file:
                            logo_base64_rep = base64.b64encode(img_file.read()).decode()
                            
                    linhas_os_html = ""
                    for _, row in df_f_rep.sort_values(by="ID", ascending=False).iterrows():
                        linhas_os_html += f"""
                        <tr>
                            <td style="border: 1px solid #000; padding: 6px; text-align: center;"><b>{row['ID']}</b></td>
                            <td style="border: 1px solid #000; padding: 6px; text-align: center;">{row['Data_Criacao']}</td>
                            <td style="border: 1px solid #000; padding: 6px;">{row['Solicitante']} ({row['Setor']})</td>
                            <td style="border: 1px solid #000; padding: 6px;">{row['Equipamento']}</td>
                            <td style="border: 1px solid #000; padding: 6px; text-align: center;">{row['Tipo_Manutencao']}</td>
                            <td style="border: 1px solid #000; padding: 6px; text-align: center;">{row['Prioridade']}</td>
                            <td style="border: 1px solid #000; padding: 6px; text-align: center;"><b>{row['Status']}</b></td>
                            <td style="border: 1px solid #000; padding: 6px;">{row['Solucao']}</td>
                            <td style="border: 1px solid #000; padding: 6px; text-align: center;">{row['finalizado_por']}</td>
                        </tr>
                        """
                        
                    print_rel_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ background-color: #ffffff; color: #000000; margin: 0; padding: 10px; font-family: Arial, sans-serif; }}
        .print-btn-container {{ text-align: center; margin-bottom: 20px; }}
        .btn-imprimir {{ background-color: #28a745; color: white; border: none; padding: 12px 25px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; }}
        @media print {{ .print-btn-container {{ display: none !important; }} body {{ padding: 0; }} }}
    </style>
</head>
<body>
    <div class="print-btn-container">
        <button class="btn-imprimir" onclick="window.print()">🖨️ Imprimir Relatório Filtrado de O.S.</button>
    </div>
    <div style="background-color: #ffffff; color: #000000; padding: 20px; border: 2px solid #000; max-width: 1000px; margin: auto;">
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000;">
            <tr>
                <td style="width: 25%; border: 1px solid #000; padding: 5px; text-align: center; vertical-align: middle;">
                    <img src="data:image/png;base64,{logo_base64_rep}" style="max-height: 45px; max-width: 100%;">
                </td>
                <td style="width: 50%; border: 1px solid #000; text-align: center; vertical-align: middle;">
                    <h3 style="margin: 0; color: #000 !important; font-size: 16px;">Relatório Geral de Ordens de Serviço (O.S.)</h3>
                </td>
                <td style="width: 25%; border: 1px solid #000; padding: 5px; font-size: 11px; text-align: right; color: #000 !important; vertical-align: middle;">
                    <b></b><br>Data: {datetime.now().strftime('%d/%m/%Y')}
                </td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; color: #000 !important; margin-top: 5px;">
            <tr>
                <td style="border: 1px solid #000; padding: 6px;"><b>Filtros Aplicados:</b> Status: {filtro_status_rep} | Ano: {filtro_ano_rep} | Mês/Ano: {filtro_mes_rep} | Dia: {filtro_dia_rep}</td>
                <td style="border: 1px solid #000; padding: 6px; width: 25%; text-align: center;"><b>Total Registros:</b> {len(df_f_rep)}</td>
            </tr>
        </table>
        <div style="margin-top: 15px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 11px; color: #000 !important;">
                <thead>
                    <tr style="background-color: #e0e0e0;">
                        <th style="border: 1px solid #000; padding: 6px;">ID</th>
                        <th style="border: 1px solid #000; padding: 6px;">Data</th>
                        <th style="border: 1px solid #000; padding: 6px;">Solicitante / Setor</th>
                        <th style="border: 1px solid #000; padding: 6px;">Equipamento</th>
                        <th style="border: 1px solid #000; padding: 6px;">Tipo</th>
                        <th style="border: 1px solid #000; padding: 6px;">Prioridade</th>
                        <th style="border: 1px solid #000; padding: 6px;">Status</th>
                        <th style="border: 1px solid #000; padding: 6px;">Solução</th>
                        <th style="border: 1px solid #000; padding: 6px;">Efetuado Por</th>
                    </tr>
                </thead>
                <tbody>
                    {linhas_os_html}
                </tbody>
            </table>
        </div>
        <table style="width: 100%; margin-top: 40px; font-size: 12px; border-collapse: collapse; color: #000 !important;">
            <tr>
                <td style="text-align: center; width: 50%;">__________________________________________________<br><b>Responsável pela Emissão</b></td>
                <td style="text-align: center; width: 50%;">__________________________________________________<br><b>Aprovação / Gerência</b></td>
            </tr>
        </table>
    </div>
</body>
</html>
"""
                    components.html(print_rel_html, height=750, scrolling=True)

    # --- TELA 4: FORMULÁRIOS E PRAZOS (FMS) ---
    elif menu == "📅 Formulários e Prazos (FMs)":
        st.markdown("# 📅 Gestão de Conformidade de Formulários (FMs)")
        tab_fm1, tab_fm2, tab_fm3 = st.tabs(["➕ Registrar / 🔄 Renovar FM", "🗑️ Excluir FM", "📊 Painel de Prazos e Status"])
        
        dias_dict = {
            "Diário (1 dia)": 1,
            "Semanal (7 dias)": 7, 
            "Quinzenal (15 dias)": 15, 
            "Mensal (30 dias)": 30, 
            "Bimestral (60 dias)": 60,
            "Trimestral (90 dias)": 90,
            "Semestral (180 dias)": 180
        }
        
        with tab_fm1:
            col_f_reg1, col_f_reg2 = st.columns(2)
            
            with col_f_reg1:
                st.subheader("Registrar Novo FM")
                with st.form("form_fm_stang", clear_on_submit=True):
                    fm_nome = st.text_input("Nome/Código do FM (Ex: FM 01 - Gerador)")
                    data_realizada = st.date_input("Data de Realização", value=datetime.now())
                    periodo_nome = st.selectbox("Período de Vencimento", list(dias_dict.keys()))
                    
                    if st.form_submit_button("Salvar e Calcular Prazo", use_container_width=True):
                        if not fm_nome:
                            st.error("Preencha o nome do FM!")
                        else:
                            df_fms = pd.read_csv(ARQUIVO_FMS, dtype=str)
                            nova_fm = {
                                "FM": fm_nome.upper(), 
                                "Data_Realizada": str(data_realizada), 
                                "Periodo": periodo_nome, 
                                "Dias_Prazo": str(dias_dict[periodo_nome])
                            }
                            df_fms = df_fms[df_fms["FM"].str.upper() != fm_nome.strip().upper()]
                            df_fms = pd.concat([df_fms, pd.DataFrame([nova_fm])], ignore_index=True)
                            df_fms.to_csv(ARQUIVO_FMS, index=False)
                            st.success(f"Formulário '{fm_nome.upper()}' cadastrado com sucesso!")
                            st.rerun()
                            
            with col_f_reg2:
                st.subheader("🔄 Renovar FM")
                df_fms_existente = pd.read_csv(ARQUIVO_FMS, dtype=str)
                if df_fms_existente.empty:
                    st.info("Nenhum FM cadastrado para renovar.")
                else:
                    lista_fms_cadastrados = df_fms_existente["FM"].unique().tolist()
                    
                    fm_escolhido = st.selectbox("Selecione o FM que foi refeito", lista_fms_cadastrados, key="select_fm_renovacao")
                    
                    row_fm_ant = df_fms_existente[df_fms_existente["FM"] == fm_escolhido]
                    per_ant_idx = 0
                    if not row_fm_ant.empty:
                        p_str = str(row_fm_ant.iloc[0]["Periodo"])
                        if p_str in list(dias_dict.keys()):
                            per_ant_idx = list(dias_dict.keys()).index(p_str)
                            
                    with st.form("form_renovar_fm"):
                        nova_data_realizada = st.date_input("Nova Data de Realização", value=datetime.now())
                        novo_periodo_nome = st.selectbox("Período de Vencimento / Renovação", list(dias_dict.keys()), index=per_ant_idx)
                        
                        btn_renovar = st.form_submit_button("🔄 Atualizar e Recalcular Vencimento", use_container_width=True)
                        
                        if btn_renovar:
                            df_fms_existente.loc[df_fms_existente["FM"] == fm_escolhido, "Data_Realizada"] = str(nova_data_realizada)
                            df_fms_existente.loc[df_fms_existente["FM"] == fm_escolhido, "Periodo"] = novo_periodo_nome
                            df_fms_existente.loc[df_fms_existente["FM"] == fm_escolhido, "Dias_Prazo"] = str(dias_dict[novo_periodo_nome])
                            
                            df_fms_existente.to_csv(ARQUIVO_FMS, index=False)
                            st.success(f"FM '{fm_escolhido}' atualizado com sucesso! Novo prazo recalculado.")
                            st.rerun()

        with tab_fm2:
            st.subheader("🗑️ Excluir Formulário (FM)")
            df_fms_exc = pd.read_csv(ARQUIVO_FMS, dtype=str)
            if df_fms_exc.empty:
                st.info("Nenhum FM cadastrado para exclusão.")
            else:
                lista_fms_exc = sorted(df_fms_exc["FM"].unique().tolist())
                with st.form("form_excluir_fm"):
                    fm_para_excluir = st.selectbox("Selecione o FM que deseja excluir permanentemente", lista_fms_exc)
                    btn_conf_exc_fm = st.form_submit_button("🗑️ Excluir FM Selecionado", type="primary", use_container_width=True)
                    
                    if btn_conf_exc_fm:
                        df_fms_exc = df_fms_exc[df_fms_exc["FM"] != fm_para_excluir]
                        df_fms_exc.to_csv(ARQUIVO_FMS, index=False)
                        st.success(f"Formulário '{fm_para_excluir}' excluído com sucesso!")
                        st.rerun()

        with tab_fm3:
            st.subheader("Painel de Prazos e Status dos FMs")
            df_fms = pd.read_csv(ARQUIVO_FMS, dtype=str)
            if not df_fms.empty:
                hoje = datetime.now().date()
                df_fms['Data_Realizada'] = pd.to_datetime(df_fms['Data_Realizada']).dt.date
                df_fms['Dias_Prazo_int'] = pd.to_numeric(df_fms['Dias_Prazo'], errors='coerce').fillna(0).astype(int)
                df_fms['Vencimento'] = df_fms.apply(lambda row: row['Data_Realizada'] + timedelta(days=int(row['Dias_Prazo_int'])), axis=1)
                df_fms['Dias_Restantes'] = df_fms['Vencimento'].apply(lambda x: (x - hoje).days)
                df_fms['Status'] = df_fms['Dias_Restantes'].apply(lambda x: "Atrasado 🔴" if x < 0 else "No Prazo 🟢")
                
                st.dataframe(df_fms[["FM", "Data_Realizada", "Periodo", "Vencimento", "Dias_Restantes", "Status"]], use_container_width=True)
                
                df_fms['Dias_Prazo'] = df_fms['Dias_Prazo_int']
                df_melted = df_fms.melt(
                    id_vars=['FM', 'Data_Realizada', 'Periodo'], 
                    value_vars=['Dias_Prazo', 'Dias_Restantes'],
                    var_name='Métrica', 
                    value_name='Dias'
                )
                df_melted['Métrica'] = df_melted['Métrica'].replace({
                    'Dias_Prazo': 'Prazo',
                    'Dias_Restantes': 'Dias Restantes'
                })
                
                fig = px.bar(
                    df_melted, 
                    x='FM', 
                    y='Dias', 
                    color='Métrica', 
                    barmode='group',
                    text='Dias',
                    title='Comparativo de Prazos e Dias Restantes por Formulário (FM)',
                    color_discrete_map={'Prazo': '#FF7F0E', 'Dias Restantes': '#1F77B4'}
                )
                fig.update_traces(texttemplate='%{text}', textposition='outside')
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)", 
                    xaxis_title="Formulário (FM)",
                    yaxis_title="Dias"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Cadastre o primeiro formulário na aba anterior para visualizar os cálculos automáticos e gráficos.")

    # --- TELA 5: SOLICITAÇÕES DE COMPRAS ---
    elif menu == "🛒 Solicitações de Compras":
        st.markdown("# 🛒 Solicitações de Materiais e Insumos")
        
        if "carrinho_compras" not in st.session_state:
            st.session_state.carrinho_compras = []
            
        if is_user_admin:
            abas_compras = st.tabs(["📋 Gerenciar Solicitações", "📝 Nova Solicitação", "🖨️ Imprimir Ordem de Compra", "✍️ Assinaturas (Admin)"])
            tab_comp1, tab_comp2, tab_comp3, tab_comp4 = abas_compras
        else:
            abas_compras = st.tabs(["📋 Gerenciar Solicitações", "📝 Nova Solicitação", "🖨️ Imprimir Ordem de Compra"])
            tab_comp1, tab_comp2, tab_comp3 = abas_compras
        
        with tab_comp1:
            st.markdown("### Gerenciar Solicitações e Anexar Orçamento")
            df_ger_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
            if df_ger_c.empty:
                st.info("Nenhuma solicitação de compra cadastrada.")
            else:
                def formatar_status_compra(val):
                    val_str = str(val).lower()
                    if "realizada" in val_str:
                        return "Compra Realizada 🟢"
                    elif "recusada" in val_str:
                        return "Compra Recusada 🔴"
                    else:
                        return "Compra em Aberta 🟠"
                
                def formatar_orcamento(val):
                    if pd.isna(val) or val == "None" or str(val).strip() == "":
                        return "None"
                    return "✅ Anexado"

                df_view = df_ger_c.copy()
                df_view['Status_Visual'] = df_view['Status'].apply(formatar_status_compra)
                df_view['Orcamento_Assinado'] = df_view['Orcamento_Assinado'].apply(formatar_orcamento)
                df_view['Data_Apenas'] = df_view['Data_Solicitacao'].astype(str).str.split(" ").str[0]

                st.markdown("""
                    <style>
                        .filtro-compras-box label p {
                            font-size: 11px !important;
                            font-weight: 600 !important;
                            margin-bottom: -2px !important;
                        }
                        .filtro-compras-box div[data-baseweb="select"] {
                            min-height: 30px !important;
                        }
                    </style>
                """, unsafe_allow_html=True)

                st.markdown("<div class='filtro-compras-box'>", unsafe_allow_html=True)
                col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
                
                with col_f1:
                    opts_data = ["Todas"] + sorted([d for d in df_view['Data_Apenas'].dropna().unique() if str(d).strip() != ""])
                    filtro_data = st.selectbox("📅 Data", opts_data, key="f_comp_data")
                with col_f2:
                    opts_solic = ["Todos"] + sorted([s for s in df_view['Solicitante'].dropna().unique() if str(s).strip() != ""])
                    filtro_solic = st.selectbox("👤 Solicitante", opts_solic, key="f_comp_solic")
                with col_f3:
                    opts_cat = ["Todas"] + sorted([c for c in df_view['Categoria'].dropna().unique() if str(c).strip() != ""])
                    filtro_cat = st.selectbox("📁 Categoria", opts_cat, key="f_comp_cat")
                with col_f4:
                    opts_item = ["Todos"] + sorted([i for i in df_view['Item'].dropna().unique() if str(i).strip() != ""])
                    filtro_item = st.selectbox("📦 Item", opts_item, key="f_comp_item")
                with col_f5:
                    opts_status = ["Todos"] + sorted([st_v for st_v in df_view['Status_Visual'].dropna().unique() if str(st_v).strip() != ""])
                    filtro_status_v = st.selectbox("🚦 Status", opts_status, key="f_comp_status")
                st.markdown("</div>", unsafe_allow_html=True)

                if filtro_data != "Todas":
                    df_view = df_view[df_view['Data_Apenas'] == filtro_data]
                if filtro_solic != "Todos":
                    df_view = df_view[df_view['Solicitante'] == filtro_solic]
                if filtro_cat != "Todas":
                    df_view = df_view[df_view['Categoria'] == filtro_cat]
                if filtro_item != "Todos":
                    df_view = df_view[df_view['Item'] == filtro_item]
                if filtro_status_v != "Todos":
                    df_view = df_view[df_view['Status_Visual'] == filtro_status_v]

                st.dataframe(df_view[["ID_Compra", "Data_Solicitacao", "Solicitante", "Setor", "Categoria", "Item", "Quantidade", "Status_Visual", "Orcamento_Assinado"]], use_container_width=True, height=200)
                
                ids_compras = sorted(df_ger_c["ID_Compra"].unique().tolist(), reverse=True)
                
                st.markdown("---")
                
                if is_user_admin:
                    col_ges_1, col_ges_2 = st.columns(2)
                    
                    with col_ges_1:
                        st.markdown("#### 📎 Gerenciar Orçamento Anexado")
                        id_anexo = st.selectbox("ID da Solicitação", ids_compras, key="select_id_anexo_gerir")
                        
                        row_atual_anexo = df_ger_c[df_ger_c["ID_Compra"] == str(id_anexo)]
                        path_atual = "None"
                        if not row_atual_anexo.empty:
                            path_atual = row_atual_anexo.iloc[0].get("Orcamento_Assinado", "None")
                        
                        tem_anexo = pd.notna(path_atual) and str(path_atual).strip() != "None" and str(path_atual).strip() != "" and os.path.exists(str(path_atual))
                        
                        with st.form("form_anexar_orcamento", clear_on_submit=False):
                            arquivo_anexo = st.file_uploader("Documento (PDF/Img)", type=["pdf", "png", "jpg", "jpeg"])
                            excluir_atual = st.checkbox("🗑️ Excluir atual", value=False, disabled=not tem_anexo)
                            if tem_anexo:
                                st.caption(f"Atual: {os.path.basename(str(path_atual))}")
                            else:
                                st.caption("Nenhum anexo atual.")
                            
                            col_b1, col_b2 = st.columns(2)
                            btn_anexar = col_b1.form_submit_button("💾 Salvar", use_container_width=True)
                            btn_remover_apenas = col_b2.form_submit_button("🗑️ Remover", use_container_width=True)
                            
                            if btn_anexar:
                                acao_realizada = False
                                if excluir_atual and tem_anexo:
                                    try:
                                        if os.path.exists(str(path_atual)):
                                            os.remove(str(path_atual))
                                    except:
                                        pass
                                    df_ger_c.loc[df_ger_c["ID_Compra"] == str(id_anexo), "Orcamento_Assinado"] = "None"
                                    acao_realizada = True
                                
                                if arquivo_anexo is not None:
                                    if tem_anexo and not excluir_atual:
                                        try:
                                            if os.path.exists(str(path_atual)):
                                                os.remove(str(path_atual))
                                        except:
                                            pass
                                            
                                    file_name = f"pedido_{id_anexo}_{arquivo_anexo.name}"
                                    save_path = os.path.join("uploads_orcamentos", file_name)
                                    
                                    with open(save_path, "wb") as f:
                                        f.write(arquivo_anexo.getbuffer())
                                        
                                    df_ger_c.loc[df_ger_c["ID_Compra"] == str(id_anexo), "Orcamento_Assinado"] = save_path
                                    acao_realizada = True
                                
                                if acao_realizada:
                                    df_to_save = df_ger_c.drop(columns=["Status_Visual", "Data_Apenas"], errors="ignore")
                                    df_to_save.to_csv(ARQUIVO_COMPRAS, index=False)
                                    st.success("Salvo com sucesso!")
                                    st.rerun()

                            if btn_remover_apenas:
                                if tem_anexo:
                                    try:
                                        if os.path.exists(str(path_atual)):
                                            os.remove(str(path_atual))
                                    except:
                                        pass
                                    df_ger_c.loc[df_ger_c["ID_Compra"] == str(id_anexo), "Orcamento_Assinado"] = "None"
                                    df_to_save = df_ger_c.drop(columns=["Status_Visual", "Data_Apenas"], errors="ignore")
                                    df_to_save.to_csv(ARQUIVO_COMPRAS, index=False)
                                    st.success("Removido!")
                                    st.rerun()
                                else:
                                    st.warning("Sem anexo.")

                    with col_ges_2:
                        st.markdown("#### ⚙️ Status, Itens & Exclusão")
                        id_pedido_status = st.selectbox("ID Pedido", ids_compras, key="sel_status_compra")
                        
                        rows_pedido = df_ger_c[df_ger_c["ID_Compra"] == str(id_pedido_status)]
                        status_atual_p = rows_pedido.iloc[0]["Status"] if not rows_pedido.empty else "Compra em Aberta"
                        
                        with st.form("form_mudar_status_compra"):
                            status_opcs = ["Compra em Aberta 🟠", "Compra Realizada 🟢", "Compra Recusada 🔴"]
                            idx_st_p = 0
                            if "Realizada" in status_atual_p: idx_st_p = 1
                            elif "Recusada" in status_atual_p: idx_st_p = 2
                            
                            novo_status_pedido = st.selectbox("Novo Status", status_opcs, index=idx_st_p)
                            
                            st.markdown("<b>Editar Itens e Quantidades do Pedido:</b>", unsafe_allow_html=True)
                            item_edits = []
                            for idx_r, r_val in rows_pedido.reset_index().iterrows():
                                st.markdown(f"Item #{idx_r+1}: <b>{r_val['Item']}</b> ({r_val['Categoria']})", unsafe_allow_html=True)
                                nova_qtd = st.number_input(f"Qtd para {r_val['Item']}", min_value=1, value=int(float(r_val['Quantidade'])) if str(r_val['Quantidade']).replace('.','',1).isdigit() else 1, key=f"qty_{id_pedido_status}_{idx_r}")
                                novo_nome_item = st.text_input(f"Nome do Item {idx_r+1}", value=r_val['Item'], key=f"name_{id_pedido_status}_{idx_r}")
                                item_edits.append({"index_original": r_val['index'], "novo_nome": novo_nome_item, "nova_qtd": nova_qtd})
                            
                            col_st1, col_st2 = st.columns(2)
                            btn_salvar_status = col_st1.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                            btn_exc_compra = col_st2.form_submit_button("🗑️ Excluir Pedido", type="primary", use_container_width=True)
                            
                            if btn_salvar_status:
                                if "Realizada" in novo_status_pedido:
                                    status_limpo = "Compra Realizada"
                                elif "Recusada" in novo_status_pedido:
                                    status_limpo = "Compra Recusada"
                                else:
                                    status_limpo = "Compra em Aberta"

                                df_ger_c.loc[df_ger_c["ID_Compra"] == str(id_pedido_status), "Status"] = status_limpo
                                
                                for ed in item_edits:
                                    orig_idx = ed["index_original"]
                                    df_ger_c.loc[orig_idx, "Item"] = str(ed["novo_nome"]).upper()
                                    df_ger_c.loc[orig_idx, "Quantidade"] = str(ed["nova_qtd"])
                                
                                df_to_save = df_ger_c.drop(columns=["Status_Visual", "Data_Apenas"], errors="ignore")
                                df_to_save.to_csv(ARQUIVO_COMPRAS, index=False)
                                st.success("Status e itens atualizados com sucesso!")
                                st.rerun()
                                
                            if btn_exc_compra:
                                df_ger_c = df_ger_c[df_ger_c["ID_Compra"] != str(id_pedido_status)]
                                df_to_save = df_ger_c.drop(columns=["Status_Visual", "Data_Apenas"], errors="ignore")
                                df_to_save.to_csv(ARQUIVO_COMPRAS, index=False)
                                st.success("Pedido excluído com sucesso!")
                                st.rerun()
                else:
                    st.info("🔒 O gerenciamento de orçamentos, alteração de status, edição de itens e exclusão são restritos a administradores.")

        with tab_comp2:
            st.markdown("### Adicione os itens desejados na solicitação:")
            with st.form("form_add_item_compra", clear_on_submit=True):
                col_i1, col_i2, col_i3 = st.columns([2, 1.5, 1])
                with col_i1:
                    item_input = st.text_input("Nome do Material / Item (Ex: Vassoura, Detergente) *")
                with col_i2:
                    cat_input = st.selectbox("Categoria", ["Material de Escritório", "Item Operacional", "Material de Limpeza"])
                with col_i3:
                    qtd_input = st.number_input("Quantidade", min_value=1, value=1)
                    
                btn_add_item = st.form_submit_button("➕ Adicionar Item à Lista da Solicitação", use_container_width=True)
                if btn_add_item:
                    if not item_input:
                        st.error("Informe o nome do material!")
                    else:
                        st.session_state.carrinho_compras.append({
                            "Item": item_input.upper(),
                            "Categoria": cat_input,
                            "Quantidade": int(qtd_input)
                        })
                        st.success(f"Item '{item_input.upper()}' (Qtd: {qtd_input}) adicionado à lista!")
            
            if st.session_state.carrinho_compras:
                st.markdown("#### Itens Atuais na Solicitação:")
                df_carrinho = pd.DataFrame(st.session_state.carrinho_compras)
                st.dataframe(df_carrinho, use_container_width=True)
                
                if st.button("🗑️ Limpar Lista de Itens"):
                    st.session_state.carrinho_compras = []
                    st.rerun()
                
                st.markdown("---")
                with st.form("form_finalizar_pedido"):
                    st.markdown("#### Dados Finais da Solicitação:")
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        solicitante_c = st.text_input("Nome do Solicitante *")
                        setor_c = st.selectbox("Setor", ["OPERAÇÃO", "MANUTENÇÃO", "PORTARIA", "ADMINISTRATIVO", "TI"])
                    with col_f2:
                        obs_c = st.text_area("Observações / Justificativa Geral")
                        
                    submit_final_compra = st.form_submit_button("💾 Salvar e Registrar Pedido Completo", use_container_width=True)
                    if submit_final_compra:
                        if not solicitante_c:
                            st.error("Preencha o nome do Solicitante!")
                        else:
                            df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
                            if not df_c.empty and "ID_Compra" in df_c.columns:
                                ids_nums = pd.to_numeric(df_c["ID_Compra"], errors="coerce").dropna()
                                novo_id_c = int(ids_nums.max() + 1) if not ids_nums.empty else 501
                            else:
                                novo_id_c = 501
                                
                            data_hora_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
                            
                            novas_linhas = []
                            for it in st.session_state.carrinho_compras:
                                novas_linhas.append({
                                    "ID_Compra": str(novo_id_c),
                                    "Data_Solicitacao": data_hora_atual,
                                    "Solicitante": solicitante_c.upper(),
                                    "Setor": setor_c.upper(),
                                    "Categoria": it["Categoria"],
                                    "Item": it["Item"],
                                    "Quantidade": str(it["Quantidade"]),
                                    "Observacoes": obs_c.upper() if obs_c else "",
                                    "Status": "Compra em Aberta",
                                    "Orcamento_Assinado": "None",
                                    "NF_Anexada": "None",
                                    "Boleto_Anexado": "None",
                                    "Assinado_Por": "None"
                                })
                            
                            df_c = pd.concat([df_c, pd.DataFrame(novas_linhas)], ignore_index=True)
                            df_c.to_csv(ARQUIVO_COMPRAS, index=False)
                            st.session_state.carrinho_compras = []
                            st.success(f"Solicitação de Compra #{novo_id_c} registrada com sucesso com todos os itens!")
                            st.rerun()
            else:
                st.info("Nenhum item adicionado à lista ainda. Preencha acima e clique em 'Adicionar Item à Lista'.")

        with tab_comp3:
            df_c_print = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
            if df_c_print.empty:
                st.warning("Nenhuma solicitação de compra cadastrada para impressão.")
            else:
                ids_disponiveis = sorted(df_c_print["ID_Compra"].unique().tolist(), reverse=True)
                
                col_print1, col_print2 = st.columns([2, 1])
                with col_print1:
                    pedido_sel_id = st.selectbox("Selecione o ID do Pedido de Compra:", ids_disponiveis)
                
                itens_pedido = df_c_print[df_c_print["ID_Compra"] == str(pedido_sel_id)]
                row_c_base = itens_pedido.iloc[0]
                
                with col_print2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    anexo_path = row_c_base.get("Orcamento_Assinado", "None")
                    if pd.notna(anexo_path) and str(anexo_path).strip() != "None" and str(anexo_path).strip() != "" and os.path.exists(str(anexo_path)):
                        with open(anexo_path, "rb") as file:
                            st.download_button(
                                label="📥 Baixar Orçamento Anexado",
                                data=file,
                                file_name=os.path.basename(str(anexo_path)),
                                mime="application/octet-stream",
                                use_container_width=True
                            )
                    else:
                        st.info("Nenhum orçamento anexado a este pedido.")
                
                st.markdown("---")
                
                logo_base64 = ""
                if os.path.exists("logo.png"):
                    with open("logo.png", "rb") as img_file:
                        logo_base64 = base64.b64encode(img_file.read()).decode()
                        
                linhas_tabela_html = ""
                for _, row in itens_pedido.iterrows():
                    linhas_tabela_html += f"""
                    <tr>
                        <td style="border: 1px solid #000; padding: 8px; width: 60%;"><b>{row['Item']}</b> ({row['Categoria']})</td>
                        <td style="border: 1px solid #000; padding: 8px; width: 40%; text-align: center;">{row['Quantidade']}</td>
                    </tr>
                    """
                        
                print_compra_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ background-color: #ffffff; color: #000000; margin: 0; padding: 10px; font-family: Arial, sans-serif; }}
        .print-btn-container {{ text-align: center; margin-bottom: 20px; }}
        .btn-imprimir {{ background-color: #007bff; color: white; border: none; padding: 12px 25px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; }}
        @media print {{ .print-btn-container {{ display: none !important; }} body {{ padding: 0; }} }}
    </style>
</head>
<body>
    <div class="print-btn-container">
        <button class="btn-imprimir" onclick="window.print()">🖨️ Imprimir Ordem de Solicitação de Compra</button>
    </div>
    <div style="background-color: #ffffff; color: #000000; padding: 20px; border: 2px solid #000; max-width: 800px; margin: auto;">
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000;">
            <tr>
                <td style="width: 28%; border: 1px solid #000; padding: 5px; text-align: center; vertical-align: middle;">
                    <img src="data:image/png;base64,{logo_base64}" style="max-height: 45px; max-width: 100%;">
                </td>
                <td style="width: 44%; border: 1px solid #000; text-align: center; vertical-align: middle;">
                    <h3 style="margin: 0; color: #000 !important; font-size: 15px;">Ordem de Solicitação de Compras</h3>
                </td>
                <td style="width: 28%; border: 1px solid #000; padding: 5px; font-size: 11px; text-align: right; color: #000 !important; vertical-align: middle;">
                    <b>LOG-COMPRAS</b>
                </td>
            </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; color: #000 !important; margin-top: 5px;">
            <tr>
                <td style="border: 1px solid #000; padding: 5px; width: 33%;"><b>ID Pedido:</b> #{row_c_base['ID_Compra']}</td>
                <td style="border: 1px solid #000; padding: 5px; width: 34%;"><b>Data:</b> {row_c_base['Data_Solicitacao']}</td>
                <td style="border: 1px solid #000; padding: 5px; width: 33%;"><b>Status:</b> {row_c_base['Status']}</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 5px;" colspan="2"><b>Solicitante:</b> {row_c_base['Solicitante']}</td>
                <td style="border: 1px solid #000; padding: 5px;"><b>Setor:</b> {row_c_base['Setor']}</td>
            </tr>
        </table>
        <div style="margin-top: 15px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 12px; color: #000 !important;">
                <thead>
                    <tr style="background-color: #e0e0e0;">
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">Item / Material</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: center;">Quantidade</th>
                    </tr>
                </thead>
                <tbody>
                    {linhas_tabela_html}
                </tbody>
            </table>
        </div>
        <div style="border: 1px solid #000; margin-top: 15px;">
            <div style="background-color: #e0e0e0; text-align: center; font-size: 12px; font-weight: bold; border-bottom: 1px solid #000; padding: 4px; color: #000 !important;">Observações / Justificativa</div>
            <div style="padding: 10px; min-height: 50px; font-size: 13px; color: #000 !important;">{row_c_base.get('Observacoes', '')}</div>
        </div>
        <table style="width: 100%; margin-top: 40px; font-size: 12px; border-collapse: collapse; color: #000 !important;">
            <tr>
                <td style="text-align: center; width: 50%;">__________________________________________________<br><b>Solicitante ({row_c_base['Solicitante']})</b></td>
                <td style="text-align: center; width: 50%;">__________________________________________________<br><b>Aprovação Compras / Gerência</b></td>
            </tr>
        </table>
    </div>
</body>
</html>
"""
                components.html(print_compra_html, height=750, scrolling=True)

        # ABA 4 - ASSINATURAS E ENVIOS DE E-MAIL (SOMENTE ADMIN)
        if is_user_admin:
            with tab_comp4:
                st.markdown("### ✍️ Painel de Assinaturas (NF e Boleto) e Configurações de E-mail SMTP")
                
                # --- SUB-SEÇÃO 1: CONFIGURAÇÃO DE E-MAIL REMETENTE / SMTP ---
                with st.expander("⚙️ Configurações de E-mail para Envio Real (SMTP / Gmail / Outlook)"):
                    df_email_cfg = pd.read_csv(ARQUIVO_CONFIG_EMAIL, dtype=str)
                    cfg_row = df_email_cfg.iloc[0] if not df_email_cfg.empty else {}
                    
                    with st.form("form_configuracao_email_api"):
                        st.markdown("**Cadastrar / Configurar Conta Remetente:**")
                        c_e1, c_e2 = st.columns(2)
                        with c_e1:
                            remetente_email = st.text_input("E-mail Remetente", value=str(cfg_row.get("Email_Remetente", "compras@stang.com.br")))
                            remetente_nome = st.text_input("Nome do Remetente", value=str(cfg_row.get("Nome_Remetente", "Intranet Stang Compras")))
                        with c_e2:
                            api_key_str = st.text_input("Senha de App / Token SMTP", value=str(cfg_row.get("API_Key", "")), type="password")
                            servidor_smtp = st.text_input("Servidor SMTP Host", value=str(cfg_row.get("Servidor_SMTP", "smtp.gmail.com")))
                            porta_smtp_in = st.text_input("Porta SMTP", value=str(cfg_row.get("Porta_SMTP", "587")))
                            
                        btn_salvar_email_cfg = st.form_submit_button("💾 Salvar Configurações de E-mail")
                        if btn_salvar_email_cfg:
                            nova_cfg = pd.DataFrame([{
                                "Email_Remetente": remetente_email,
                                "Nome_Remetente": remetente_nome,
                                "API_Key": api_key_str,
                                "Servidor_SMTP": servidor_smtp,
                                "Porta_SMTP": porta_smtp_in
                            }])
                            nova_cfg.to_csv(ARQUIVO_CONFIG_EMAIL, index=False)
                            st.success("Configurações de E-mail salvas com sucesso!")
                            st.rerun()

                st.markdown("---")
                
                # --- SUB-SEÇÃO 2: ASSINATURAS E ANEXOS ---
                df_ass = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
                if df_ass.empty:
                    st.info("Nenhuma compra registrada para assinar.")
                else:
                    ids_ass = sorted(df_ass["ID_Compra"].unique().tolist(), reverse=True)
                    col_sel1, col_sel2 = st.columns([1, 2])
                    
                    with col_sel1:
                        id_sel_ass = st.selectbox("Selecione o Número do Pedido (Orçamento):", ids_ass, key="sel_ass_id")
                        rows_ass = df_ass[df_ass["ID_Compra"] == str(id_sel_ass)]
                        row_base_ass = rows_ass.iloc[0]
                    
                    with col_sel2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        assinado_por_val = str(row_base_ass.get('Assinado_Por', 'None'))
                        
                        if assinado_por_val != "None" and assinado_por_val.strip() != "":
                            st.markdown(f"**Status da Assinatura Digital:** <span style='color: #00ff66; font-weight: bold;'>🟢 Assinado por: {assinado_por_val}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("**Status da Assinatura Digital:** <span style='color: #ff4444; font-weight: bold;'>🔴 Pendente de Assinatura</span>", unsafe_allow_html=True)

                        st.write(f"**Orçamento Anexado:** {'✅ Sim' if str(row_base_ass.get('Orcamento_Assinado', 'None')) != 'None' else '❌ Não'}")
                        st.write(f"**NF Anexada:** {'✅ Sim' if str(row_base_ass.get('NF_Anexada', 'None')) != 'None' else '❌ Não'}")
                        st.write(f"**Boleto Anexado:** {'✅ Sim' if str(row_base_ass.get('Boleto_Anexado', 'None')) != 'None' else '❌ Não'}")
                    
                    st.markdown("---")
                    
                    col_upload, col_acoes = st.columns(2)
                    
                    with col_upload:
                        with st.form("form_up_nf_bol"):
                            st.markdown("**Upload de Nota Fiscal e Boleto**")
                            up_nf = st.file_uploader("Upload da Nota Fiscal (NF)", type=["pdf", "png", "jpg", "jpeg"])
                            up_bol = st.file_uploader("Upload do Boleto", type=["pdf", "png", "jpg", "jpeg"])
                            
                            if st.form_submit_button("Salvar Documentos"):
                                salvou_algo = False
                                if up_nf is not None:
                                    nf_name = f"nf_{id_sel_ass}_{up_nf.name}"
                                    nf_path = os.path.join("uploads_orcamentos", nf_name)
                                    with open(nf_path, "wb") as f: f.write(up_nf.getbuffer())
                                    df_ass.loc[df_ass["ID_Compra"] == str(id_sel_ass), "NF_Anexada"] = nf_path
                                    salvou_algo = True
                                    
                                if up_bol is not None:
                                    bol_name = f"boleto_{id_sel_ass}_{up_bol.name}"
                                    bol_path = os.path.join("uploads_orcamentos", bol_name)
                                    with open(bol_path, "wb") as f: f.write(up_bol.getbuffer())
                                    df_ass.loc[df_ass["ID_Compra"] == str(id_sel_ass), "Boleto_Anexado"] = bol_path
                                    salvou_algo = True
                                    
                                if salvou_algo:
                                    df_to_save = df_ass.drop(columns=["Status_Visual", "Data_Apenas"], errors="ignore")
                                    df_to_save.to_csv(ARQUIVO_COMPRAS, index=False)
                                    st.success("Documentos salvos com sucesso!")
                                    st.rerun()

                    with col_acoes:
                        st.markdown("**✍️ Selecionar e Carimbar Assinatura Digital**")
                        
                        df_u_ass = pd.read_csv(ARQUIVO_USERS, dtype=str)
                        row_u_logado = df_u_ass[df_u_ass["Usuario"].str.lower() == st.session_state.usuario.lower()]
                        
                        ass_cadastrada_path = "None"
                        if not row_u_logado.empty:
                            ass_cadastrada_path = str(row_u_logado.iloc[0].get("Assinatura_PNG", "None"))
                            
                        ass_valida = (ass_cadastrada_path != "None" and os.path.exists(ass_cadastrada_path))
                        
                        if ass_valida:
                            st.caption(f"Assinatura digital cadastrada para **{st.session_state.usuario}** carregada com sucesso:")
                            st.image(ass_cadastrada_path, width=180)
                        else:
                            st.warning("⚠️ Nenhuma assinatura em PNG cadastrada para o seu usuário. Faça o upload temporário abaixo:")
                            up_ass_temp = st.file_uploader("Upload Temporário da Assinatura PNG", type=["png"], key="temp_png_ass")
                            if up_ass_temp is not None:
                                ass_cadastrada_path = os.path.join("uploads_assinaturas", f"temp_{st.session_state.usuario}.png")
                                with open(ass_cadastrada_path, "wb") as f:
                                    f.write(up_ass_temp.getbuffer())
                                ass_valida = True
                                
                        if st.button("✍️ Carimbar e Assinar Documentos (NF / Boleto / Orçamento)", use_container_width=True):
                            nf_path = str(row_base_ass.get("NF_Anexada", "None"))
                            bol_path = str(row_base_ass.get("Boleto_Anexado", "None"))
                            orc_path = str(row_base_ass.get("Orcamento_Assinado", "None"))
                            
                            tem_docs = (nf_path != "None" and os.path.exists(nf_path)) or (bol_path != "None" and os.path.exists(bol_path)) or (orc_path != "None" and os.path.exists(orc_path))
                            
                            if not tem_docs:
                                st.error("Faça o upload do Orçamento, Nota Fiscal ou Boleto antes de assinar.")
                            elif not ass_valida:
                                st.error("É necessário possuir uma assinatura PNG para carimbar o documento.")
                            else:
                                erro_carimbo = False
                                # Aplica a assinatura no final de cada documento existente no pedido
                                for p_doc in [nf_path, bol_path, orc_path]:
                                    if p_doc != "None" and os.path.exists(p_doc):
                                        res = carimbar_assinatura_no_documento(p_doc, ass_cadastrada_path, st.session_state.usuario)
                                        if not res:
                                            erro_carimbo = True

                                df_ass.loc[df_ass["ID_Compra"] == str(id_sel_ass), "Assinado_Por"] = st.session_state.usuario
                                df_to_save = df_ass.drop(columns=["Status_Visual", "Data_Apenas"], errors="ignore")
                                df_to_save.to_csv(ARQUIVO_COMPRAS, index=False)
                                
                                if not erro_carimbo:
                                    st.success(f"Documentos assinados e carimbados com sucesso por: {st.session_state.usuario}! Status atualizado para 🟢.")
                                else:
                                    st.warning(f"Documentos marcados como assinados por {st.session_state.usuario}, mas alguns anexos não puderam ser carimbados visualmente.")
                                st.rerun()
                                
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        df_email_cfg_cur = pd.read_csv(ARQUIVO_CONFIG_EMAIL, dtype=str)
                        cfg_email_dict = df_email_cfg_cur.iloc[0].to_dict() if not df_email_cfg_cur.empty else {}
                        remetente_cadastrado = cfg_email_dict.get("Email_Remetente", "compras@stang.com.br")
                        
                        with st.form("form_email_ass"):
                            st.markdown("**📧 Envio do Pedido por E-mail (Real / SMTP)**")
                            st.caption(f"Remetente: **{remetente_cadastrado}**")
                            email_dest = st.text_input("E-mail de Destino *")
                            obs_email = st.text_area("Observação / Mensagem do E-mail")
                            
                            if st.form_submit_button("📧 Enviar por E-mail Agora", use_container_width=True):
                                if not email_dest:
                                    st.error("Preencha o e-mail de destino.")
                                elif str(row_base_ass.get("Assinado_Por", "None")) == "None":
                                    st.error("Os documentos precisam ser assinados digitalmente antes do envio.")
                                else:
                                    lista_anexos_envio = []
                                    for key_doc in ["Orcamento_Assinado", "NF_Anexada", "Boleto_Anexado"]:
                                        p_f = str(row_base_ass.get(key_doc, "None"))
                                        if p_f != "None" and os.path.exists(p_f):
                                            lista_anexos_envio.append(p_f)
                                            
                                    assunto_e = f"Solicitação de Compra #{id_sel_ass} - Documentos Assinados"
                                    corpo_e = f"Olá,\n\nSegue em anexo a documentação referente à Solicitação de Compra #{id_sel_ass}.\n\n"
                                    corpo_e += f"Solicitante: {row_base_ass.get('Solicitante', '')}\nSetor: {row_base_ass.get('Setor', '')}\n"
                                    corpo_e += f"Assinado digitalmente por: {row_base_ass.get('Assinado_Por', '')}\n\n"
                                    if obs_email:
                                        corpo_e += f"Observações:\n{obs_email}\n\n"
                                    corpo_e += "Atenciosamente,\nIntranet Stang"
                                    
                                    sucesso_e, msg_e = enviar_email_real(email_dest, assunto_e, corpo_e, lista_anexos_envio, cfg_email_dict)
                                    
                                    if sucesso_e:
                                        st.success(msg_e)
                                    else:
                                        st.error(msg_e)

    # --- TELA 6: DASHBOARD ---
    elif menu == "📊 Dashboard":
        st.markdown("# 📊 Painel Geral de Indicadores (Dashboard)")
        
        df_os_dash = carregar_banco_os()
        df_compras_dash = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
        df_fms_dash = pd.read_csv(ARQUIVO_FMS, dtype=str)
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Total de O.S.", len(df_os_dash))
        with col_m2:
            os_abertas = len(df_os_dash[df_os_dash["Status"] != "Finalizada"]) if not df_os_dash.empty else 0
            st.metric("O.S. Em Aberto", os_abertas)
        with col_m3:
            st.metric("Solicitações de Compra", len(df_compras_dash["ID_Compra"].unique()) if not df_compras_dash.empty else 0)
        with col_m4:
            st.metric("Formulários (FMs)", len(df_fms_dash) if not df_fms_dash.empty else 0)
            
        st.markdown("---")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if not df_os_dash.empty:
                fig_os = px.pie(df_os_dash, names="Status", title="Distribuição de O.S. por Status", hole=0.4)
                fig_os.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_os, use_container_width=True)
            else:
                st.info("Sem dados de O.S. para exibir gráfico.")
                
        with col_g2:
            if not df_compras_dash.empty:
                fig_comp = px.histogram(df_compras_dash, x="Categoria", title="Solicitações de Compras por Categoria", color="Status")
                fig_comp.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_comp, use_container_width=True)
            else:
                st.info("Sem dados de Compras para exibir gráfico.")
