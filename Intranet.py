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
    
    # Cabeçalho
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
    
    # Info
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
    
    # Prioriadade
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
    
    # Setor
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
    
    # Textos
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
    
    # Assinaturas
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

def gerar_html_os_impressao(os_row):
    equipamento_val = os_row['Equipamento'] if pd.notna(os_row.get('Equipamento')) else 'N/A'
    solucao_val = os_row['Solucao'] if pd.notna(os_row.get('Solucao')) else ''
    itens_val = os_row['Itens_Trocados'] if pd.notna(os_row.get('Itens_Trocados')) else ''
    finalizador_val = os_row['finalizado_por'] if pd.notna(os_row.get('finalizado_por')) else ''
    data_criacao_val = str(os_row['Data_Criacao'])
    
    logo_base64 = ""
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as img_file:
            logo_base64 = base64.b64encode(img_file.read()).decode()

    return f"""
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
        <button class="btn-imprimir" onclick="window.print()">🖨️ Imprimir O.S.</button>
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
                <td style="text-align: center; width: 50%;">__________________________________________________<br><b>Responsável pelo Serviço ({finalizador_val})</b></td>
            </tr>
        </table>
    </div>
</body>
</html>
"""

def carimbar_assinatura_no_documento(caminho_doc, caminho_assinatura_png, nome_usuario):
    if not os.path.exists(caminho_doc) or not os.path.exists(caminho_assinatura_png):
        return False
    
    ext = os.path.splitext(caminho_doc)[1].lower()
    if ext == ".pdf" and HAS_PDF_LIBS:
        try:
            reader = PdfReader(caminho_doc)
            writer = PdfWriter()
            num_pages = len(reader.pages)
            
            ultima_pagina = reader.pages[-1]
            largura = float(ultima_pagina.mediabox.width)
            altura = float(ultima_pagina.mediabox.height)
            
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(largura, altura))
            
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
            
            ass_width = int(doc_img.width * 0.25)
            w_percent = (ass_width / float(ass_img.width))
            ass_height = int((float(ass_img.height) * float(w_percent)))
            ass_img = ass_img.resize((ass_width, ass_height), Image.Resampling.LANCZOS)
            
            pos_x = doc_img.width - ass_width - 20
            pos_y = doc_img.height - ass_height - 20
            
            doc_img.paste(ass_img, (pos_x, pos_y), ass_img)
            doc_img.convert("RGB").save(caminho_doc)
            return True
        except Exception as e:
            st.error(f"Erro ao aplicar carimbo na Imagem: {e}")
            return False
    return True

