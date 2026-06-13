import os
import csv
import time
import tempfile
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

# Función: Python ahora es el dueño y servidor de tu página web
@app.get("/")
async def serve_frontend():
    # Busca el archivo index.html en la carpeta frontend (un nivel atrás del backend)
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=404, detail="Archivo index.html no encontrado.")
    return FileResponse(frontend_path)

# Función: Permiso para mostrar el Favicon (Escudo dorado)
@app.get("/favicon.png")
async def serve_favicon():
    favicon_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "favicon.png")
    if not os.path.exists(favicon_path):
        raise HTTPException(status_code=404, detail="Archivo favicon.png no encontrado.")
    return FileResponse(favicon_path)

@app.post("/analizar-estado")
async def analizar_estado(email: str = Form(...), niche: str = Form(...), lang: str = Form(...), file: UploadFile = File(...)):
    
    try:
        file_exists = os.path.isfile("leads.csv")
        with open("leads.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Fecha", "Email", "Perfil"])
            writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), email, niche])
    except Exception as e:
        print(f"Error interno CSV: {e}")

    temp_file_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        documento = client.files.upload(file=temp_file_path)
        
        # LÓGICA BILINGÜE ESTRICTA BASADA EN LA BANDERA SELECCIONADA
        idioma_instruccion = "ESTRICTAMENTE EN INGLÉS (Strictly in English)" if lang == 'en' else "ESTRICTAMENTE EN ESPAÑOL"
        
        prompt = f"""Actúa como Quant Reward Plan.
Analiza este estado de cuenta para el perfil financiero: {niche.upper()}.
REGLAS ESTRICTAS E INQUEBRANTABLES: 
1. IDIOMA OBLIGATORIO: DEBES generar todo el reporte {idioma_instruccion}. Ignora el idioma del documento original.
2. Privacidad total: Ignora y no menciones ningún dato personal, nombre o número de cuenta.
3. Genera urgencia: Calcula y muestra al usuario la fuga de capital a nivel Mensual y Anual.
4. Si el perfil es 'PERSONAL' (Estrategia Estándar): Enfoca el reporte en la URGENCIA de reparar su historial crediticio, obtener una tarjeta básica asegurada, y optimizar gastos en autos esenciales y viajes económicos. NO menciones bienes raíces ni hipotecas.
5. Si el perfil es 'BUSINESS' (Estrategia Premium): Enfoca el reporte en hacer un upgrade a tarjetas premium (Chase/Amex), implementar monitoreo de crédito avanzado, y refinanciar autos a tasas premium.
6. Si el perfil es 'ELITE' (Estrategia Élite): Enfoca el reporte en la gestión de alto patrimonio, adquisición de hipotecas Jumbo, automatización de inversiones, y conserjería para jets privados.
7. Sé directo, persuasivo y estructurado en viñetas (bullet points) breves."""
        
        respuesta = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[prompt, documento]
        )
        
        client.files.delete(name=documento.name)
        
        return {"analisis": respuesta.text}
        
    except Exception as e:
        print(f"ERROR CRÍTICO EN IA: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno en IA. Revisa la consola de VS Code para más detalles.")
        
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# Función: Guardar mensajes del formulario de contacto
@app.post("/contacto")
async def guardar_contacto(nombre: str = Form(...), email: str = Form(...), mensaje: str = Form(...)):
    try:
        file_exists = os.path.isfile("mensajes_contacto.csv")
        with open("mensajes_contacto.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Fecha", "Nombre", "Email", "Mensaje"])
            writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), nombre, email, mensaje])
        return {"status": "success"}
    except Exception as e:
        print(f"Error guardando contacto: {e}")
        raise HTTPException(status_code=500, detail="Error interno guardando el mensaje.")

if __name__ == "__main__":
    import uvicorn
    # Ajuste CRÍTICO para Railway: Puerto dinámico y host 0.0.0.0
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)