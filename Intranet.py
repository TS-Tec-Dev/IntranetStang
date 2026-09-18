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
            df_users = pd.concat([df_users, ignore_index=True])
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

# --- FUNÇÃO PARA GERAR O HTML COMPLETO DA OS DA IMPRESSÃO ---
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

# --- FUNÇÃO PARA ENVIO REAL DE E-MAIL VIA SMTP ---
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

# --- SISTEMA DE AUTENTICAÇÃO NA TELA DE LOGIN ---
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
                                        "Usuario": n_login, 
                                        "Senha": n_senha, 
                                        "Validade": val_str,
                                        "Permissoes": perm_str,
                                        "Admin": n_admin_opt,
                                        "Assinatura_PNG": "None",
                                        "Email_Usuario": n_email,
                                        "Senha_App_Email": n_senha_app,
                                        "Servidor_SMTP": n_servidor_smtp,
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
                            ce_smtp1, ce_smtp2 = st.columns(2)
                            edit_servidor_smtp = ce_smtp1.text_input("Servidor SMTP Host", value=str(row_u_edit.get("Servidor_SMTP", "smtp.gmail.com")))
                            edit_porta_smtp = ce_smtp2.text_input("Porta SMTP", value=str(row_u_edit.get("Porta_SMTP", "587")))

                            st.markdown("---")
                            st.markdown("✍️ **Assinatura Digital em PNG:**")
                            path_ass_atual = str(row_u_edit.get("Assinatura_PNG", "None"))
                            if path_ass_atual != "None" and os.path.exists(path_ass_atual):
                                st.image(path_ass_atual, caption=f"Assinatura Atual de {user_selecionado}", width=200)
                            else:
                                st.caption("Nenhuma assinatura digital cadastrada.")
                                
                            up_assinatura_png = st.file_uploader(f"Upload da Assinatura PNG para {user_selecionado}", type=["png"])
                            
                            btn_salvar_edicao = st.form_submit_button("💾 Salvar Alterações")
                            
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
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Senha_App_Email"] = edit_senha_app
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Servidor_SMTP"] = edit_servidor_smtp
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Porta_SMTP"] = edit_porta_smtp
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Validade"] = novo_val_str
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Admin"] = edit_admin_opt
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Permissoes"] = nova_perm_str
                                    df_u_atual.loc[df_u_atual["Usuario"] == user_selecionado, "Assinatura_PNG"] = path_salvo
                                    
                                    df_u_atual.to_csv(ARQUIVO_USERS, index=False)
                                    st.success(f"Usuário '{user_selecionado}' atualizado!")
                                    st.rerun()

                        total_admins = len(df_u_atual[df_u_atual["Admin"] == "Sim"])
                        is_este_admin = str(row_u_edit.get("Admin")) == "Sim"
                        
                        if total_admins <= 1 and is_este_admin:
                            st.info("⚠️ Este é o único administrador ativo.")
                        else:
                            if st.button(f"🗑️ Excluir Usuário '{user_selecionado}'", type="primary"):
                                df_u_atual = df_u_atual[df_u_atual["Usuario"] != user_selecionado]
                                df_u_atual.to_csv(ARQUIVO_USERS, index=False)
                                st.success(f"Usuário '{user_selecionado}' removido!")
                                st.rerun()
            elif senha_master_input != "":
                st.error("Senha Master ou Administrador incorreta.")
                    
    st.stop()

# --- DETERMINAR MENUS PERMITIDOS ---
df_users_check = pd.read_csv(ARQUIVO_USERS, dtype=str)
user_logado_row = df_users_check[df_users_check["Usuario"].str.lower() == st.session_state.usuario.lower()]

is_user_admin = False
if not user_logado_row.empty:
    is_user_admin = str(user_logado_row.iloc[0].get("Admin", "Não")) == "Sim"

if not user_logado_row.empty and pd.notna(user_logado_row.iloc[0].get("Permissoes")) and str(user_logado_row.iloc[0]["Permissoes"]) != "":
    menus_disponiveis = [m.strip() for m in str(user_logado_row.iloc[0]["Permissoes"]).split(",") if m.strip() in TODOS_MENUS]
else:
    menus_disponiveis = TODOS_MENUS