def enviar_email_real(destinatario, assunto, corpo, anexos, config):
    try:
        remetente = config.get("Email_Remetente", "")
        senha_app = config.get("Senha_App", "")
        servidor_smtp = config.get("Servidor_SMTP", "smtp.gmail.com")
        porta_smtp = int(config.get("Porta_SMTP", "587"))
        nome_remetente = config.get("Nome_Remetente", "Intranet Stang")
        
        if not remetente or not senha_app:
            return False, "E-mail remetente ou Senha de App não configurados para este usuário na tela de Login!"
            
        msg = MIMEMultipart()
        msg['From'] = f"{nome_remetente} <{remetente}>"
        msg['To'] = destinatario
        msg['Subject'] = assunto
        
        msg.attach(MIMEText(corpo, 'plain'))
        
        for file_item in anexos:
            if isinstance(file_item, tuple):
                file_bytes, filename = file_item
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file_bytes)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {filename}")
                msg.attach(part)
            elif file_item and str(file_item) != "None" and os.path.exists(str(file_item)):
                with open(file_item, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                filename = os.path.basename(file_item)
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

# --- SISTEMA DE AUTENTICAÇÃO ---
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
                            
        with st.expander("🔑 Gerenciar Usuários, Assinatura Digital e E-mail"):
            senha_master_input = st.text_input("Insira a Senha Master ou Senha de Administrador", type="password", key="master_unlock")
            
            df_users_check_master = pd.read_csv(ARQUIVO_USERS, dtype=str)
            admins_senhas = df_users_check_master[df_users_check_master["Admin"] == "Sim"]["Senha"].tolist()
            
            libera_gestao = (senha_master_input == "master") or (senha_master_input in admins_senhas and senha_master_input != "")
            
            if libera_gestao:
                st.success("Painel de gestão de usuários liberado:")
                
                aba_ges1, aba_ges2 = st.tabs(["➕ Cadastrar Novo Usuário", "✏️ Editar / ✍️ Assinatura PNG / 📧 Config. E-mail / 🗑️ Excluir"])
                
                with aba_ges1:
                    with st.form("form_gestao_login"):
                        st.markdown("<b>Novo Usuário a Cadastrar:</b>", unsafe_allow_html=True)
                        n_login = st.text_input("Login do Novo Usuário").strip()
                        n_senha = st.text_input("Senha do Novo Usuário", type="password")
                        n_val = st.selectbox("Validade", ["Vitalício", "Definir Data Limite"])
                        
                        n_data = datetime.now().date() + timedelta(days=30)
                        if n_val == "Definir Data Limite":
                            n_data = st.date_input("Data Limite de Acesso")
                            
                        n_admin_opt = st.selectbox("Perfil de Administrador", ["Não", "Sim"])
                            
                        st.markdown("<b>Permissões de Acesso aos Menus:</b>", unsafe_allow_html=True)
                        n_permissoes = st.multiselect(
                            "Selecione as opções que este usuário poderá acessar:",
                            options=TODOS_MENUS,
                            default=["📝 Nova O.S.", "🛒 Solicitações de Compras"]
                        )
                        
                        st.markdown("---")
                        st.markdown("<b>📧 Configuração Individual de E-mail (SMTP):</b>", unsafe_allow_html=True)
                        n_email = st.text_input("E-mail do Usuário", value="")
                        n_senha_app = st.text_input("Senha de App / Token SMTP", type="password", key="n_senha_app")
                        c_smtp1, c_smtp2 = st.columns(2)
                        n_servidor_smtp = c_smtp1.text_input("Servidor SMTP", value="smtp.gmail.com")
                        n_porta_smtp = c_smtp2.text_input("Porta SMTP", value="587")
                            
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
                                        "Usuario": n_login, "Senha": n_senha, "Validade": val_str,
                                        "Permissoes": perm_str, "Admin": n_admin_opt,
                                        "Assinatura_PNG": "None", "Email_Usuario": n_email,
                                        "Senha_App_Email": n_senha_app, "Servidor_SMTP": n_servidor_smtp,
                                        "Porta_SMTP": n_porta_smtp
                                    }
                                    df_u = pd.concat([df_u, pd.DataFrame([novo_reg])], ignore_index=True)
                                    df_u.to_csv(ARQUIVO_USERS, index=False)
                                    st.success(f"Usuário '{n_login}' cadastrado com sucesso!")
                                    st.rerun()

                with aba_ges2:
                    df_u_atual = pd.read_csv(ARQUIVO_USERS, dtype=str)
                    st.dataframe(df_u_atual[["Usuario", "Email_Usuario", "Validade", "Admin", "Assinatura_PNG"]], use_container_width=True)
                    
                    lista_usuarios_edit = df_u_atual["Usuario"].tolist()
                    if lista_usuarios_edit:
                        st.markdown("---")
                        user_selecionado = st.selectbox("Selecione o usuário para Editar / Configurar", lista_usuarios_edit)
                        row_u_edit = df_u_atual[df_u_atual["Usuario"] == user_selecionado].iloc[0]
                        
                        with st.form("form_editar_usuario"):
                            st.subheader(f"Editando Usuário: {user_selecionado}")
                            edit_senha = st.text_input("Nova Senha", value=str(row_u_edit["Senha"]), type="password")
                            
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
                                edit_data = st.date_input("Nova Data Limite", value=edit_data)
                                
                            admin_atual_str = str(row_u_edit.get("Admin", "Não"))
                            edit_admin_opt = st.selectbox("Perfil de Administrador", ["Não", "Sim"], index=0 if admin_atual_str != "Sim" else 1)
                                
                            perm_atuais_list = [p.strip() for p in str(row_u_edit["Permissoes"]).split(",") if p.strip() in TODOS_MENUS]
                            edit_permissoes = st.multiselect(
                                "Permissões de Acesso:",
                                options=TODOS_MENUS,
                                default=perm_atuais_list
                            )
                            
                            st.markdown("---")
                            st.markdown("<b>📧 Configuração Individual de E-mail (SMTP):</b>", unsafe_allow_html=True)
                            edit_email = st.text_input("E-mail do Usuário", value=str(row_u_edit.get("Email_Usuario", "")))
                            edit_senha_app = st.text_input("Senha de App / Token SMTP", value=str(row_u_edit.get("Senha_App_Email", "")), type="password")
                            c_smtp_e1, c_smtp_e2 = st.columns(2)
                            edit_serv_smtp = c_smtp_e1.text_input("Servidor SMTP", value=str(row_u_edit.get("Servidor_SMTP", "smtp.gmail.com")))
                            edit_porta_smtp = c_smtp_e2.text_input("Porta SMTP", value=str(row_u_edit.get("Porta_SMTP", "587")))
                            
                            st.markdown("---")
                            st.markdown("<b>✍️ Assinatura Digital (PNG transparente)</b>", unsafe_allow_html=True)
                            ass_atual_png = str(row_u_edit.get("Assinatura_PNG", "None"))
                            if ass_atual_png != "None" and os.path.exists(ass_atual_png):
                                st.image(ass_atual_png, width=200, caption="Assinatura Cadastrada Atual")
                            
                            arquivo_nova_ass = st.file_uploader("Fazer upload de nova assinatura (.png, .jpg)", type=['png', 'jpg', 'jpeg'], key="up_ass_png")
                            
                            btn_salvar_edit = st.form_submit_button("Salvar Alterações e Configurações")
                            
                            if btn_salvar_edit:
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Senha"] = edit_senha
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Validade"] = "Vitalício" if edit_val_tipo == "Vitalício" else str(edit_data)
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Admin"] = edit_admin_opt
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Permissoes"] = ",".join(edit_permissoes)
                                
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Email_Usuario"] = edit_email
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Senha_App_Email"] = edit_senha_app
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Servidor_SMTP"] = edit_serv_smtp
                                df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Porta_SMTP"] = edit_porta_smtp
                                
                                if arquivo_nova_ass is not None:
                                    ext_ass = os.path.splitext(arquivo_nova_ass.name)[1]
                                    path_salvar_ass = os.path.join("uploads_assinaturas", f"ass_digital_{user_selecionado}{ext_ass}")
                                    with open(path_salvar_ass, "wb") as f_a:
                                        f_a.write(arquivo_nova_ass.read())
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Assinatura_PNG"] = path_salvar_ass
                                
                                df_u_atual.to_csv(ARQUIVO_USERS, index=False)
                                st.success(f"Alterações de '{user_selecionado}' salvas com sucesso!")
                                st.rerun()

                        if user_selecionado.lower() != "thiagosc":
                            if st.button(f"🗑️ Excluir o usuário '{user_selecionado}'"):
                                df_u_atual = df_u_atual[df_u_atual["Usuario"] != user_selecionado]
                                df_u_atual.to_csv(ARQUIVO_USERS, index=False)
                                st.success("Usuário excluído!")
                                st.rerun()
            else:
                if senha_master_input:
                    st.error("Senha de administrador inválida!")

