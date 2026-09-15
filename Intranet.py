import io
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import fitz  # PyMuPDF
import streamlit as st


def assinar_pdf(pdf_bytes, imagem_assinatura_bytes):
    """Carimba a imagem da assinatura no rodapé da última página do PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    ultima_pagina = doc[-1]

    # Define o retângulo onde a assinatura será colada (rodapé centralizado)
    # [x0, y0, x1, y1] - ajustável conforme a necessidade
    rect_pagina = ultima_pagina.rect
    largura_img, altura_img = 150, 50
    x0 = (rect_pagina.width - largura_img) / 2
    y0 = rect_pagina.height - altura_img - 20
    rect_assinatura = fitz.Rect(x0, y0, x0 + largura_img, y0 + altura_img)

    ultima_pagina.insert_image(
        rect_assinatura, stream=imagem_assinatura_bytes
    )

    pdf_assinado = io.BytesIO()
    doc.save(pdf_assinado)
    doc.close()
    return pdf_assinado.getvalue()


def enviar_email_smtp(
    destinatario, assunto, corpo, pdf_bytes, nome_arquivo, config_smtp
):
    """Realiza o disparo do e-mail via servidor SMTP nativo do Python."""
    msg = MIMEMultipart()
    msg["From"] = config_smtp["usuario"]
    msg["To"] = destinatario
    msg["Subject"] = assunto

    msg.attach(MIMEText(corpo, "plain"))

    anexo = MIMEApplication(pdf_bytes, Name=nome_arquivo)
    anexo["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
    msg.attach(anexo)

    with smtplib.SMTP(config_smtp["servidor"], config_smtp["porta"]) as server:
        server.starttls()
        server.login(config_smtp["usuario"], config_smtp["senha"])
        server.send_message(msg)


# --- INTERFACE STREAMLIT ---
st.title("Processamento e Assinatura de Documentos")

# Uploads
pdf_upload = st.file_uploader("Selecione o PDF", type=["pdf"])
assinatura_upload = st.file_uploader(
    "Selecione a Imagem da Assinatura (PNG)", type=["png", "jpg", "jpeg"]
)

# Dados de E-mail
st.subheader("Dados para Envio")
email_destinatario = st.text_input("E-mail do Destinatário")

# Configurações do Servidor SMTP (Podem ser movidas para secrets/env)
CONFIG_SMTP = {
    "servidor": "smtp.gmail.com",  # Exemplo: smtp.office365.com ou servidor próprio
    "porta": 587,
    "usuario": "seu_email@dominio.com",
    "senha": "sua_senha_ou_app_password",
}

if st.button("Assinar e Enviar Documento"):
    if pdf_upload and assinatura_upload and email_destinatario:
        try:
            # 1. Processa e Carimba o PDF
            bytes_pdf_assinado = assinar_pdf(
                pdf_upload.read(), assinatura_upload.read()
            )

            # 2. Envia por E-mail
            enviar_email_smtp(
                destinatario=email_destinatario,
                assunto="Documento Assinado",
                corpo="Segue em anexo o documento assinado.",
                pdf_bytes=bytes_pdf_assinado,
                nome_arquivo=f"Assinado_{pdf_upload.name}",
                config_smtp=CONFIG_SMTP,
            )

            st.success("Documento assinado e e-mail enviado com sucesso!")

            # Botão alternativo para download direto
            st.download_button(
                label="Baixar PDF Assinado",
                data=bytes_pdf_assinado,
                file_name=f"Assinado_{pdf_upload.name}",
                mime="application/pdf",
            )

        except Exception as e:
            st.error(f"Falha ao processar o envio: {e}")
    else:
        st.warning(
            "Preencha todos os campos e adicione os arquivos necessários."
        )
