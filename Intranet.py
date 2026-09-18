import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
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
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as RLTable, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
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
    "🖨️ Emissão e Relatórios de O.S.", 
    "📅 Gestão de Conformidade de Formulários (FMs)",
    "🛒 Solicitações de Compras",
    "✍️ Painel de Assinaturas (NF e Boleto)",
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
        
        /* CARDS COMPACTOS DE STATUS (ESTILO POWER BI / MODERN BADGES) */
        .status-card-container {{
            display: flex;
            gap: 12px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .status-card {{
            flex: 1;
            min-width: 140px;
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            padding: 10px 14px;
            backdrop-filter: blur(8px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .status-card:hover {{
            border-color: rgba(0, 255, 204, 0.4);
            transform: translateY(-2px);
        }}
        .status-card-title {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 4px;
            font-weight: 600;
        }}
        .status-card-value {{
            font-size: 14px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .badge-success {{ color: #00ffaa; }}
        .badge-danger {{ color: #ff4b4b; }}
        .badge-warning {{ color: #ffb703; }}
        
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
    else:
        df_fms = pd.read_csv(ARQUIVO_FMS, dtype=str)
        mudou_fms = False
        if "Dias_Prazo" not in df_fms.columns:
            df_fms["Dias_Prazo"] = "30"
            mudou_fms = True
        if mudou_fms:
            df_fms.to_csv(ARQUIVO_FMS, index=False)
        
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
    colunas_users = [
        "Usuario", "Senha", "Validade", "Permissoes", "Admin", "Assinatura_PNG", 
        "Email_Usuario", "Senha_App_Email", "Servidor_SMTP", "Porta_SMTP"
    ]
    
    if not os.path.exists(ARQUIVO_USERS):
        df_users = pd.DataFrame([{
            "Usuario": "thiagosc",
            "Senha": "stang2026",
            "Validade": "Vitalício",
            "Permissoes": todos_menus_str,
            "Admin": "Sim",
            "Assinatura_PNG": "None",
            "Email_Usuario": "thiagosc@stang.com.br",
            "Senha_App_Email": "",
            "Servidor_SMTP": "smtp.gmail.com",
            "Porta_SMTP": "587"
        }])
        df_users.to_csv(ARQUIVO_USERS, index=False)
    else:
        df_users = pd.read_csv(ARQUIVO_USERS, dtype=str)
        mudou_u = False
        for col in colunas_users:
            if col not in df_users.columns:
                if col in ["Assinatura_PNG"]:
                    df_users[col] = "None"
                elif col == "Servidor_SMTP":
                    df_users[col] = "smtp.gmail.com"
                elif col == "Porta_SMTP":
                    df_users[col] = "587"
                else:
                    df_users[col] = ""
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
                "Email_Usuario": "thiagosc@stang.com.br",
                "Senha_App_Email": "",
                "Servidor_SMTP": "smtp.gmail.com",
                "Porta_SMTP": "587"
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

# Função auxiliar para renderizar arquivos (Imagens / PDFs em Base64)
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
            
            pdf_display = f'''
                <object data="data:application/pdf;base64,{base64_pdf}" type="application/pdf" width="100%" height="450px">
                    <embed src="data:application/pdf;base64,{base64_pdf}" type="application/pdf" width="100%" height="450px"/>
                    <p style="font-size: 12px; color: #666;">Se o seu navegador não exibir o PDF acima automaticamente, <a href="data:application/pdf;base64,{base64_pdf}" download="{os.path.basename(str(caminho_arquivo))}">clique aqui para baixar diretamente</a>.</p>
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

# --- FUNÇÃO PARA GERAR O PDF DA ORDEM DE SERVIÇO INDIVIDUAL ---
def gerar_pdf_os(os_row):
    if not HAS_PDF_LIBS:
        return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle('Title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, alignment=1)
    style_header_right = ParagraphStyle('HeaderRight', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=2)
    style_cell_normal = ParagraphStyle('CellNormal', parent=styles['Normal'], fontName='Helvetica', fontSize=9)
    style_cell_center_bold = ParagraphStyle('CellCenterBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1)
    
    elements = []
    
    logo_cell = Paragraph("<b>STANG</b>", style_title)
    if os.path.exists("logo.png"):
        try:
            logo_cell = RLImage("logo.png", width=100, height=35)
        except Exception:
            pass
            
    header_data = [
        [
            logo_cell,
            Paragraph("<b>Solicitação de Manutenção - Ordem de Serviço</b>", style_title),
            Paragraph("<b>FM 12</b><br/>Revisão: 02/2024", style_header_right)
        ]
    ]
    t_header = RLTable(header_data, colWidths=[120, 280, 140])
    t_header.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 4))
    
    data_criacao_val = str(os_row.get('Data_Criacao', ''))
    partes_dt = data_criacao_val.split(' ')
    data_str = partes_dt[0] if len(partes_dt) > 0 else ''
    hora_str = partes_dt[1] if len(partes_dt) > 1 else '17:00'
    
    info_data = [
        [
            Paragraph(f"<b>Número:</b> {os_row.get('ID', '')}", style_cell_normal),
            Paragraph(f"<b>Data:</b> {data_str}", style_cell_normal),
            Paragraph(f"<b>Hora:</b> {hora_str}", style_cell_normal)
        ]
    ]
    t_info = RLTable(info_data, colWidths=[180, 180, 180])
    t_info.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 4))
    
    prio_data = [
        [
            Paragraph("Tipo de Manutenção", style_cell_center_bold),
            Paragraph("Prioridade de Manutenção", style_cell_center_bold)
        ],
        [
            Paragraph(f"<b>{os_row.get('Tipo_Manutencao', '')}</b>", style_cell_center_bold),
            Paragraph(f"<b>{os_row.get('Prioridade', '')}</b>", style_cell_center_bold)
        ]
    ]
    t_prio = RLTable(prio_data, colWidths=[270, 270])
    t_prio.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#e0e0e0')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_prio)
    elements.append(Spacer(1, 4))
    
    equip_val = os_row.get('Equipamento', 'N/A')
    if pd.isna(equip_val) or str(equip_val).strip() == "":
        equip_val = 'N/A'
        
    solic_data = [
        [
            Paragraph(f"<b>SETOR:</b> {os_row.get('Setor', '')}", style_cell_normal),
            Paragraph(f"<b>SOLICITANTE:</b> {os_row.get('Solicitante', '')}", style_cell_normal)
        ],
        [
            Paragraph(f"<b>Equipamento:</b> {equip_val}", style_cell_normal),
            ""
        ]
    ]
    t_solic = RLTable(solic_data, colWidths=[270, 270])
    t_solic.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
        ('SPAN', (0,1), (1,1)),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_solic)
    elements.append(Spacer(1, 4))
    
    def criar_secao_texto(titulo, conteudo, min_height=40):
        val_txt = conteudo if pd.notna(conteudo) else ""
        sec_data = [
            [Paragraph(f"<b>{titulo}</b>", style_cell_center_bold)],
            [Paragraph(str(val_txt).replace('\n', '<br/>'), style_cell_normal)]
        ]
        t_sec = RLTable(sec_data, colWidths=[540], rowHeights=[18, max(min_height, 35)])
        t_sec.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (0,0), colors.HexColor('#e0e0e0')),
            ('VALIGN', (0,1), (0,1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        return t_sec

    elements.append(criar_secao_texto("Descrição do Problema", os_row.get('Descricao', ''), min_height=60))
    elements.append(Spacer(1, 4))
    elements.append(criar_secao_texto("Descrição da Solução", os_row.get('Solucao', ''), min_height=45))
    elements.append(Spacer(1, 4))
    elements.append(criar_secao_texto("Itens Trocados", os_row.get('Itens_Trocados', ''), min_height=35))
    elements.append(Spacer(1, 25))
    
    finalizador_val = os_row.get('finalizado_por', '')
    if pd.isna(finalizador_val):
        finalizador_val = ''
        
    ass_data = [
        [
            Paragraph("__________________________________________________<br/><b>Manutenção</b>", style_cell_center_bold),
            Paragraph(f"__________________________________________________<br/><b>Responsável pelo Serviço ({finalizador_val})</b>", style_cell_center_bold)
        ]
    ]
    t_ass = RLTable(ass_data, colWidths=[270, 270])
    t_ass.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_ass)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# --- AUTENTICAÇÃO E SESSÃO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "permissoes_usuario" not in st.session_state:
    st.session_state.permissoes_usuario = TODOS_MENUS

if not st.session_state.autenticado:
    st.markdown("<h2 style='text-align: center; color: white;'>🔐 Intranet Stang - Login</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            submit_login = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit_login:
                df_u = pd.read_csv(ARQUIVO_USERS, dtype=str)
                user_match = df_u[df_u["Usuario"].str.lower() == usuario_input.strip().lower()]
                if not user_match.empty and user_match.iloc[0]["Senha"] == senha_input:
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = user_match.iloc[0]["Usuario"]
                    st.session_state.is_admin = (user_match.iloc[0]["Admin"].strip().lower() == "sim")
                    perms_str = user_match.iloc[0]["Permissoes"]
                    if pd.isna(perms_str) or perms_str.strip() == "":
                        st.session_state.permissoes_usuario = TODOS_MENUS
                    else:
                        st.session_state.permissoes_usuario = [p.strip() for p in perms_str.split(",") if p.strip()]
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

# --- MENU LATERAL ---
st.sidebar.markdown(f"### 👤 Olá, **{st.session_state.usuario_logado}**")
menus_permitidos = [m for m in TODOS_MENUS if m in st.session_state.permissoes_usuario]
if not menus_permitidos:
    menus_permitidos = TODOS_MENUS

menu_escolhido = st.sidebar.radio("📌 Navegação", menus_permitidos)

if st.sidebar.button("🚪 Sair / Trocar Usuário", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.usuario_logado = ""
    st.session_state.is_admin = False
    st.rerun()

# ==============================================================================
# 1. ABA: NOVA O.S.
# ==============================================================================
if menu_escolhido == "📝 Nova O.S.":
    st.markdown("## 📝 Abertura de Nova Ordem de Serviço (O.S.)")
    
    with st.form("form_nova_os", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            solicitante = st.text_input("Solicitante *", value=st.session_state.usuario_logado)
            setor = st.selectbox("Setor *", ["Manutenção", "Operação", "Administrativo", "Segurança", "TI", "Qualidade"])
            equipamento = st.text_input("Equipamento / Máquina")
        with col2:
            tipo_manutencao = st.selectbox("Tipo de Manutenção *", ["Corretiva", "Preventiva", "Melhoria", "Preditiva"])
            prioridade = st.selectbox("Prioridade *", ["Baixa", "Média", "Alta", "Urgente"])
            
        descricao = st.text_area("Descrição Detalhada do Problema / Serviço *")
        
        submitted_os = st.form_submit_button("🚀 Cadastrar Ordem de Serviço", use_container_width=True)
        if submitted_os:
            if not solicitante or not descricao:
                st.error("Preencha os campos obrigatórios (Solicitante e Descrição).")
            else:
                df_os = carregar_banco_os()
                novo_id = int(df_os["ID"].max() + 1) if not df_os.empty and df_os["ID"].max() > 0 else 1
                
                nova_linha = {
                    "ID": novo_id,
                    "Data_Criacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Solicitante": solicitante,
                    "Setor": setor,
                    "Equipamento": equipamento if equipamento else "N/A",
                    "Tipo_Manutencao": tipo_manutencao,
                    "Prioridade": prioridade,
                    "Descricao": descricao,
                    "Solucao": "",
                    "Itens_Trocados": "",
                    "finalizado_por": "",
                    "Data_Termino": "",
                    "Status": "Aberta"
                }
                
                df_os = pd.concat([df_os, pd.DataFrame([nova_linha])], ignore_index=True)
                df_os.to_csv(ARQUIVO_OS, index=False)
                st.success(f"O.S. nº {novo_id} aberta com sucesso!")

# ==============================================================================
# 2. ABA: GERENCIAR O.S.
# ==============================================================================
elif menu_escolhido == "📋 Gerenciar O.S.":
    st.markdown("## 📋 Gerenciamento e Andamento de O.S.")
    df_os = carregar_banco_os()
    
    if df_os.empty:
        st.info("Nenhuma Ordem de Serviço cadastrada.")
    else:
        status_filtro = st.selectbox("Filtrar por Status", ["Todas", "Aberta", "Em Andamento", "Concluída"])
        if status_filtro != "Todas":
            df_os = df_os[df_os["Status"] == status_filtro]
            
        st.dataframe(df_os, use_container_width=True)
        
        st.markdown("### ⚙️ Atualizar O.S.")
        os_ids = df_os["ID"].tolist()
        if os_ids:
            os_selecionada = st.selectbox("Selecione o ID da O.S. para atualizar", os_ids)
            linha_atual = df_os[df_os["ID"] == os_selecionada].iloc[0]
            
            with st.form("form_atualiza_os"):
                novo_status = st.selectbox("Novo Status", ["Aberta", "Em Andamento", "Concluída"], index=["Aberta", "Em Andamento", "Concluída"].index(linha_atual["Status"]) if linha_atual["Status"] in ["Aberta", "Em Andamento", "Concluída"] else 0)
                solucao = st.text_area("Descrição da Solução", value=str(linha_atual["Solucao"]) if pd.notna(linha_atual["Solucao"]) else "")
                itens_trocados = st.text_input("Itens / Peças Trocadas", value=str(linha_atual["Itens_Trocados"]) if pd.notna(linha_atual["Itens_Trocados"]) else "")
                responsavel = st.text_input("Responsável pelo Serviço (Finalizado por)", value=str(linha_atual["finalizado_por"]) if pd.notna(linha_atual["finalizado_por"]) else st.session_state.usuario_logado)
                
                salvar_atualizacao = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                if salvar_atualizacao:
                    idx = df_os[df_os["ID"] == os_selecionada].index[0]
                    df_os.at[idx, "Status"] = novo_status
                    df_os.at[idx, "Solucao"] = solucao
                    df_os.at[idx, "Itens_Trocados"] = itens_trocados
                    df_os.at[idx, "finalizado_por"] = responsavel
                    if novo_status == "Concluída" and (pd.isna(df_os.at[idx, "Data_Termino"]) or str(df_os.at[idx, "Data_Termino"]) == ""):
                        df_os.at[idx, "Data_Termino"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df_os.to_csv(ARQUIVO_OS, index=False)
                    st.success(f"O.S. nº {os_selecionada} atualizada com sucesso!")
                    st.rerun()

# ==============================================================================
# 3. ABA: EMISSÃO E RELATÓRIOS DE O.S.
# ==============================================================================
elif menu_escolhido == "🖨️ Emissão e Relatórios de O.S.":
    st.markdown("## 🖨️ Emissão e Relatórios de O.S.")
    df_os = carregar_banco_os()
    
    if df_os.empty:
        st.info("Nenhuma Ordem de Serviço disponível para emissão.")
    else:
        tipo_emissao = st.radio("Selecione o tipo de emissão:", ["Emitir O.S. Individual (PDF)", "Imprimir Relatório Geral de O.S."], horizontal=True)
        
        if tipo_emissao == "Emitir O.S. Individual (PDF)":
            os_ids = df_os["ID"].tolist()
            os_escolhida = st.selectbox("Selecione o ID da O.S.", os_ids)
            linha_os = df_os[df_os["ID"] == os_escolhida].iloc[0]
            
            st.markdown("### 📄 Pré-visualização da O.S.")
            st.dataframe(pd.DataFrame([linha_os]), use_container_width=True)
            
            if HAS_PDF_LIBS:
                pdf_bytes = gerar_pdf_os(linha_os)
                if pdf_bytes:
                    st.download_button(
                        label=f"📥 Baixar O.S. #{os_escolhida} em PDF",
                        data=pdf_bytes,
                        file_name=f"OS_{os_escolhida}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.warning("Biblioteca ReportLab não instalada para geração de PDF em formato oficial.")
        
        else:
            st.markdown("### 📊 Relatório Geral de Ordens de Serviço")
            st.dataframe(df_os, use_container_width=True)
            
            st.markdown("""
                <div class="no-print">
                    <p style="color: #00ffaa; font-size: 14px;">💡 Dica: Para imprimir o relatório geral completo, utilize o botão abaixo ou pressione <b>Ctrl + P</b> no seu navegador.</p>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("🖨️ Imprimir Relatório Geral", use_container_width=True):
                components.html("""
                    <script>
                        window.print();
                    </script>
                """, height=0)

# ==============================================================================
# 4. ABA: GESTÃO DE CONFORMIDADE DE FORMULÁRIOS (FMS)
# ==============================================================================
elif menu_escolhido == "📅 Gestão de Conformidade de Formulários (FMs)":
    st.markdown("## 📅 Gestão de Conformidade de Formulários (FMs)")
    
    if os.path.exists(ARQUIVO_FMS):
        df_fms = pd.read_csv(ARQUIVO_FMS, dtype=str)
    else:
        df_fms = pd.DataFrame(columns=["FM", "Data_Realizada", "Periodo", "Dias_Prazo"])
        
    with st.form("form_fms"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            fm_nome = st.text_input("Nome do FM / Formulário")
        with col2:
            data_realizada = st.date_input("Data Realizada", value=datetime.today())
        with col3:
            periodo = st.selectbox("Período", ["Diário", "Semanal", "Mensal", "Anual"])
        with col4:
            dias_prazo = st.number_input("Prazo (Dias)", min_value=1, value=30, step=1)
            
        salvar_fm = st.form_submit_button("Registrar / Atualizar FM", use_container_width=True)
        if salvar_fm:
            if fm_nome:
                nova_linha_fm = {
                    "FM": fm_nome,
                    "Data_Realizada": str(data_realizada),
                    "Periodo": periodo,
                    "Dias_Prazo": str(dias_prazo)
                }
                df_fms = pd.concat([df_fms, pd.DataFrame([nova_linha_fm])], ignore_index=True)
                df_fms.to_csv(ARQUIVO_FMS, index=False)
                st.success(f"Formulário {fm_nome} registrado com sucesso!")
                st.rerun()
                
    st.markdown("### 📊 Painel de Prazo e Status dos FMs")
    if not df_fms.empty:
        # Cálculo dos dias restantes
        hoje = datetime.today().date()
        status_lista = []
        dias_restantes_lista = []
        
        for idx, row in df_fms.iterrows():
            try:
                dt_real = datetime.strptime(row["Data_Realizada"], "%Y-%m-%d").date()
                prazo = int(row["Dias_Prazo"])
                vencimento = dt_real + timedelta(days=prazo)
                dias_rest = (vencimento - hoje).days
                dias_restantes_lista.append(dias_rest)
                
                if dias_rest < 0:
                    status_lista.append("Vencido")
                elif dias_rest <= 5:
                    status_lista.append("Próximo ao Vencimento")
                else:
                    status_lista.append("Em Dia")
            except Exception:
                dias_restantes_lista.append(0)
                status_lista.append("Erro")
                
        df_fms["Dias_Restantes"] = dias_restantes_lista
        df_fms["Status_FM"] = status_lista
        
        st.dataframe(df_fms, use_container_width=True)
        
        # Gráfico cruzando Prazo e Dias Restantes (Conforme solicitado)
        fig_fm = px.scatter(
            df_fms, 
            x="Dias_Prazo", 
            y="Dias_Restantes", 
            color="Status_FM",
            hover_data=["FM", "Data_Realizada"],
            title="Relação entre Prazo Estabelecido e Dias Restantes por Formulário",
            template="plotly_dark"
        )
        fig_fm.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_fm, use_container_width=True)
    else:
        st.info("Nenhum formulário cadastrado no momento.")

# ==============================================================================
# 5. ABA: SOLICITAÇÕES DE COMPRAS (MANTIDO INTACTO)
# ==============================================================================
elif menu_escolhido == "🛒 Solicitações de Compras":
    st.markdown("## 🛒 Solicitações de Compras")
    if os.path.exists(ARQUIVO_COMPRAS):
        df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
    else:
        df_c = pd.DataFrame(columns=["ID_Compra", "Data_Solicitacao", "Solicitante", "Setor", "Categoria", "Item", "Quantidade", "Observacoes", "Status"])
        
    with st.form("form_compras", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            solic_c = st.text_input("Solicitante *", value=st.session_state.usuario_logado)
            setor_c = st.selectbox("Setor *", ["Manutenção", "Operação", "Administrativo", "Segurança", "TI", "Qualidade"])
            categoria_c = st.selectbox("Categoria", ["Peças", "Ferramentas", "EPI", "Material de Escritório", "Outros"])
        with col2:
            item_c = st.text_input("Item Solicitado *")
            qtd_c = st.number_input("Quantidade", min_value=1, value=1, step=1)
        obs_c = st.text_area("Observações / Justificativa")
        
        sub_c = st.form_submit_button("Enviar Solicitação de Compra", use_container_width=True)
        if sub_c:
            if not item_c:
                st.error("Informe o item solicitado.")
            else:
                novo_id_c = int(df_c["ID_Compra"].max() + 1) if not df_c.empty and df_c["ID_Compra"].max() > 0 else 1
                nova_compra = {
                    "ID_Compra": novo_id_c,
                    "Data_Solicitacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Solicitante": solic_c,
                    "Setor": setor_c,
                    "Categoria": categoria_c,
                    "Item": item_c,
                    "Quantidade": str(qtd_c),
                    "Observacoes": obs_c,
                    "Status": "Pendente",
                    "Orcamento_Assinado": "None",
                    "NF_Anexada": "None",
                    "Boleto_Anexado": "None",
                    "Assinado_Por": "None"
                }
                df_c = pd.concat([df_c, pd.DataFrame([nova_compra])], ignore_index=True)
                df_c.to_csv(ARQUIVO_COMPRAS, index=False)
                st.success(f"Solicitação de Compra #{novo_id_c} cadastrada com sucesso!")
                
    st.markdown("### 📋 Lista de Solicitações de Compras")
    if not df_c.empty:
        st.dataframe(df_c[["ID_Compra", "Data_Solicitacao", "Solicitante", "Setor", "Item", "Quantidade", "Status"]], use_container_width=True)
    else:
        st.info("Nenhuma solicitação de compra cadastrada.")

# ==============================================================================
# 6. ABA: PAINEL DE ASSINATURAS (NF E BOLETO) (MANTIDO INTACTO)
# ==============================================================================
elif menu_escolhido == "✍️ Painel de Assinaturas (NF e Boleto)":
    st.markdown("## ✍️ Painel de Assinaturas (NF e Boleto)")
    if os.path.exists(ARQUIVO_COMPRAS):
        df_c = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
    else:
        df_c = pd.DataFrame()
        
    if df_c.empty:
        st.info("Nenhuma compra ou documento para assinatura registrado.")
    else:
        st.dataframe(df_c[["ID_Compra", "Item", "Solicitante", "Status", "Orcamento_Assinado", "NF_Anexada", "Boleto_Anexado"]], use_container_width=True)
        
        comp_ids = df_c["ID_Compra"].tolist()
        comp_sel = st.selectbox("Selecione a Compra / Documento para gerenciar anexos e assinaturas", comp_ids)
        if comp_sel:
            row_comp = df_c[df_c["ID_Compra"] == comp_sel].iloc[0]
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### 📄 Documentos Anexados")
                exibir_documento(row_comp.get("Orcamento_Assinado", ""), "Orçamento / Proposta")
                exibir_documento(row_comp.get("NF_Anexada", ""), "Nota Fiscal")
                exibir_documento(row_comp.get("Boleto_Anexado", ""), "Boleto")
            with col_b:
                st.markdown("#### ✍️ Ações de Assinatura")
                novo_status_ass = st.selectbox("Atualizar Status do Pagamento / Aprovação", ["Pendente", "Aprovado", "Assinado", "Pago", "Rejeitado"], index=0)
                if st.button("Atualizar Status da Assinatura"):
                    idx_c = df_c[df_c["ID_Compra"] == comp_sel].index[0]
                    df_c.at[idx_c, "Status"] = novo_status_ass
                    df_c.at[idx_c, "Assinado_Por"] = st.session_state.usuario_logado
                    df_c.to_csv(ARQUIVO_COMPRAS, index=False)
                    st.success("Status atualizado com sucesso!")
                    st.rerun()

# ==============================================================================
# 7. ABA: DASHBOARD (COM FILTROS GLOBAIS E GRÁFICOS POWER BI SEM FUNDO)
# ==============================================================================
elif menu_escolhido == "📊 Dashboard":
    st.markdown("## 📊 Dashboard Executivo (Power BI Style)")
    
    df_os = carregar_banco_os()
    if os.path.exists(ARQUIVO_COMPRAS):
        df_compras = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
    else:
        df_compras = pd.DataFrame(columns=["ID_Compra", "Data_Solicitacao", "Setor", "Status"])
        
    # --- FILTROS GLOBAIS DE DIA, MÊS E ANO ---
    st.markdown("### 🎛️ Filtros Globais")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    # Tratamento de datas O.S. para filtros
    if not df_os.empty and "Data_Criacao" in df_os.columns:
        df_os["Data_Parsed"] = pd.to_datetime(df_os["Data_Criacao"], errors="coerce")
        anos_disponiveis = sorted(df_os["Data_Parsed"].dt.year.dropna().unique().astype(int).tolist())
    else:
        anos_disponiveis = []
        
    with col_f1:
        filtro_ano = st.selectbox("Ano", ["Todos"] + [str(a) for a in anos_disponiveis])
    with col_f2:
        filtro_mes = st.selectbox("Mês", ["Todos", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
    with col_f3:
        filtro_dia = st.selectbox("Dia", ["Todos"] + [str(d) for d in range(1, 32)])
        
    # Aplicação dos filtros em O.S.
    df_os_filt = df_os.copy()
    if not df_os_filt.empty and "Data_Parsed" in df_os_filt.columns:
        if filtro_ano != "Todos":
            df_os_filt = df_os_filt[df_os_filt["Data_Parsed"].dt.year == int(filtro_ano)]
        if filtro_mes != "Todos":
            df_os_filt = df_os_filt[df_os_filt["Data_Parsed"].dt.month == int(filtro_mes)]
        if filtro_dia != "Todos":
            df_os_filt = df_os_filt[df_os_filt["Data_Parsed"].dt.day == int(filtro_dia)]
            
    # Aplicação dos filtros em Compras
    df_comp_filt = df_compras.copy()
    if not df_comp_filt.empty and "Data_Solicitacao" in df_comp_filt.columns:
        df_comp_filt["Data_Parsed"] = pd.to_datetime(df_comp_filt["Data_Solicitacao"], errors="coerce")
        if filtro_ano != "Todos":
            df_comp_filt = df_comp_filt[df_comp_filt["Data_Parsed"].dt.year == int(filtro_ano)]
        if filtro_mes != "Todos":
            df_comp_filt = df_comp_filt[df_comp_filt["Data_Parsed"].dt.month == int(filtro_mes)]
        if filtro_dia != "Todos":
            df_comp_filt = df_comp_filt[df_comp_filt["Data_Parsed"].dt.day == int(filtro_dia)]
            
    st.markdown("---")
    
    # Separação por dois setores: Compras e O.S. em janelas diferentes ao seu lado
    col_setor_compras, col_setor_os = st.columns(2)
    
    with col_setor_compras:
        st.markdown("### 🛒 Setor: Compras")
        
        if df_comp_filt.empty:
            st.info("Nenhum dado de compras para os filtros selecionados.")
        else:
            # Gráfico 1: Compras por Status (Donut sem fundo estilo Power BI)
            status_comp_counts = df_comp_filt["Status"].value_counts().reset_index()
            status_comp_counts.columns = ["Status", "Quantidade"]
            fig_c1 = px.pie(
                status_comp_counts, 
                names="Status", 
                values="Quantidade", 
                hole=0.5, 
                title="Status das Solicitações de Compras"
            )
            fig_c1.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white"
            )
            st.plotly_chart(fig_c1, use_container_width=True)
            
            # Gráfico 2: Compras por Categoria / Setor (Barra sem fundo estilo Power BI)
            if "Categoria" in df_comp_filt.columns:
                cat_counts = df_comp_filt["Categoria"].value_counts().reset_index()
                cat_counts.columns = ["Categoria", "Total"]
                fig_c2 = px.bar(
                    cat_counts, 
                    x="Categoria", 
                    y="Total", 
                    title="Compras por Categoria",
                    text="Total"
                )
                fig_c2.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig_c2, use_container_width=True)
                
    with col_setor_os:
        st.markdown("### 🔧 Setor: Ordens de Serviço (O.S.)")
        
        if df_os_filt.empty:
            st.info("Nenhuma O.S. encontrada para os filtros selecionados.")
        else:
            # Gráfico 3: O.S. por Status (Pie/Donut sem fundo)
            status_os_counts = df_os_filt["Status"].value_counts().reset_index()
            status_os_counts.columns = ["Status", "Quantidade"]
            fig_o1 = px.pie(
                status_os_counts, 
                names="Status", 
                values="Quantidade", 
                hole=0.5, 
                title="Status das Ordens de Serviço"
            )
            fig_o1.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white"
            )
            st.plotly_chart(fig_o1, use_container_width=True)
            
            # Gráfico 4: O.S. por Prioridade (Barra sem fundo)
            prio_counts = df_os_filt["Prioridade"].value_counts().reset_index()
            prio_counts.columns = ["Prioridade", "Total"]
            fig_o2 = px.bar(
                prio_counts, 
                x="Prioridade", 
                y="Total", 
                title="O.S. por Prioridade",
                text="Total",
                color="Prioridade"
            )
            fig_o2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_o2, use_container_width=True)
            
            # Gráfico 5: O.S. por Tipo de Manutenção (Linha / Área sem fundo)
            tipo_counts = df_os_filt["Tipo_Manutencao"].value_counts().reset_index()
            tipo_counts.columns = ["Tipo", "Total"]
            fig_o3 = px.bar(
                tipo_counts, 
                x="Tipo", 
                y="Total", 
                title="O.S. por Tipo de Manutenção",
                text="Total"
            )
            fig_o3.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_o3, use_container_width=True)
