import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
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

# --- FUNÇÃO PARA GERAR O PDF DA ORDEM DE SERVIÇO ---
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
    style_cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9)
    style_cell_normal = ParagraphStyle('CellNormal', parent=styles['Normal'], fontName='Helvetica', fontSize=9)
    style_cell_center_bold = ParagraphStyle('CellCenterBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1)
    
    elements = []
    
    # 1. Tabela de Cabeçalho (Logo, Título e FM)
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
    
    # 2. Dados de Identificação (Número, Data, Hora)
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
    
    # 3. Tipo e Prioridade
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
    
    # 4. Setor, Solicitante e Equipamento
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
    
    # 5. Seções de Texto: Descrição, Solução, Itens Trocados
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
    elements.append(Spacer(1, 15))
    
    # 6. Assinaturas
    finalizador_val = os_row.get('finalizado_por', '')
    if pd.isna(finalizador_val):
        finalizador_val = ''
        
    ass_data = [
        [
            Paragraph("__________________________________________________<br/><b>Manutenção / Executor</b>", style_cell_center_bold),
            Paragraph("__________________________________________________<br/><b>Solicitante / Operação</b>", style_cell_center_bold)
        ]
    ]
    t_ass = RLTable(ass_data, colWidths=[270, 270])
    t_ass.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_ass)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# --- AUTENTICAÇÃO E SESSÃO ---
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None
if "admin" not in st.session_state:
    st.session_state["admin"] = False
if "permissoes" not in st.session_state:
    st.session_state["permissoes"] = []

df_users_login = pd.read_csv(ARQUIVO_USERS, dtype=str)

