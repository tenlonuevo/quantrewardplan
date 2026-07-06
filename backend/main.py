import os
import json
import csv
import time
import tempfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)
raw_key = os.getenv("GEMINI_API_KEY")

if not raw_key:
    raise RuntimeError("API Key no encontrada. Verifica tu archivo .env")

API_KEY = raw_key.strip()
client = genai.Client(api_key=API_KEY)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=404, detail="Archivo index.html no encontrado.")
    return FileResponse(frontend_path)

@app.get("/favicon.png")
async def serve_favicon():
    favicon_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "favicon.png")
    if not os.path.exists(favicon_path):
        raise HTTPException(status_code=404, detail="Archivo favicon.png no encontrado.")
    return FileResponse(favicon_path)

@app.post("/analizar-estado")
async def analizar_estado(
    email: str = Form(...), 
    niche: str = Form(...), 
    lang: str = Form(...),
    gasto: float = Form(0.0),
    utm_source: str = Form(""),
    utm_medium: str = Form(""),
    utm_campaign: str = Form(""),
    file: Optional[UploadFile] = File(None)
):
    try:
        file_exists = os.path.isfile("leads.csv")
        with open("leads.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Fecha", "Email", "Perfil", "Gasto", "Origen_Ad", "Medio", "Campaña"])
            writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), email, niche, gasto, utm_source, utm_medium, utm_campaign])
    except Exception as e:
        print(f"Error interno CSV: {e}")

    # RUTA VIP CON PDF/IMAGEN
    if file and file.filename:
        temp_file_path = ""
        try:
            ext = os.path.splitext(file.filename)[1].lower()
            if not ext: ext = ".pdf"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                temp_file.write(await file.read())
                temp_file_path = temp_file.name

            documento = client.files.upload(file=temp_file_path)
            
            if lang == 'en':
                titulo_informe = "**QUANT REWARD PLAN: FINANCIAL AUDIT**"
                idioma_instruccion = "ESTRICTAMENTE EN INGLÉS"
            else:
                titulo_informe = "**QUANT REWARD PLAN: AUDITORÍA FINANCIERA**"
                idioma_instruccion = "ESTRICTAMENTE EN ESPAÑOL"
            
            prompt = f"""Actúa como Quant Reward Plan.
            Analiza este estado de cuenta o comprobante para el perfil financiero: {niche.upper()}.
            REGLAS ESTRICTAS E INQUEBRANTABLES: 
            1. IDIOMA OBLIGATORIO: DEBES generar todo el reporte {idioma_instruccion}.
            2. El título inicial debe ser EXACTAMENTE este: {titulo_informe}
            3. Privacidad total: Ignora y no menciones ningún dato personal, nombre o número de cuenta.
            4. Genera urgencia: Calcula y muestra la fuga de capital a nivel Mensual y Anual basada en los montos detectados.
            5. Sé directo, persuasivo y estructurado en viñetas breves enfocadas en la pérdida financiera."""
            
            respuesta = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=[prompt, documento]
            )
            client.files.delete(name=documento.name)
            return {"analisis": respuesta.text}
            
        except Exception as e:
            print(f"ERROR CRÍTICO EN IA: {str(e)}")
            raise HTTPException(status_code=500, detail="Error interno en IA procesando documento.")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    # RUTA RÁPIDA (SLIDER)
    else:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        multiplicador = config["multiplicadores_nicho"].get(niche, 3)
        valor_punto = config.get("valor_punto_promedio", 0.015)
        
        fuga_mensual = (gasto * multiplicador) * valor_punto
        fuga_anual = fuga_mensual * 12

        if lang == 'en':
            if niche == 'elite':
                analisis = f"**QUANT REWARD PLAN: ELITE STRATEGY**\n\n### **CRITICAL CAPITAL LEAKAGE ANALYSIS**\n* **Monthly Capital Leakage:** **${fuga_mensual:,.2f}**\n* **Annual Projected Leakage:** **${fuga_anual:,.2f}**\n\nYour current financial management is hemorrhaging potential wealth. Every second this capital remains unoptimized, your net worth stagnates. Stop using liquidity and start leveraging assets to fund your luxury lifestyle."
            elif niche == 'business':
                analisis = f"**QUANT REWARD PLAN: PREMIUM STRATEGY**\n\n### **CRITICAL FINANCIAL LEAKAGE ALERT**\n* **Monthly Capital Leakage:** **${fuga_mensual:,.2f}**\n* **Annual Projected Leakage:** **${fuga_anual:,.2f}**\n\n(Estimated loss from missed reward multipliers and lack of expenditure float). You are giving free money to the bank instead of financing your premium lifestyle and travel goals."
            else:
                analisis = f"**QUANT REWARD PLAN: STANDARD STRATEGY**\n\n### **CRITICAL LEAKAGE ANALYSIS**\n* **Monthly Capital Leakage:** **${fuga_mensual:,.2f}**\n* **Annual Projected Leakage:** **${fuga_anual:,.2f}**\n\nYou are spending significantly more than your optimized capacity. At this rate, your financial profile is losing value every month due to unmanaged credit and lack of rewards."
        else:
            if niche == 'elite':
                analisis = f"**QUANT REWARD PLAN: ESTRATEGIA ÉLITE**\n\n### **ANÁLISIS CRÍTICO DE FUGA DE CAPITAL**\n* **Fuga de Capital Mensual:** **${fuga_mensual:,.2f}**\n* **Fuga Proyectada Anual:** **${fuga_anual:,.2f}**\n\nTu gestión financiera actual está desangrando riqueza potencial. Cada segundo que este capital permanece sin optimizar, tu patrimonio neto se estanca. Deja de usar liquidez y empieza a apalancar activos."
            elif niche == 'business':
                analisis = f"**QUANT REWARD PLAN: ESTRATEGIA PREMIUM**\n\n### **ALERTA CRÍTICA DE FUGA FINANCIERA**\n* **Fuga de Capital Mensual:** **${fuga_mensual:,.2f}**\n* **Fuga Proyectada Anual:** **${fuga_anual:,.2f}**\n\n(Pérdida estimada por multiplicadores de recompensas omitidos y falta de estrategia). Le estás regalando dinero al banco en lugar de financiar tu estilo de vida premium y viajes."
            else:
                analisis = f"**QUANT REWARD PLAN: ESTRATEGIA ESTÁNDAR**\n\n### **ANÁLISIS CRÍTICO DE FUGA**\n* **Fuga de Capital Mensual:** **${fuga_mensual:,.2f}**\n* **Fuga Proyectada Anual:** **${fuga_anual:,.2f}**\n\nEstás gastando sin estrategia. A este ritmo, tu perfil financiero pierde valor cada mes por no aprovechar las recompensas que te pertenecen por derecho."
        
        return {"analisis": analisis}

@app.post("/contacto")
async def guardar_contacto(nombre: str = Form(...), email: str = Form(...), mensaje: str = Form(...)):
    # 1. Guardar en CSV local
    try:
        file_exists = os.path.isfile("mensajes_contacto.csv")
        with open("mensajes_contacto.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Fecha", "Nombre", "Email", "Mensaje"])
            writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), nombre, email, mensaje])
    except Exception as e:
        print(f"Error interno CSV Contacto: {e}")

    # 2. Intentar enviar correo de alerta (Si las variables existen en el .env)
    try:
        destinatario = os.getenv("CONTACT_EMAIL", "tenlonuevo@gmail.com")
        remitente = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")

        if remitente and password:
            msg = MIMEMultipart()
            msg['From'] = remitente
            msg['To'] = destinatario
            msg['Subject'] = f"Nuevo Mensaje de Soporte: {nombre}"
            body = f"Nombre: {nombre}\nEmail: {email}\nMensaje:\n{mensaje}"
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(remitente, password)
            server.send_message(msg)
            server.quit()
    except Exception as e:
        print(f"Aviso: No se pudo enviar el email (revisar credenciales SMTP). El mensaje se guardó en CSV. Detalle: {e}")

    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)