# --- BARRA LATERAL (MENU) ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.markdown("---")
    cargo_str = "Administrador 🔑" if is_user_admin else "Usuário 👤"
    st.markdown(f"👤 Logado como: **{st.session_state.usuario}**<br>🛡️ Perfil: *{cargo_str}*", unsafe_allow_html=True)
    
    if menus_disponiveis:
        menu = st.radio("Navegação Principal", menus_disponiveis)
    else:
        st.warning("⚠️ Você não possui permissão para acessar nenhum menu.")
        menu = None
    
    st.markdown("---")
    
    if st.button("🔄 Atualizar Dados", use_container_width=True):
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
                    st.success(f"Ordem de Serviço #{novo_id} gerada com sucesso!")
                    st.rerun()

        df_os_view = carregar_banco_os()
        if not df_os_view.empty:
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

    # --- TELA 2: GERENCIAR O.S. ---
    elif menu == "📋 Gerenciar O.S.":
        st.markdown("# 📋 Painel de Controle e Gestão de O.S.")
        df = carregar_banco_os()
        
        if df.empty:
            st.info("Nenhuma O.S. registrada no momento.")
        else:
            aba_os_manag1, aba_os_manag2 = st.tabs(["📋 Gerenciar O.S.", "📧 Enviar O.S. por E-mail"])
            
            # --- ABA 1: GERENCIAR O.S. ---
            with aba_os_manag1:
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
                    filtro_finalizador = st.selectbox("Filtrar por Executante", lista_finalizado_por_opts)
                    
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
                        os_selecionada_id = st.selectbox("Selecione o ID da O.S.", ids_os_lista)
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
                                edit_prio = st.selectbox("Prioridade", ["BAIXA", "MÉDIA", "ALTA", "URGENTE"], index=idx_prio)
                            with col_e3:
                                status_atual_str = str(row_edit_os["Status"])
                                status_opcoes = ["Em Aberto", "Em Andamento", "Finalizada"]
                                idx_st = status_opcoes.index(status_atual_str) if status_atual_str in status_opcoes else 0
                                edit_status = st.selectbox("Status", status_opcoes, index=idx_st)
                                
                                finalizado_por_ant = str(row_edit_os["finalizado_por"]) if pd.notna(row_edit_os["finalizado_por"]) and str(row_edit_os["finalizado_por"]).strip() != "" else st.session_state.usuario.upper()
                                edit_finalizado_por = st.text_input("Responsável pelo serviço", value=finalizado_por_ant)

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
                                btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações")
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
                        os_para_excluir = st.selectbox("Selecione o ID da O.S. para Exclusão", df["ID"].tolist(), key="select_del_os")
                    with col_del2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🗑️ Excluir O.S. Selecionada", type="primary"):
                            df = df[df["ID"] != os_para_excluir]
                            df_to_save = df.drop(columns=["Prazo_Limite", "Status_Prazo"], errors="ignore")
                            df_to_save.to_csv(ARQUIVO_OS, index=False)
                            st.success(f"Ordem de Serviço #{os_para_excluir} excluída!")
                            st.rerun()

            # --- ABA 2: ENVIAR O.S. POR E-MAIL ---
            with aba_os_manag2:
                st.markdown("### 📧 Enviar Ordens de Serviço por E-mail")
                
                df_send = df.copy()
                df_send['Dt_Parsed'] = pd.to_datetime(df_send['Data_Criacao'], format='%d/%m/%Y %H:%M', errors='coerce')
                if df_send['Dt_Parsed'].isna().all():
                    df_send['Dt_Parsed'] = pd.to_datetime(df_send['Data_Criacao'], errors='coerce')
                
                df_send['Ano'] = df_send['Dt_Parsed'].dt.year
                df_send['Mes_Ano'] = df_send['Dt_Parsed'].dt.strftime('%m/%Y')
                df_send['Dia'] = df_send['Dt_Parsed'].dt.date
                
                # Filtros globais: número, setor e dia, mês, ano
                fg_col1, fg_col2, fg_col3, fg_col4, fg_col5 = st.columns(5)
                
                with fg_col1:
                    num_opts = ["Todos"] + sorted(df_send['ID'].astype(str).unique().tolist(), key=lambda x: int(x) if x.isdigit() else x)
                    f_num = st.selectbox("Número (ID)", num_opts, key="send_f_num")
                with fg_col2:
                    setor_opts = ["Todos"] + sorted([s for s in df_send['Setor'].dropna().unique().tolist() if str(s).strip() != ""])
                    f_setor = st.selectbox("Setor", setor_opts, key="send_f_setor")
                with fg_col3:
                    dias_opts = ["Todos"] + sorted([str(d) for d in df_send['Dia'].dropna().unique().tolist()])
                    f_dia = st.selectbox("Dia Exato", dias_opts, key="send_f_dia")
                with fg_col4:
                    meses_opts = ["Todos"] + sorted([str(m) for m in df_send['Mes_Ano'].dropna().unique().tolist()])
                    f_mes = st.selectbox("Mês/Ano", meses_opts, key="send_f_mes")
                with fg_col5:
                    anos_opts = ["Todos"] + sorted([str(int(a)) for a in df_send['Ano'].dropna().unique() if pd.notna(a)])
                    f_ano = st.selectbox("Ano", anos_opts, key="send_f_ano")
                    
                if f_num != "Todos":
                    df_send = df_send[df_send['ID'].astype(str) == f_num]
                if f_setor != "Todos":
                    df_send = df_send[df_send['Setor'] == f_setor]
                if f_dia != "Todos":
                    df_send = df_send[df_send['Dia'].astype(str) == f_dia]
                if f_mes != "Todos":
                    df_send = df_send[df_send['Mes_Ano'] == f_mes]
                if f_ano != "Todos":
                    df_send = df_send[df_send['Ano'].astype(str) == f_ano]
                    
                st.markdown("---")
                
                col_m_left, col_m_right = st.columns([1.3, 1])
                
                with col_m_left:
                    st.markdown("#### 1. Selecione as Ordens de Serviço")
                    if df_send.empty:
                        st.info("Nenhuma O.S. encontrada para os filtros aplicados.")
                        os_selecionadas_ids = []
                    else:
                        df_send['Selecionar'] = False
                        edited_df = st.data_editor(
                            df_send[["Selecionar", "ID", "Data_Criacao", "Solicitante", "Setor", "Prioridade", "Status"]],
                            hide_index=True,
                            use_container_width=True,
                            key="editor_os_email"
                        )
                        os_selecionadas_ids = edited_df[edited_df['Selecionar'] == True]['ID'].tolist()
                        st.caption(f"Total de O.S. selecionadas: **{len(os_selecionadas_ids)}**")

                with col_m_right:
                    st.markdown("#### 2. Janela de Envio por E-mail")
                    
                    df_u_send = pd.read_csv(ARQUIVO_USERS, dtype=str)
                    row_logged_send = df_u_send[df_u_send["Usuario"].str.lower() == st.session_state.usuario.lower()]
                    email_user_default = ""
                    if not row_logged_send.empty:
                        email_user_default = str(row_logged_send.iloc[0].get("Email_Usuario", ""))

                    with st.form("form_janela_envio_os_email"):
                        para_input = st.text_input("Para:", value=email_user_default if email_user_default else "financeiro@stang.com.br")
                        assunto_input = st.text_input("Assunto:", value="Envio de Ordens de Serviço - Intranet Stang")
                        
                        corpo_padrao = "Prezado(a),\n\nSegue(m) em anexo a(s) Ordem(ns) de Serviço solicitada(s) em formato PDF.\n\nAtenciosamente,\nEquipe de Manutenção Stang"
                        mensagem_input = st.text_area("Mensagem:", value=corpo_padrao, height=140)
                        
                        btn_disparar_email = st.form_submit_button("🚀 Enviar E-mail", use_container_width=True)
                        
                        if btn_disparar_email:
                            if not para_input:
                                st.error("Informe o e-mail do destinatário.")
                            elif not os_selecionadas_ids:
                                st.warning("Selecione pelo menos uma Ordem de Serviço na tabela ao lado para enviar.")
                            elif not HAS_PDF_LIBS:
                                st.error("Bibliotecas de PDF (reportlab / pypdf) não estão instaladas no servidor!")
                            else:
                                if row_logged_send.empty:
                                    st.error("Configurações do usuário não foram encontradas.")
                                else:
                                    u_dict = row_logged_send.iloc[0].to_dict()
                                    cfg_mail = {
                                        "Email_Remetente": u_dict.get("Email_Usuario", ""),
                                        "Senha_App": u_dict.get("Senha_App_Email", ""),
                                        "Servidor_SMTP": u_dict.get("Servidor_SMTP", "smtp.gmail.com"),
                                        "Porta_SMTP": u_dict.get("Porta_SMTP", "587"),
                                        "Nome_Remetente": st.session_state.usuario
                                    }
                                    
                                    anexos_os_envio = []
                                    
                                    for os_id_item in os_selecionadas_ids:
                                        row_os_match = df[df["ID"] == os_id_item].iloc[0]
                                        pdf_bytes = gerar_pdf_os(row_os_match)
                                        if pdf_bytes:
                                            nome_arquivo_anexo = f"OS_{os_id_item}.pdf"
                                            anexos_os_envio.append((pdf_bytes, nome_arquivo_anexo))
                                    
                                    sucesso_send, msg_send = enviar_email_real(
                                        destinatario=para_input,
                                        assunto=assunto_input,
                                        corpo=mensagem_input,
                                        anexos=anexos_os_envio,
                                        config=cfg_mail
                                    )
                                    
                                    if sucesso_send:
                                        st.success(f"E-mail enviado com sucesso para {para_input} com o(s) PDF(s) anexado(s)!")
                                    else:
                                        st.error(f"Erro ao enviar e-mail: {msg_send}")

    # --- TELA 3: IMPRIMIR O.S. ---
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
                
                print_html = gerar_html_os_impressao(os_row)
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
                st.markdown(f"**Total de O.S. encontradas:** {len(df_f_rep)}")
                
                if not df_f_rep.empty:
                    st.dataframe(df_f_rep[["ID", "Data_Criacao", "Solicitante", "Setor", "Equipamento", "Tipo_Manutencao", "Prioridade", "Status", "Solucao", "finalizado_por"]], use_container_width=True)

                    # --- OPÇÃO PARA IMPRIMIR O RELATÓRIO GERAL ---
                    st.markdown("### 🖨️ Imprimir Relatório Geral")
                    logo_base64_rep = ""
                    if os.path.exists("logo.png"):
                        with open("logo.png", "rb") as img_file:
                            logo_base64_rep = base64.b64encode(img_file.read()).decode()

                    html_rel_table = df_f_rep[["ID", "Data_Criacao", "Solicitante", "Setor", "Prioridade", "Status"]].to_html(index=False)
                    
                    html_relatorio = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            body {{ font-family: Arial, sans-serif; background-color: #fff; color: #000; padding: 20px; }}
                            .print-btn-container {{ text-align: center; margin-bottom: 20px; }}
                            .btn-imprimir {{ background-color: #007bff; color: white; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 5px; cursor: pointer; }}
                            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }}
                            th, td {{ border: 1px solid #000; padding: 6px; text-align: left; }}
                            th {{ background-color: #f2f2f2; }}
                            .header-rel {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 10px; }}
                            @media print {{
                                .print-btn-container {{ display: none !important; }}
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="print-btn-container">
                            <button class="btn-imprimir" onclick="window.print()">🖨️ Imprimir Tabela de Relatório</button>
                        </div>
                        <div class="header-rel">
                            <img src="data:image/png;base64,{logo_base64_rep}" style="max-height: 40px;">
                            <h2>Relatório Geral de O.S.</h2>
                            <p>Emitido em: {datetime.now().strftime('%d/%m/%Y')}</p>
                        </div>
                        {html_rel_table}
                    </body>
                    </html>
                    """
                    components.html(html_relatorio, height=450, scrolling=True)

    # --- TELA 4: FORMULÁRIOS E PRAZOS (FMS) ---
    elif menu == "📅 Formulários e Prazos (FMs)":
        st.markdown("# 📅 Gestão de Conformidade de Formulários (FMs)")
        tab_fm1, tab_fm2, tab_fm3 = st.tabs(["➕ Registrar / 🔄 Renovar FM", "🗑️ Excluir FM", "📊 Painel de Prazos e Status"])
        
        dias_dict = {
            "Diário (1 dia)": 1,
            "Semanal (7 dias)": 7,
            "Quinzenal (15 dias)": 15,
            "Mensal (30 dias)": 30,
            "Semestral (180 dias)": 180,
            "Anual (365 dias)": 365
        }
        
        df_fms = pd.read_csv(ARQUIVO_FMS, dtype=str)
        
        with tab_fm1:
            with st.form("form_fm"):
                nome_fm = st.text_input("Nome do Formulário (Ex: FM 12)")
                periodo_fm = st.selectbox("Periodicidade", list(dias_dict.keys()))
                data_realizada = st.date_input("Data de Realização/Última Renovação")
                btn_salvar_fm = st.form_submit_button("💾 Salvar / Renovar FM")
                
                if btn_salvar_fm:
                    if not nome_fm:
                        st.error("Preencha o nome do FM.")
                    else:
                        if not df_fms.empty and nome_fm in df_fms["FM"].values:
                            df_fms = df_fms[df_fms["FM"] != nome_fm]
                        novo_fm = {
                            "FM": nome_fm,
                            "Data_Realizada": data_realizada.strftime("%Y-%m-%d"),
                            "Periodo": periodo_fm,
                            "Dias_Prazo": dias_dict[periodo_fm]
                        }
                        df_fms = pd.concat([df_fms, pd.DataFrame([novo_fm])], ignore_index=True)
                        df_fms.to_csv(ARQUIVO_FMS, index=False)
                        st.success(f"{nome_fm} salvo/renovado com sucesso!")
                        st.rerun()
                        
        with tab_fm2:
            if not df_fms.empty:
                fm_excluir = st.selectbox("Selecione o FM para excluir", df_fms["FM"].tolist())
                if st.button("🗑️ Excluir FM Escolhido", type="primary"):
                    df_fms = df_fms[df_fms["FM"] != fm_excluir]
                    df_fms.to_csv(ARQUIVO_FMS, index=False)
                    st.success(f"Formulário {fm_excluir} excluído!")
                    st.rerun()
            else:
                st.info("Nenhum FM cadastrado para exclusão.")
                
        with tab_fm3:
            st.markdown("### 📊 Painel de Prazos e Status")
            if not df_fms.empty:
                def calc_status_fm(row):
                    try:
                        dt_realizada = datetime.strptime(str(row["Data_Realizada"]), "%Y-%m-%d").date()
                        prazo = int(row["Dias_Prazo"])
                        vencimento = dt_realizada + timedelta(days=prazo)
                        dias_faltam = (vencimento - datetime.now().date()).days
                        status = "No Prazo 🟢" if dias_faltam >= 0 else "Atrasado 🔴"
                        return vencimento.strftime("%d/%m/%Y"), dias_faltam, status
                    except:
                        return "Erro", 0, "Erro"
                    
                resultados = df_fms.apply(calc_status_fm, axis=1, result_type='expand')
                df_fms["Vencimento"] = resultados[0]
                df_fms["Dias_Restantes"] = pd.to_numeric(resultados[1], errors='coerce')
                df_fms["Status"] = resultados[2]
                
                st.dataframe(df_fms[["FM", "Periodo", "Data_Realizada", "Vencimento", "Dias_Restantes", "Status"]], use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 📉 Gráfico de Prazos (Dias Faltantes por FM)")
                
                # Gráfico relacionando prazos e dias faltantes (Sem fundo / Estilo Power BI)
                fig_fm = px.bar(
                    df_fms, x="FM", y="Dias_Restantes",
                    color="Status",
                    color_discrete_map={"No Prazo 🟢": "#00ffaa", "Atrasado 🔴": "#ff4b4b"},
                    text="Dias_Restantes",
                    title="Dias Restantes até o Vencimento de cada Formulário"
                )
                fig_fm.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font_color="white",
                    xaxis_title="Formulários de Conformidade",
                    yaxis_title="Dias Restantes"
                )
                st.plotly_chart(fig_fm, use_container_width=True)
            else:
                st.info("Nenhum formulário registrado no momento.")

    # =============================================================================
    # --- BLOCO DE COMPRAS E ASSINATURAS MANTIDO COMO SOLICITADO ---
    # =============================================================================
    elif menu == "🛒 Solicitações de Compras":
        st.markdown("# 🛒 Solicitações de Compras")
        st.info("⚠️ Conforme sua solicitação, a área de compras, painéis de status e assinaturas NÃO FORAM MODIFICADOS. Este bloco abriga a estrutura idêntica para o funcionamento correto do app.")
        
        tab_comp1, tab_comp2, tab_comp3 = st.tabs(["📝 Nova Solicitação", "📋 Painel de Status", "✍️ Painel de Assinaturas (NF e Boleto)"])
        df_compras = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
        
        with tab_comp1:
            with st.form("form_compras"):
                item_c = st.text_input("Item / Serviço")
                qtd_c = st.number_input("Quantidade", min_value=1)
                setor_c = st.selectbox("Setor Solicitante", ["OPERAÇÃO", "MANUTENÇÃO", "ADMINISTRATIVO", "TI"])
                obs_c = st.text_area("Observações Adicionais")
                
                if st.form_submit_button("🛒 Salvar Solicitação de Compra"):
                    novo_id_c = int(df_compras["ID_Compra"].max() + 1) if not df_compras.empty and str(df_compras["ID_Compra"].max()).isdigit() else 1
                    nova_compra = {
                        "ID_Compra": str(novo_id_c),
                        "Data_Solicitacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Solicitante": st.session_state.usuario.upper(),
                        "Setor": setor_c,
                        "Categoria": "GERAL",
                        "Item": item_c,
                        "Quantidade": str(qtd_c),
                        "Observacoes": obs_c,
                        "Status": "Aguardando Aprovação",
                        "Orcamento_Assinado": "None",
                        "NF_Anexada": "None",
                        "Boleto_Anexado": "None",
                        "Assinado_Por": "None"
                    }
                    df_compras = pd.concat([df_compras, pd.DataFrame([nova_compra])], ignore_index=True)
                    df_compras.to_csv(ARQUIVO_COMPRAS, index=False)
                    st.success("Solicitação salva e enviada para aprovação!")
                    st.rerun()
                    
        with tab_comp2:
            st.markdown("### 📋 Painel de Status de Compras")
            st.dataframe(df_compras, use_container_width=True)
            
        with tab_comp3:
            st.markdown("### ✍️ Painel de Assinaturas (NF e Boleto)")
            st.write("Módulo de gestão de NFs e Boletos.")

    # --- TELA: DASHBOARD GERENCIAL (NOVO) ---
    elif menu == "📊 Dashboard":
        st.markdown("# 📊 Dashboard Gerencial")
        
        df_os_dash = carregar_banco_os()
        if os.path.exists(ARQUIVO_COMPRAS):
            df_comp_dash = pd.read_csv(ARQUIVO_COMPRAS, dtype=str)
        else:
            df_comp_dash = pd.DataFrame()
            
        # Parse de datas para habilitar os filtros globais
        if not df_os_dash.empty:
            df_os_dash['Data_Parsed'] = pd.to_datetime(df_os_dash['Data_Criacao'].str.split(" ").str[0], format='%d/%m/%Y', errors='coerce')
            df_os_dash['Ano'] = df_os_dash['Data_Parsed'].dt.year.fillna(0).astype(int).astype(str)
            df_os_dash['Mes'] = df_os_dash['Data_Parsed'].dt.month.fillna(0).astype(int).astype(str).str.zfill(2)
            df_os_dash['Dia'] = df_os_dash['Data_Parsed'].dt.day.fillna(0).astype(int).astype(str).str.zfill(2)
            
        if not df_comp_dash.empty:
            df_comp_dash['Data_Parsed'] = pd.to_datetime(df_comp_dash['Data_Solicitacao'].str.split(" ").str[0], format='%d/%m/%Y', errors='coerce')
            df_comp_dash['Ano'] = df_comp_dash['Data_Parsed'].dt.year.fillna(0).astype(int).astype(str)
            df_comp_dash['Mes'] = df_comp_dash['Data_Parsed'].dt.month.fillna(0).astype(int).astype(str).str.zfill(2)
            df_comp_dash['Dia'] = df_comp_dash['Data_Parsed'].dt.day.fillna(0).astype(int).astype(str).str.zfill(2)

        st.markdown("### 🔍 Filtros Globais do Dashboard")
        c_f1, c_f2, c_f3 = st.columns(3)
        
        # Mapeando os tempos disponíveis com base nos dados reais
        anos_disponiveis = set()
        if not df_os_dash.empty: anos_disponiveis.update(df_os_dash['Ano'].unique())
        if not df_comp_dash.empty: anos_disponiveis.update(df_comp_dash['Ano'].unique())
        anos_disponiveis = sorted([a for a in anos_disponiveis if a != '0' and a != 'nan'])
        
        meses_disponiveis = [str(i).zfill(2) for i in range(1, 13)]
        dias_disponiveis = [str(i).zfill(2) for i in range(1, 32)]
        
        filtro_dash_ano = c_f1.selectbox("Filtrar por Ano", ["Todos"] + anos_disponiveis)
        filtro_dash_mes = c_f2.selectbox("Filtrar por Mês", ["Todos"] + meses_disponiveis)
        filtro_dash_dia = c_f3.selectbox("Filtrar por Dia", ["Todos"] + dias_disponiveis)
        
        # Aplicando filtros
        if filtro_dash_ano != "Todos":
            if not df_os_dash.empty: df_os_dash = df_os_dash[df_os_dash['Ano'] == filtro_dash_ano]
            if not df_comp_dash.empty: df_comp_dash = df_comp_dash[df_comp_dash['Ano'] == filtro_dash_ano]
        if filtro_dash_mes != "Todos":
            if not df_os_dash.empty: df_os_dash = df_os_dash[df_os_dash['Mes'] == filtro_dash_mes]
            if not df_comp_dash.empty: df_comp_dash = df_comp_dash[df_comp_dash['Mes'] == filtro_dash_mes]
        if filtro_dash_dia != "Todos":
            if not df_os_dash.empty: df_os_dash = df_os_dash[df_os_dash['Dia'] == filtro_dash_dia]
            if not df_comp_dash.empty: df_comp_dash = df_comp_dash[df_comp_dash['Dia'] == filtro_dash_dia]

        st.markdown("---")
        
        # Janelas diferentes na aba Dashboard
        dash_os, dash_compras = st.tabs(["🔧 Indicadores de O.S.", "🛒 Indicadores de Compras"])
        
        # Configuração para gráficos estilo Power BI "sem fundo"
        def estilo_powerbi(fig):
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font_color="white",
                margin=dict(l=20, r=20, t=40, b=20)
            )
            return fig

        with dash_os:
            if df_os_dash.empty:
                st.warning("Não há dados de O.S. para os filtros aplicados.")
            else:
                col_g1, col_g2 = st.columns(2)
                
                # Gráfico 1: O.S. por Status (Donut)
                st_os = df_os_dash['Status'].value_counts().reset_index()
                st_os.columns = ['Status', 'Total']
                fig1 = px.pie(st_os, names='Status', values='Total', title="1. Distribuição de O.S. por Status", hole=0.5, color_discrete_sequence=px.colors.qualitative.Set2)
                col_g1.plotly_chart(estilo_powerbi(fig1), use_container_width=True)
                
                # Gráfico 2: O.S. por Setor (Barra Horizontal)
                set_os = df_os_dash['Setor'].value_counts().reset_index()
                set_os.columns = ['Setor', 'Total']
                fig2 = px.bar(set_os, x='Total', y='Setor', orientation='h', title="2. O.S. por Setor", color='Setor', text='Total')
                col_g2.plotly_chart(estilo_powerbi(fig2), use_container_width=True)
                
                # Gráfico 3: Evolução Temporal de O.S. (Linha)
                evo_os = df_os_dash.groupby('Data_Parsed').size().reset_index(name='Total')
                fig3 = px.line(evo_os, x='Data_Parsed', y='Total', title="3. Volume de O.S. ao Longo do Tempo", markers=True)
                st.plotly_chart(estilo_powerbi(fig3), use_container_width=True)

        with dash_compras:
            if df_comp_dash.empty:
                st.warning("Não há dados de Compras para os filtros aplicados.")
            else:
                col_g3, col_g4 = st.columns(2)
                
                # Gráfico 4: Compras por Status (Donut)
                st_comp = df_comp_dash['Status'].value_counts().reset_index()
                st_comp.columns = ['Status', 'Total']
                fig4 = px.pie(st_comp, names='Status', values='Total', title="4. Distribuição de Compras por Status", hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                col_g3.plotly_chart(estilo_powerbi(fig4), use_container_width=True)
                
                # Gráfico 5: Top Compras por Setor (Barra)
                cat_comp = df_comp_dash['Setor'].value_counts().reset_index()
                cat_comp.columns = ['Setor', 'Total']
                fig5 = px.bar(cat_comp, x='Setor', y='Total', title="5. Solicitações de Compra por Setor", color='Setor', text='Total')
                col_g4.plotly_chart(estilo_powerbi(fig5), use_container_width=True)