if st.session_state.autenticado:
    df_u_auth = pd.read_csv(ARQUIVO_USERS, dtype=str)
    try:
        user_auth_row = df_u_auth[df_u_auth["Usuario"] == st.session_state.usuario].iloc[0]
        permissoes_usuario = [p.strip() for p in str(user_auth_row["Permissoes"]).split(",") if p.strip()]
        is_admin_usuario = str(user_auth_row.get("Admin", "Não")) == "Sim"
    except:
        permissoes_usuario = []
        is_admin_usuario = False
    
    st.sidebar.markdown(f"### 👤 Olá, **{st.session_state.usuario}**")
    
    if st.sidebar.button("🚪 Sair / Logout", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario = ""
        st.rerun()
        
    st.sidebar.markdown("---")
    
    opcoes_menu = [m for m in TODOS_MENUS if m in permissoes_usuario]
    if not opcoes_menu:
        opcoes_menu = ["Sem Permissões"]
        
    menu = st.sidebar.radio("Navegação do Sistema:", opcoes_menu)
    st.sidebar.markdown("---")
    
    # === REGRAS DE STATUS ===
    def renderizar_cards_status():
        df_os = carregar_banco_os()
        df_compras = pd.read_csv(ARQUIVO_COMPRAS, dtype=str) if os.path.exists(ARQUIVO_COMPRAS) else pd.DataFrame()
        
        pend_os = len(df_os[df_os["Status"].isin(["Pendente", ""])]) if not df_os.empty else 0
        and_os = len(df_os[df_os["Status"] == "Em Andamento"]) if not df_os.empty else 0
        fin_os = len(df_os[df_os["Status"] == "Finalizado"]) if not df_os.empty else 0
        
        pend_comp = len(df_compras[df_compras["Status"].isin(["Nova Solicitação", "Pendente Assinatura Diretor"])]) if not df_compras.empty else 0
        fin_comp = len(df_compras[df_compras["Status"] == "Compra Aprovada/Finalizada"]) if not df_compras.empty else 0

        html_cards = f"""
        <div class="status-card-container">
            <div class="status-card"><div class="status-card-title">O.S. Pendentes</div><div class="status-card-value badge-danger">🚨 {pend_os}</div></div>
            <div class="status-card"><div class="status-card-title">O.S. Em Andamento</div><div class="status-card-value badge-warning">⏳ {and_os}</div></div>
            <div class="status-card"><div class="status-card-title">O.S. Finalizadas</div><div class="status-card-value badge-success">✅ {fin_os}</div></div>
            <div class="status-card"><div class="status-card-title">Compras Pendentes</div><div class="status-card-value badge-danger">🛒 {pend_comp}</div></div>
            <div class="status-card"><div class="status-card-title">Compras Finalizadas</div><div class="status-card-value badge-success">📦 {fin_comp}</div></div>
        </div>
        """
        st.markdown(html_cards, unsafe_allow_html=True)
    
    # Exibe os status globais no topo de qualquer tela, exceto se for tela que ocupe muito espaço
    if menu not in ["Sem Permissões"]:
        renderizar_cards_status()
        
    # --- TELA 1: NOVA O.S. ---
    if menu == "📝 Nova O.S.":
        st.markdown("# 📝 Emitir Nova Ordem de Serviço")
        with st.form("form_nova_os"):
            col1, col2 = st.columns(2)
            with col1:
                solicitante = st.text_input("Solicitante*", value=st.session_state.usuario)
                setor = st.selectbox("Setor*", ["Operação", "Administrativo", "TI", "Manutenção", "Outros"])
                equipamento = st.text_input("Equipamento (opcional)")
            with col2:
                tipo_manutencao = st.selectbox("Tipo de Manutenção*", ["Preventiva", "Corretiva", "Melhoria"])
                prioridade = st.selectbox("Prioridade*", ["Baixa", "Média", "Alta", "Urgente"])
                data_criacao_input = st.date_input("Data de Criação")
                hora_criacao_input = st.time_input("Hora de Criação", value=datetime.now().time())
                
            descricao = st.text_area("Descrição do Problema*", height=100)
            
            st.markdown("---")
            enviar = st.form_submit_button("Gerar Solicitação e O.S.", use_container_width=True)
            
            if enviar:
                if not solicitante or not descricao:
                    st.error("Preencha todos os campos obrigatórios (*).")
                else:
                    df_os = carregar_banco_os()
                    novo_id = df_os["ID"].max() + 1 if not df_os.empty else 1
                    data_hora_final = f"{data_criacao_input.strftime('%d/%m/%Y')} {hora_criacao_input.strftime('%H:%M')}"
                    nova_os = pd.DataFrame([{
                        "ID": novo_id,
                        "Data_Criacao": data_hora_final,
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
                        "Status": "Pendente"
                    }])
                    df_os = pd.concat([df_os, nova_os], ignore_index=True)
                    df_os.to_csv(ARQUIVO_OS, index=False)
                    st.success(f"✅ O.S. #{novo_id} criada com sucesso e enviada para Pendentes!")
                    st.rerun()

    # --- TELA 2: GERENCIAR O.S. ---
    elif menu == "📋 Gerenciar O.S.":
        st.markdown("# 📋 Gerenciamento de Ordens de Serviço")
        df_os = carregar_banco_os()
        
        if df_os.empty:
            st.info("Nenhuma O.S. cadastrada.")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_status = st.multiselect("Filtrar por Status", ["Pendente", "Em Andamento", "Finalizado"], default=["Pendente", "Em Andamento"])
            with col_f2:
                filtro_id = st.text_input("Buscar por ID da O.S. (deixe vazio para ver todas)")
                
            if filtro_status:
                df_os_view = df_os[df_os["Status"].isin(filtro_status)]
            else:
                df_os_view = df_os
                
            if filtro_id.strip():
                df_os_view = df_os_view[df_os_view["ID"].astype(str) == filtro_id.strip()]
                
            st.dataframe(df_os_view[["ID", "Data_Criacao", "Solicitante", "Setor", "Prioridade", "Status"]], use_container_width=True)
            
            if not df_os_view.empty:
                st.markdown("---")
                id_selecionado = st.selectbox("Selecione o ID da O.S. para Editar/Finalizar:", df_os_view["ID"].tolist())
                os_selecionada = df_os[df_os["ID"] == id_selecionado].iloc[0]
                idx_selecionado = df_os[df_os["ID"] == id_selecionado].index[0]
                
                with st.form("form_edicao_os"):
                    st.markdown(f"#### Editando O.S. #{id_selecionado}")
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        novo_status = st.selectbox("Status", ["Pendente", "Em Andamento", "Finalizado"], index=["Pendente", "Em Andamento", "Finalizado"].index(os_selecionada["Status"]) if os_selecionada["Status"] in ["Pendente", "Em Andamento", "Finalizado"] else 0)
                        edit_prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Urgente"], index=["Baixa", "Média", "Alta", "Urgente"].index(os_selecionada["Prioridade"]) if os_selecionada["Prioridade"] in ["Baixa", "Média", "Alta", "Urgente"] else 0)
                    with col_e2:
                        edit_setor = st.selectbox("Setor", ["Operação", "Administrativo", "TI", "Manutenção", "Outros"], index=["Operação", "Administrativo", "TI", "Manutenção", "Outros"].index(os_selecionada["Setor"]) if os_selecionada["Setor"] in ["Operação", "Administrativo", "TI", "Manutenção", "Outros"] else 0)
                        edit_equipamento = st.text_input("Equipamento", value=str(os_selecionada.get("Equipamento", "")))
                        
                    edit_descricao = st.text_area("Descrição do Problema", value=str(os_selecionada["Descricao"]))
                    edit_solucao = st.text_area("Descrição da Solução Aplicada", value=str(os_selecionada.get("Solucao", "")))
                    edit_itens = st.text_input("Itens Trocados/Utilizados", value=str(os_selecionada.get("Itens_Trocados", "")))
                    
                    finalizado_por = st.text_input("Responsável pela Manutenção / Finalizador", value=str(os_selecionada.get("finalizado_por", st.session_state.usuario)))
                    
                    btn_salvar = st.form_submit_button("Salvar Alterações da O.S.", use_container_width=True)
                    
                    if btn_salvar:
                        df_os.at[idx_selecionado, "Status"] = novo_status
                        df_os.at[idx_selecionado, "Prioridade"] = edit_prioridade
                        df_os.at[idx_selecionado, "Setor"] = edit_setor
                        df_os.at[idx_selecionado, "Equipamento"] = edit_equipamento
                        df_os.at[idx_selecionado, "Descricao"] = edit_descricao
                        df_os.at[idx_selecionado, "Solucao"] = edit_solucao
                        df_os.at[idx_selecionado, "Itens_Trocados"] = edit_itens
                        df_os.at[idx_selecionado, "finalizado_por"] = finalizado_por
                        
                        if novo_status == "Finalizado" and pd.isna(df_os.at[idx_selecionado, "Data_Termino"]) or str(df_os.at[idx_selecionado, "Data_Termino"]) == "":
                            df_os.at[idx_selecionado, "Data_Termino"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                            
                        df_os.to_csv(ARQUIVO_OS, index=False)
                        st.success(f"O.S. #{id_selecionado} atualizada com sucesso!")
                        st.rerun()

    # --- TELA 3: IMPRIMIR / RELATÓRIOS ---
    elif menu == "🖨️ Imprimir O.S.":
        st.markdown("# 🖨️ Emissão e Relatórios de O.S.")
        df_os = carregar_banco_os()
        
        tab_imp1, tab_imp2 = st.tabs(["🖨️ Imprimir O.S. Individual", "📊 Relatório Geral de O.S."])
        
        with tab_imp1:
            if df_os.empty:
                st.info("Nenhuma O.S. cadastrada para imprimir.")
            else:
                lista_ids_impressao = sorted(df_os["ID"].astype(int).tolist(), reverse=True)
                id_imp = st.selectbox("Selecione a O.S. para gerar o espelho de impressão:", lista_ids_impressao)
                
                os_imprimir = df_os[df_os["ID"] == id_imp].iloc[0]
                
                st.markdown("### 📄 Visualização do Documento Físico:")
                html_print = gerar_html_os_impressao(os_imprimir)
                
                with st.expander("👁️ Abrir Visualização / Impressão no Navegador"):
                    components.html(html_print, height=800, scrolling=True)
                
                if HAS_PDF_LIBS:
                    st.markdown("---")
                    st.markdown("### 📥 Gerar Arquivo PDF Oficial (Com Cabeçalho Automático)")
                    pdf_bytes = gerar_pdf_os(os_imprimir)
                    if pdf_bytes:
                        st.download_button(
                            label=f"💾 Baixar PDF da O.S. #{id_imp}",
                            data=pdf_bytes,
                            file_name=f"OS_{id_imp}_Stang.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
        
        with tab_imp2:
            st.markdown("### 📊 Gerar Relatório de O.S.")
            if df_os.empty:
                st.info("Nenhum dado.")
            else:
                c_rel1, c_rel2 = st.columns(2)
                f_rel_setor = c_rel1.selectbox("Filtro Setor", ["Todos"] + df_os["Setor"].unique().tolist())
                f_rel_status = c_rel2.selectbox("Filtro Status", ["Todos"] + df_os["Status"].unique().tolist())
                
                df_f_rep = df_os.copy()
                if f_rel_setor != "Todos":
                    df_f_rep = df_f_rep[df_f_rep["Setor"] == f_rel_setor]
                if f_rel_status != "Todos":
                    df_f_rep = df_f_rep[df_f_rep["Status"] == f_rel_status]
                    
                st.metric("Total de O.S. no Filtro", len(df_f_rep))
                
                if not df_f_rep.empty:
                    st.dataframe(df_f_rep[["ID", "Data_Criacao", "Solicitante", "Setor", "Equipamento", "Tipo_Manutencao", "Prioridade", "Status", "Solucao", "finalizado_por"]], use_container_width=True)
                    
                    # CÓDIGO INSERIDO: Opção de imprimir relatório geral de O.S.
                    linhas_html = ""
                    for _, r in df_f_rep.iterrows():
                        linhas_html += f"<tr><td style='padding:5px; border:1px solid #ddd;'>{r['ID']}</td><td style='padding:5px; border:1px solid #ddd;'>{r.get('Data_Criacao', '')}</td><td style='padding:5px; border:1px solid #ddd;'>{r.get('Solicitante', '')}</td><td style='padding:5px; border:1px solid #ddd;'>{r.get('Setor', '')}</td><td style='padding:5px; border:1px solid #ddd;'>{r.get('Status', '')}</td></tr>"
                    
                    html_relatorio = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            body {{ font-family: Arial, sans-serif; padding: 20px; }}
                            .print-btn {{ background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-bottom: 20px; }}
                            @media print {{ 
                                .print-btn {{ display: none !important; }} 
                                body {{ padding: 0; background-color: #ffffff; color: #000000; }}
                            }}
                        </style>
                    </head>
                    <body>
                        <div style="text-align: center;">
                            <button class="print-btn" onclick="window.print()">🖨️ Imprimir Relatório Geral de O.S.</button>
                        </div>
                        <h3 style="text-align: center;">Relatório Geral de Ordens de Serviço</h3>
                        <p style="text-align: center;"><b>Filtros aplicados:</b> Setor ({f_rel_setor}) | Status ({f_rel_status})</p>
                        <table style="width:100%; border-collapse: collapse; text-align: left; font-size: 12px; border: 1px solid #000;">
                            <tr style="background-color: #e0e0e0;">
                                <th style="padding:8px; border:1px solid #000;">ID</th>
                                <th style="padding:8px; border:1px solid #000;">Data</th>
                                <th style="padding:8px; border:1px solid #000;">Solicitante</th>
                                <th style="padding:8px; border:1px solid #000;">Setor</th>
                                <th style="padding:8px; border:1px solid #000;">Status</th>
                            </tr>
                            {linhas_html}
                        </table>
                    </body>
                    </html>
                    """
                    with st.expander("🖨️ Abrir Visualização e Imprimir Relatório"):
                        components.html(html_relatorio, height=600, scrolling=True)

    # --- TELA 4: FMs (FORMULÁRIOS) ---
    elif menu == "📅 Formulários e Prazos (FMs)":
        st.markdown("# 📅 Gestão de Conformidade de Formulários (FMs)")
        
        df_fms = pd.read_csv(ARQUIVO_FMS, dtype=str) if os.path.exists(ARQUIVO_FMS) else pd.DataFrame(columns=["FM", "Data_Realizada", "Periodo", "Dias_Prazo"])
        
        tab_fm1, tab_fm2, tab_fm3 = st.tabs(["➕ Lançar / Atualizar FM", "📜 Histórico de FMs", "⏰ Painel de Prazos e Status"])
        
        with tab_fm1:
            st.markdown("### Atualizar preenchimento de FM")
            with st.form("form_fm"):
                col_fm1, col_fm2 = st.columns(2)
                fms_disponiveis = [f"FM {str(i).zfill(2)}" for i in range(1, 21)]
                fm_sel = col_fm1.selectbox("Selecione o FM", fms_disponiveis)
                dt_realizada = col_fm2.date_input("Data da última realização / conferência")
                
                periodo_sel = st.selectbox("Período de Validade (Obrigatório)", ["Diário", "Semanal", "Mensal", "Trimestral", "Semestral", "Anual"])
                
                mapa_dias = {"Diário": 1, "Semanal": 7, "Mensal": 30, "Trimestral": 90, "Semestral": 180, "Anual": 365}
                dias_prazo = mapa_dias[periodo_sel]
                
                btn_fm = st.form_submit_button("Lançar / Atualizar", use_container_width=True)
                
                if btn_fm:
                    nova_linha = pd.DataFrame([{
                        "FM": fm_sel,
                        "Data_Realizada": dt_realizada.strftime('%d/%m/%Y'),
                        "Periodo": periodo_sel,
                        "Dias_Prazo": str(dias_prazo)
                    }])
                    df_fms = pd.concat([df_fms, nova_linha], ignore_index=True)
                    df_fms.to_csv(ARQUIVO_FMS, index=False)
                    st.success(f"{fm_sel} lançado com sucesso!")
                    st.rerun()
                    
        with tab_fm2:
            st.dataframe(df_fms, use_container_width=True)
            if not df_fms.empty and is_admin_usuario:
                if st.button("Limpar Histórico de FMs (CUIDADO)"):
                    pd.DataFrame(columns=["FM", "Data_Realizada", "Periodo", "Dias_Prazo"]).to_csv(ARQUIVO_FMS, index=False)
                    st.success("Histórico apagado!")
                    st.rerun()
                    
        with tab_fm3:
            st.markdown("### Status Atual e Vencimentos")
            if df_fms.empty:
                st.info("Nenhum FM cadastrado para cálculo de prazos.")
            else:
                fms_unicos = df_fms.sort_values(by="Data_Realizada", ascending=True).drop_duplicates(subset=["FM"], keep="last").copy()
                
                def calcular_status(row):
                    try:
                        dt_real = datetime.strptime(row["Data_Realizada"], '%d/%m/%Y').date()
                        dt_venc = dt_real + timedelta(days=int(row["Dias_Prazo"]))
                        dias_faltam = (dt_venc - datetime.now().date()).days
                        
                        if dias_faltam < 0:
                            return pd.Series([dt_venc.strftime('%d/%m/%Y'), f"Atrasado ({-dias_faltam} dias)", dias_faltam])
                        elif dias_faltam <= 3:
                            return pd.Series([dt_venc.strftime('%d/%m/%Y'), f"Vence em {dias_faltam} dias (ALERTA)", dias_faltam])
                        else:
                            return pd.Series([dt_venc.strftime('%d/%m/%Y'), f"No prazo ({dias_faltam} dias)", dias_faltam])
                    except Exception as e:
                        return pd.Series(["Erro", "Erro na Data", 0])
                
                fms_unicos[["Proximo_Vencimento", "Status_Prazo", "Dias_Restantes"]] = fms_unicos.apply(calcular_status, axis=1)
                
                st.dataframe(fms_unicos[["FM", "Data_Realizada", "Periodo", "Proximo_Vencimento", "Status_Prazo"]], use_container_width=True)
                
                # CÓDIGO INSERIDO: Gráfico FM x Dias Restantes
                st.markdown("### 📊 Relação: FM x Dias Restantes")
                df_fms_chart = fms_unicos.copy()
                df_fms_chart['Cor'] = df_fms_chart['Dias_Restantes'].apply(lambda x: '#ff4b4b' if x < 0 else '#00ffaa')
                
                fig_fm = px.bar(
                    df_fms_chart, 
                    x='FM', 
                    y='Dias_Restantes', 
                    text='Dias_Restantes',
                    title='Dias Restantes para Vencimento de cada FM'
                )
                fig_fm.update_traces(marker_color=df_fms_chart['Cor'], textposition='outside')
                fig_fm.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color='white')
                )
                st.plotly_chart(fig_fm, use_container_width=True)

    # --- TELA 5: SOLICITAÇÕES DE COMPRAS ---
    elif menu == "🛒 Solicitações de Compras":
        st.markdown("# 🛒 Solicitações de Compras de Materiais")
        
        df_compras = pd.read_csv(ARQUIVO_COMPRAS, dtype=str) if os.path.exists(ARQUIVO_COMPRAS) else pd.DataFrame(columns=[
            "ID_Compra", "Data_Solicitacao", "Solicitante", "Setor", "Categoria", 
            "Item", "Quantidade", "Observacoes", "Status", "Orcamento_Assinado",
            "NF_Anexada", "Boleto_Anexado", "Assinado_Por"
        ])
        
        tab_c1, tab_c2, tab_c3, tab_c4, tab_c5 = st.tabs([
            "📝 Nova Solicitação", 
            "📋 Gerenciar Compras", 
            "📎 Anexar NF e Boleto", 
            "✍️ Painel de Assinaturas (NF e Boleto)",
            "🖨️ Imprimir Espelho de Compra"
        ])
        
        with tab_c1:
            st.markdown("### Cadastrar Nova Necessidade de Compra")
            with st.form("form_nova_compra"):
                c_c1, c_c2 = st.columns(2)
                solic_c = c_c1.text_input("Solicitante", value=st.session_state.usuario)
                setor_c = c_c2.selectbox("Setor Destino", ["Operação", "Administrativo", "TI", "Manutenção", "Cozinha", "Frota", "Outros"])
                
                cat_c = st.selectbox("Categoria do Item", ["Peças de Manutenção", "EPIs", "Material de Escritório", "Alimentação", "Produtos de Limpeza", "Serviços Terceirizados", "Outros"])
                
                st.markdown("#### Lista de Itens (Adicione os itens separando por linha se houver mais de um)")
                itens_c = st.text_area("Descreva os itens e especificações (Ex: 1x Parafuso sextavado 10mm \n2x Luvas de couro)")
                
                obs_c = st.text_area("Observações (Fornecedor sugerido, urgência, etc.)")
                
                arquivo_orcamento = st.file_uploader("Anexar Orçamento (PDF, JPG, PNG) - Opcional para solicitar, obrigatório para aprovar", type=['pdf', 'png', 'jpg', 'jpeg'], key="up_orcamento_novo")
                
                btn_compra = st.form_submit_button("Gerar Solicitação de Compra", use_container_width=True)
                
                if btn_compra:
                    if not solic_c or not itens_c:
                        st.error("Preencha solicitante e a descrição dos itens.")
                    else:
                        n_id_c = 1
                        if not df_compras.empty:
                            n_id_c = df_compras["ID_Compra"].astype(int).max() + 1
                            
                        path_orc = "None"
                        if arquivo_orcamento is not None:
                            ext_orc = os.path.splitext(arquivo_orcamento.name)[1]
                            path_orc = os.path.join("uploads_orcamentos", f"orc_{n_id_c}_solic{ext_orc}")
                            with open(path_orc, "wb") as f_o:
                                f_o.write(arquivo_orcamento.read())
                                
                        nova_compra = pd.DataFrame([{
                            "ID_Compra": str(n_id_c),
                            "Data_Solicitacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Solicitante": solic_c,
                            "Setor": setor_c,
                            "Categoria": cat_c,
                            "Item": itens_c.replace("\n", " | "),
                            "Quantidade": "Ver descrição",
                            "Observacoes": obs_c,
                            "Status": "Nova Solicitação",
                            "Orcamento_Assinado": path_orc,
                            "NF_Anexada": "None",
                            "Boleto_Anexado": "None",
                            "Assinado_Por": "None"
                        }])
                        df_compras = pd.concat([df_compras, nova_compra], ignore_index=True)
                        df_compras.to_csv(ARQUIVO_COMPRAS, index=False)
                        st.success(f"Solicitação #{n_id_c} gerada com sucesso!")
                        st.rerun()

        with tab_c2:
            st.markdown("### Gerenciamento e Aprovação (Fluxo Principal)")
            
            c_f_c1, c_f_c2 = st.columns(2)
            f_stat_c = c_f_c1.selectbox("Filtrar por Status", ["Todos", "Nova Solicitação", "Pendente Assinatura Diretor", "Compra Autorizada", "Aguardando Entrega/NF", "Compra Aprovada/Finalizada", "Cancelada"])
            f_id_c = c_f_c2.text_input("Buscar ID Compra")
            
            df_c_view = df_compras.copy()
            if f_stat_c != "Todos":
                df_c_view = df_c_view[df_c_view["Status"] == f_stat_c]
            if f_id_c:
                df_c_view = df_c_view[df_c_view["ID_Compra"] == f_id_c]
                
            st.dataframe(df_c_view[["ID_Compra", "Data_Solicitacao", "Solicitante", "Setor", "Categoria", "Status", "Orcamento_Assinado"]], use_container_width=True)
            
            if not df_c_view.empty:
                st.markdown("---")
                id_sel_c = st.selectbox("Selecione o ID para Gerenciar/Atualizar Status:", df_c_view["ID_Compra"].tolist(), key="sel_id_gerenciar")
                idx_c = df_compras[df_compras["ID_Compra"] == id_sel_c].index[0]
                row_c = df_compras.iloc[idx_c]
                
                st.markdown(f"**Itens Solicitados:** {row_c['Item']}")
                st.markdown(f"**Observações:** {row_c.get('Observacoes', '')}")
                exibir_documento(row_c.get("Orcamento_Assinado", "None"), "Orçamento Anexado Original")
                
                with st.form("form_atualiza_compra"):
                    st.markdown(f"#### Alterar Status da Compra #{id_sel_c}")
                    
                    lista_status = ["Nova Solicitação", "Pendente Assinatura Diretor", "Compra Autorizada", "Aguardando Entrega/NF", "Compra Aprovada/Finalizada", "Cancelada"]
                    novo_stat_c = st.selectbox("Novo Status", lista_status, index=lista_status.index(row_c["Status"]) if row_c["Status"] in lista_status else 0)
                    
                    arquivo_orcamento_novo = st.file_uploader("Substituir Orçamento Base (Opcional)", type=['pdf', 'png', 'jpg', 'jpeg'], key="up_orc_novo")
                    
                    btn_at_compra = st.form_submit_button("Atualizar Compra", use_container_width=True)
                    
                    if btn_at_compra:
                        df_compras.at[idx_c, "Status"] = novo_stat_c
                        
                        if arquivo_orcamento_novo is not None:
                            ext_orc2 = os.path.splitext(arquivo_orcamento_novo.name)[1]
                            path_orc2 = os.path.join("uploads_orcamentos", f"orc_{id_sel_c}_atualizado{ext_orc2}")
                            with open(path_orc2, "wb") as f_o2:
                                f_o2.write(arquivo_orcamento_novo.read())
                            df_compras.at[idx_c, "Orcamento_Assinado"] = path_orc2
                            
                        df_compras.to_csv(ARQUIVO_COMPRAS, index=False)
                        st.success(f"Status da compra #{id_sel_c} atualizado para '{novo_stat_c}'!")
                        st.rerun()

        with tab_c3:
            st.markdown("### Anexar Nota Fiscal e Boleto Físico/Digital (Setor de Compras)")
            df_c_pendentes_anexo = df_compras[df_compras["Status"].isin(["Compra Autorizada", "Aguardando Entrega/NF"])]
            
            if df_c_pendentes_anexo.empty:
                st.info("Não há compras nos status 'Compra Autorizada' ou 'Aguardando Entrega/NF' aguardando lançamento de NF.")
            else:
                id_sel_anexo = st.selectbox("Selecione a Compra para anexar NF/Boleto", df_c_pendentes_anexo["ID_Compra"].tolist(), key="sel_id_anexo")
                idx_anexo = df_compras[df_compras["ID_Compra"] == id_sel_anexo].index[0]
                
                with st.form("form_anexo_financeiro"):
                    st.info(f"Anexando documentos para a Compra #{id_sel_anexo}")
                    arquivo_nf = st.file_uploader("Anexar Nota Fiscal (PDF, JPG, PNG)", type=['pdf', 'png', 'jpg', 'jpeg'], key="up_nf")
                    arquivo_boleto = st.file_uploader("Anexar Boleto Bancário (PDF, JPG, PNG)", type=['pdf', 'png', 'jpg', 'jpeg'], key="up_bol")
                    
                    btn_salvar_anexos = st.form_submit_button("Salvar Anexos Financeiros e Encaminhar para Assinatura", use_container_width=True)
                    
                    if btn_salvar_anexos:
                        if arquivo_nf is not None:
                            ext_nf = os.path.splitext(arquivo_nf.name)[1]
                            path_nf = os.path.join("uploads_orcamentos", f"NF_{id_sel_anexo}{ext_nf}")
                            with open(path_nf, "wb") as f_nf:
                                f_nf.write(arquivo_nf.read())
                            df_compras.at[idx_anexo, "NF_Anexada"] = path_nf
                            
                        if arquivo_boleto is not None:
                            ext_bol = os.path.splitext(arquivo_boleto.name)[1]
                            path_bol = os.path.join("uploads_orcamentos", f"BOLETO_{id_sel_anexo}{ext_bol}")
                            with open(path_bol, "wb") as f_bol:
                                f_bol.write(arquivo_boleto.read())
                            df_compras.at[idx_anexo, "Boleto_Anexado"] = path_bol
                            
                        df_compras.at[idx_anexo, "Status"] = "Pendente Assinatura Diretor"
                        df_compras.to_csv(ARQUIVO_COMPRAS, index=False)
                        st.success(f"Arquivos da compra #{id_sel_anexo} anexados. Status alterado para 'Pendente Assinatura Diretor'.")
                        st.rerun()

        with tab_c4:
            st.markdown("### ✍️ Painel de Assinaturas (Aprovação de NF/Boletos pelo Diretor/Financeiro)")
            
            df_c_assinatura = df_compras[df_compras["Status"] == "Pendente Assinatura Diretor"]
            
            if df_c_assinatura.empty:
                st.success("Não há documentos pendentes de assinatura no momento. 🎉")
            else:
                id_sel_ass = st.selectbox("Selecione o Lote (Compra) para Revisão e Assinatura", df_c_assinatura["ID_Compra"].tolist(), key="sel_id_ass")
                idx_ass = df_compras[df_compras["ID_Compra"] == id_sel_ass].index[0]
                row_ass = df_compras.iloc[idx_ass]
                
                col_docs1, col_docs2 = st.columns(2)
                with col_docs1:
                    exibir_documento(row_ass.get("NF_Anexada", "None"), "Nota Fiscal")
                with col_docs2:
                    exibir_documento(row_ass.get("Boleto_Anexado", "None"), "Boleto")
                    
                st.markdown("---")
                st.markdown("#### Ação de Assinatura Digital e Compartilhamento")
                
                ass_png_usuario = "None"
                if os.path.exists(ARQUIVO_USERS):
                    df_usr_ass = pd.read_csv(ARQUIVO_USERS, dtype=str)
                    usr_match = df_usr_ass[df_usr_ass["Usuario"] == st.session_state.usuario]
                    if not usr_match.empty:
                        ass_png_usuario = str(usr_match.iloc[0].get("Assinatura_PNG", "None"))
                        
                if ass_png_usuario == "None" or not os.path.exists(ass_png_usuario):
                    st.warning("⚠️ Você não possui uma assinatura PNG cadastrada. Peça ao administrador para cadastrar sua assinatura no menu de Login para carimbar documentos.")
                else:
                    st.info(f"Sua assinatura digital está ativa ({ass_png_usuario}). Ela será aplicada graficamente nos documentos abaixo.")
                
                email_destino_def = "thiagosc2026@gmail.com"
                
                with st.form("form_assinar_documentos"):
                    st.write("**Documentos a Assinar:**")
                    assinar_nf = st.checkbox("Carimbar e Assinar Nota Fiscal", value=True)
                    assinar_bol = st.checkbox("Carimbar e Assinar Boleto", value=True)
                    
                    st.write("**Opções de Envio por E-mail (Via SMTP do seu usuário):**")
                    enviar_por_email = st.checkbox("Enviar documentos assinados por E-mail?", value=True)
                    email_destinatario = st.text_input("E-mail do Destinatário (ex: Financeiro)", value=email_destino_def)
                    corpo_email_ass = st.text_area("Corpo da Mensagem", value=f"Olá, \n\nSegue em anexo a Nota Fiscal e o Boleto aprovados e assinados digitalmente referentes à solicitação de compra #{id_sel_ass}.\n\nAtenciosamente,\n{st.session_state.usuario}")
                    
                    btn_executar_assinatura = st.form_submit_button("Aplicar Assinatura Digital, Mudar Status e Enviar E-mail", use_container_width=True)
                    
                    if btn_executar_assinatura:
                        if ass_png_usuario == "None" or not os.path.exists(ass_png_usuario):
                            st.error("Assinatura PNG não localizada. Configure-a primeiro no painel de administração.")
                        else:
                            sucesso_ass_nf = True
                            sucesso_ass_bol = True
                            anexos_para_email = []
                            
                            caminho_nf_original = row_ass.get("NF_Anexada", "None")
                            if assinar_nf and caminho_nf_original != "None" and os.path.exists(caminho_nf_original):
                                sucesso_ass_nf = carimbar_assinatura_no_documento(caminho_nf_original, ass_png_usuario, st.session_state.usuario)
                                if sucesso_ass_nf:
                                    anexos_para_email.append(caminho_nf_original)
                            
                            caminho_bol_original = row_ass.get("Boleto_Anexado", "None")
                            if assinar_bol and caminho_bol_original != "None" and os.path.exists(caminho_bol_original):
                                sucesso_ass_bol = carimbar_assinatura_no_documento(caminho_bol_original, ass_png_usuario, st.session_state.usuario)
                                if sucesso_ass_bol:
                                    anexos_para_email.append(caminho_bol_original)
                                    
                            if sucesso_ass_nf and sucesso_ass_bol:
                                msg_email_feedback = "E-mail não solicitado."
                                
                                if enviar_por_email:
                                    if not email_destinatario:
                                        msg_email_feedback = "❌ Destinatário não informado, e-mail cancelado."
                                    elif not anexos_para_email:
                                        msg_email_feedback = "❌ Sem documentos válidos para anexar."
                                    else:
                                        usr_cfg_match = df_usr_ass[df_usr_ass["Usuario"] == st.session_state.usuario].iloc[0]
                                        config_smtp = {
                                            "Email_Remetente": usr_cfg_match.get("Email_Usuario", ""),
                                            "Senha_App": usr_cfg_match.get("Senha_App_Email", ""),
                                            "Servidor_SMTP": usr_cfg_match.get("Servidor_SMTP", "smtp.gmail.com"),
                                            "Porta_SMTP": usr_cfg_match.get("Porta_SMTP", "587"),
                                            "Nome_Remetente": f"{st.session_state.usuario} - Intranet"
                                        }
                                        
                                        assunto = "Aprovação deAqui está o código completo refatorado, incluindo todas as implementações solicitadas: o **botão de impressão do relatório geral de O.S.**, o **Dashboard global integrado estilo Power BI com fundo transparente (dividido entre O.S. e Compras)**, o **gráfico comparativo de prazos no painel de FMs**, e a **restauração exata** das lógicas de Assinaturas e Compras que haviam sido cortadas."

```python
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