if st.session_state["usuario_logado"] is None:
    st.markdown("<h2 style='text-align: center; color: white;'>🔐 Intranet Stang - Login</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("form_login"):
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            submit_login = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit_login:
                usuario_limpo = usuario_input.strip().lower()
                user_match = df_users_login[df_users_login["Usuario"].str.lower() == usuario_limpo]
                
                if not user_match.empty and user_match.iloc[0]["Senha"] == senha_input:
                    st.session_state["usuario_logado"] = user_match.iloc[0]["Usuario"]
                    st.session_state["admin"] = user_match.iloc[0]["Admin"] == "Sim"
                    perms_str = user_match.iloc[0]["Permissoes"]
                    st.session_state["permissoes"] = [p.strip() for p in perms_str.split(",") if p.strip()]
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

# --- MENU LATERAL ---
st.sidebar.markdown(f"👤 **Logado como:** `{st.session_state['usuario_logado']}`")
if st.sidebar.button("🚪 Sair / Trocar Usuário", use_container_width=True):
    st.session_state["usuario_logado"] = None
    st.session_state["admin"] = False
    st.session_state["permissoes"] = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧭 Menu Principal")

menus_disponiveis = TODOS_MENUS if st.session_state["admin"] else [m for m in TODOS_MENUS if m in st.session_state["permissoes"]]
if not menus_disponiveis:
    menus_disponiveis = ["📊 Dashboard"]

menu_selecionado = st.sidebar.radio("Navegação", menus_disponiveis, label_visibility="collapsed")

# ==========================================
# 1. NOVA O.S.
# ==========================================
if menu_selecionado == "📝 Nova O.S.":
    st.markdown("## 📝 Nova Ordem de Serviço")
    
    with st.form("form_nova_os", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            solicitante = st.text_input("Solicitante")
            setor = st.selectbox("Setor", ["Manutenção", "Operação", "Elétrica", "Automação", "Segurança / SMS", "Administrativo"])
            equipamento = st.text_input("Equipamento / Local")
        with col2:
            tipo_manutencao = st.selectbox("Tipo de Manutenção", ["Corretiva", "Preventiva", "Preditiva", "Melhoria"])
            prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Urgente"])
            
        descricao = st.text_area("Descrição do Problema / Serviço Solicitado")
        
        submitted_os = st.form_submit_button("Criar Ordem de Serviço", use_container_width=True)
        if submitted_os:
            if not solicitante or not descricao:
                st.error("Preencha ao menos o Solicitante e a Descrição.")
            else:
                df_os = carregar_banco_os()
                novo_id = int(df_os["ID"].max() + 1) if not df_os.empty and df_os["ID"].max() > 0 else 1
                
                nova_linha = {
                    "ID": novo_id,
                    "Data_Criacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Solicitante": solicitante,
                    "Setor": setor,
                    "Equipamento": equipamento,
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
                st.success(f"Ordem de Serviço #{novo_id} criada com sucesso!")

# ==========================================
# 2. GERENCIAR O.S.
# ==========================================
elif menu_selecionado == "📋 Gerenciar O.S.":
    st.markdown("## 📋 Gerenciamento de Ordens de Serviço")
    df_os = carregar_banco_os()
    
    if df_os.empty:
        st.info("Nenhuma O.S. cadastrada.")
    else:
        filtro_status = st.selectbox("Filtrar por Status", ["Todas", "Aberta", "Em Andamento", "Finalizada"])
        if filtro_status != "Todas":
            df_os = df_os[df_os["Status"] == filtro_status]
            
        st.dataframe(df_os, use_container_width=True)
        
        st.markdown("### Atualizar O.S.")
        os_ids = df_os["ID"].tolist()
        if os_ids:
            os_selecionada = st.selectbox("Selecione o ID da O.S. para Editar / Finalizar", os_ids)
            row_os = df_os[df_os["ID"] == os_selecionada].iloc[0]
            
            with st.form("form_atualiza_os"):
                novo_status = st.selectbox("Status", ["Aberta", "Em Andamento", "Finalizada"], index=["Aberta", "Em Andamento", "Finalizada"].index(row_os["Status"]) if row_os["Status"] in ["Aberta", "Em Andamento", "Finalizada"] else 0)
                solucao = st.text_area("Descrição da Solução", value=str(row_os["Solucao"]) if pd.notna(row_os["Solucao"]) else "")
                itens_trocados = st.text_area("Itens Trocados", value=str(row_os["Itens_Trocados"]) if pd.notna(row_os["Itens_Trocados"]) else "")
                finalizado_por = st.text_input("Finalizado / Executado por", value=str(row_os["finalizado_por"]) if pd.notna(row_os["finalizado_por"]) else "")
                
                btn_salvar_os = st.form_submit_button("Salvar Alterações", use_container_width=True)
                if btn_salvar_os:
                    df_os.loc[df_os["ID"] == os_selecionada, "Status"] = novo_status
                    df_os.loc[df_os["ID"] == os_selecionada, "Solucao"] = solucao
                    df_os.loc[df_os["ID"] == os_selecionada, "Itens_Trocados"] = itens_trocados
                    df_os.loc[df_os["ID"] == os_selecionada, "finalizado_por"] = finalizado_por
                    if novo_status == "Finalizada" and (pd.isna(row_os["Data_Termino"]) or row_os["Data_Termino"] == ""):
                        df_os.loc[df_os["ID"] == os_selecionada, "Data_Termino"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    df_os.to_csv(ARQUIVO_OS, index=False)
                    st.success(f"O.S. #{os_selecionada} atualizada com sucesso!")
                    st.rerun()

# ==========================================
# 3. EMISSÃO E RELATÓRIOS DE O.S.
# ==========================================
elif menu_selecionado == "🖨️ Emissão e Relatórios de O.S.":
    st.markdown("## 🖨️ Emissão e Relatórios de O.S.")
    df_os = carregar_banco_os()
    
    if df_os.empty:
        st.info("Nenhuma O.S. cadastrada para emissão.")
    else:
        aba_emissao, aba_rel_geral = st.tabs(["📄 Emitir O.S. Individual", "📊 Relatório Geral de O.S."])
        
        with aba_emissao:
            os_ids = df_os["ID"].tolist()
            os_id_escolhida = st.selectbox("Selecione a O.S. para Visualizar/Imprimir", os_ids)
            
            if os_id_escolhida:
                row_os = df_os[df_os["ID"] == os_id_escolhida].iloc[0]
                
                st.markdown(f"""
                ### Ordem de Serviço #{row_os['ID']}
                - **Data:** {row_os['Data_Criacao']} | **Setor:** {row_os['Setor']} | **Solicitante:** {row_os['Solicitante']}
                - **Tipo:** {row_os['Tipo_Manutencao']} | **Prioridade:** {row_os['Prioridade']} | **Status:** {row_os['Status']}
                - **Equipamento:** {row_os['Equipamento']}
                - **Descrição:** {row_os['Descricao']}
                - **Solução:** {row_os['Solucao']}
                - **Itens Trocados:** {row_os['Itens_Trocados']}
                - **Executor:** {row_os['finalizado_por']}
                """)
                
                if HAS_PDF_LIBS:
                    pdf_bytes = gerar_pdf_os(row_os)
                    if pdf_bytes:
                        st.download_button(
                            label="📥 Baixar O.S. em PDF (FM 12)",
                            data=pdf_bytes,
                            file_name=f"OS_{row_os['ID']}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.warning("Biblioteca ReportLab não instalada para geração avançada de PDF.")
                    
        with aba_rel_geral:
            st.markdown("### 📊 Relatório Geral de Ordens de Serviço")
            st.dataframe(df_os, use_container_width=True)
            
            # Opção de exportação para CSV/Excel do relatório geral
            csv_geral = df_os.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Relatório Geral em CSV",
                data=csv_geral,
                file_name=f"relatorio_geral_os_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

# ==========================================
# 4. FORMULÁRIOS E PRAZOS (FMS)
# ==========================================
elif menu_selecionado == "📅 Formulários e Prazos (FMs)":
    st.markdown("## 📅 Gestão de Conformidade de Formulários (FMs)")
    
    if os.path.exists(ARQUIVO_FMS):
        df_fms = pd.read_csv(ARQUIVO_FMS)
    else:
        df_fms = pd.DataFrame(columns=["FM", "Data_Realizada", "Periodo", "Dias_Prazo"])
        
    with st.form("form_fm"):
        col1, col2, col3 = st.columns(3)
        with col1:
            fm_nome = st.text_input("Nome/Código do FM (ex: FM 01)")
        with col2:
            data_realizada = st.date_input("Data Realizada", value=datetime.today())
        with col3:
            periodo = st.selectbox("Periodicidade", ["Diário", "Semanal", "Mensal", "Anual"])
            dias_prazo = st.number_input("Prazo Limite (Dias)", min_value=1, value=30)
            
        btn_add_fm = st.form_submit_button("Registrar / Atualizar FM", use_container_width=True)
        if btn_add_fm and fm_nome:
            nova_fm = pd.DataFrame([{
                "FM": fm_nome,
                "Data_Realizada": str(data_realizada),
                "Periodo": periodo,
                "Dias_Prazo": int(dias_prazo)
            }])
            df_fms = pd.concat([df_fms, nova_fm], ignore_index=True)
            df_fms.to_csv(ARQUIVO_FMS, index=False)
            st.success(f"Formulário {fm_nome} registrado com sucesso!")
            st.rerun()
            
    st.markdown("---")
    st.markdown("### 📊 Painel de Prazos e Status dos FMs")
    if not df_fms.empty:
        # Calcular dias restantes
        hoje = datetime.today().date()
        dias_restantes_list = []
        for idx, row in df_fms.iterrows():
            dt_real = datetime.strptime(str(row["Data_Realizada"]), "%Y-%m-%d").date()
            prazo = int(row["Dias_Prazo"])
            vencimento = dt_real + timedelta(days=prazo)
            restante = (vencimento - hoje).days
            dias_restantes_list.append(restante)
            
        df_fms["Dias_Restantes"] = dias_restantes_list
        
        st.dataframe(df_fms, use_container_width=True)
        
        # Gráfico entre prazo e quantos dias faltam para cada FM
        fig_fm = px.bar(
            df_fms, 
            x="FM", 
            y="Dias_Restantes", 
            color="Dias_Restantes",
            title="Dias Restantes por Formulário (FM)",
            labels={"Dias_Restantes": "Dias Restantes", "FM": "Formulário"},
            color_continuous_scale="Tealgrn"
        )
        fig_fm.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        st.plotly_chart(fig_fm, use_container_width=True)
    else:
        st.info("Nenhum formulário registrado ainda.")

# ==========================================
# 5. SOLICITAÇÕES DE COMPRAS
# ==========================================
elif menu_selecionado == "🛒 Solicitações de Compras":
    st.markdown("## 🛒 Solicitações de Compras")
    
    if os.path.exists(ARQUIVO_COMPRAS):
        df_compras = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
    else:
        df_compras = pd.DataFrame(columns=[
            "ID_Compra", "Data_Solicitacao", "Solicitante", "Setor", "Categoria", 
            "Item", "Quantidade", "Observacoes", "Status", "Orcamento_Assinado",
            "NF_Anexada", "Boleto_Anexado", "Assinado_Por"
        ])
        
    with st.form("form_nova_compra", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            solicitante_c = st.text_input("Solicitante")
            setor_c = st.selectbox("Setor", ["Manutenção", "Operação", "Elétrica", "Automação", "Segurança / SMS", "Administrativo"])
            categoria_c = st.selectbox("Categoria", ["Peças", "Ferramentas", "Serviços", "EPIs", "Escritório", "Outros"])
        with col2:
            item_c = st.text_input("Item / Descrição")
            qtd_c = st.number_input("Quantidade", min_value=1, value=1)
            obs_c = st.text_area("Observações")
            
        btn_comprar = st.form_submit_button("Enviar Solicitação de Compra", use_container_width=True)
        if btn_comprar:
            if not solicitante_c or not item_c:
                st.error("Preencha o Solicitante e o Item.")
            else:
                novo_id_c = int(df_compras["ID_Compra"].max() + 1) if not df_compras.empty and df_compras["ID_Compra"].str.isnumeric().any() else 1
                nova_c = {
                    "ID_Compra": novo_id_c,
                    "Data_Solicitacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Solicitante": solicitante_c,
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
                df_compras = pd.concat([df_compras, pd.DataFrame([nova_c])], ignore_index=True)
                df_compras.to_csv(ARQUIVO_COMPRAS, index=False)
                st.success(f"Solicitação de Compra #{novo_id_c} criada com sucesso!")
                st.rerun()
                
    st.markdown("---")
    st.markdown("### 📋 Acompanhamento de Compras")
    if not df_compras.empty:
        st.dataframe(df_compras, use_container_width=True)
    else:
        st.info("Nenhuma solicitação de compra registrada.")

# ==========================================
# 6. DASHBOARD
# ==========================================
elif menu_selecionado == "📊 Dashboard":
    st.markdown("## 📊 Dashboard Executivo (Power BI Style)")
    
    df_os = carregar_banco_os()
    if os.path.exists(ARQUIVO_COMPRAS):
        df_compras = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
    else:
        df_compras = pd.DataFrame(columns=["ID_Compra", "Data_Solicitacao", "Setor", "Categoria", "Status"])

    # --- FILTROS GLOBAIS DE DIA, MÊS E ANO ---
    st.markdown("### 🔍 Filtros Globais")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        filtro_ano = st.selectbox("Ano", ["Todos", "2026", "2025", "2024"])
    with col_f2:
        filtro_mes = st.selectbox("Mês", ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])
    with col_f3:
        filtro_dia = st.selectbox("Dia", ["Todos"] + [str(i).zfill(2) for i in range(1, 32)])

    # Aplicar filtros nas O.S.
    if not df_os.empty and "Data_Criacao" in df_os.columns:
        df_os_filtrado = df_os.copy()
        if filtro_ano != "Todos":
            df_os_filtrado = df_os_filtrado[df_os_filtrado["Data_Criacao"].str.startswith(filtro_ano)]
        if filtro_mes != "Todos":
            df_os_filtrado = df_os_filtrado[df_os_filtrado["Data_Criacao"].str.contains(f"-{filtro_mes}-", na=False)]
        if filtro_dia != "Todos":
            df_os_filtrado = df_os_filtrado[df_os_filtrado["Data_Criacao"].str.contains(f"-{filtro_dia} ", na=False)]
    else:
        df_os_filtrado = df_os

    # Aplicar filtros nas Compras
    if not df_compras.empty and "Data_Solicitacao" in df_compras.columns:
        df_compras_filtrado = df_compras.copy()
        if filtro_ano != "Todos":
            df_compras_filtrado = df_compras_filtrado[df_compras_filtrado["Data_Solicitacao"].str.startswith(filtro_ano)]
        if filtro_mes != "Todos":
            df_compras_filtrado = df_compras_filtrado[df_compras_filtrado["Data_Solicitacao"].str.contains(f"-{filtro_mes}-", na=False)]
        if filtro_dia != "Todos":
            df_compras_filtrado = df_compras_filtrado[df_compras_filtrado["Data_Solicitacao"].str.contains(f"-{filtro_dia} ", na=False)]
    else:
        df_compras_filtrado = df_compras

    st.markdown("---")

    # Layout separado por dois setores (Compras e O.S.) em janelas/colunas diferentes ao lado
    col_setor_compras, col_setor_os = st.columns(2)

    with col_setor_compras:
        st.markdown("### 🛒 Setor: Compras")
        
        if not df_compras_filtrado.empty:
            # Gráfico 1 de Compras: Status das Compras
            fig_c1 = px.pie(df_compras_filtrado, names="Status", title="Status das Solicitações de Compras", hole=0.4)
            fig_c1.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                margin=dict(t=30, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_c1, use_container_width=True)
            
            # Gráfico 2 de Compras: Compras por Categoria
            if "Categoria" in df_compras_filtrado.columns:
                fig_c2 = px.bar(df_compras_filtrado["Categoria"].value_counts().reset_index(), x="index", y="Categoria", title="Volume por Categoria", labels={"index": "Categoria", "Categoria": "Total"})
                fig_c2.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    margin=dict(t=30, b=10, l=10, r=10)
                )
                st.plotly_chart(fig_c2, use_container_width=True)
        else:
            st.info("Sem dados de compras para os filtros selecionados.")

    with col_setor_os:
        st.markdown("### 🔧 Setor: Ordens de Serviço (O.S.)")
        
        if not df_os_filtrado.empty:
            # Gráfico 1 de O.S.: O.S. por Status
            fig_os1 = px.pie(df_os_filtrado, names="Status", title="Distribuição de Status de O.S.", hole=0.4)
            fig_os1.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                margin=dict(t=30, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_os1, use_container_width=True)
            
            # Gráfico 2 de O.S.: O.S. por Prioridade
            if "Prioridade" in df_os_filtrado.columns:
                fig_os2 = px.bar(df_os_filtrado["Prioridade"].value_counts().reset_index(), x="index", y="Prioridade", title="O.S. por Prioridade", labels={"index": "Prioridade", "Prioridade": "Total"})
                fig_os2.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    margin=dict(t=30, b=10, l=10, r=10)
                )
                st.plotly_chart(fig_os2, use_container_width=True)
                
            # Gráfico 3 de O.S.: Tipo de Manutenção
            if "Tipo_Manutencao" in df_os_filtrado.columns:
                fig_os3 = px.bar(df_os_filtrado["Tipo_Manutencao"].value_counts().reset_index(), x="index", y="Tipo_Manutencao", title="Tipos de Manutenção", labels={"index": "Tipo", "Tipo_Manutencao": "Total"}, color="index")
                fig_os3.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    margin=dict(t=30, b=10, l=10, r=10)
                )
                st.plotly_chart(fig_os3, use_container_width=True)
        else:
            st.info("Sem dados de O.S. para os filtros selecionados.")
