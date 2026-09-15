from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles  # ✅ Agregamos esto
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# 📍 Cargar variables de entorno
carpeta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_env = os.path.join(carpeta_actual, ".env")
load_dotenv(dotenv_path=ruta_env)

# 🔑 Leer credenciales
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# ❌ Detener si faltan credenciales
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("❌ ERROR: Faltan variables de entorno")
    exit(1)

# ✅ Inicializar API
app = FastAPI(title="API de Paquete Sorpresa")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔗 Conectar a Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# 📂 Servir archivos estáticos (HTML, CSS, JS) desde carpeta "public"
CARPETA_PUBLICA = os.path.join(carpeta_actual, "public")
os.makedirs(CARPETA_PUBLICA, exist_ok=True)
app.mount("/estatico", StaticFiles(directory=CARPETA_PUBLICA), name="archivos_estaticos")

# 🏠 Ruta raíz: redirigir al index.html
@app.get("/")
def raiz():
    return {
        "mensaje": "✅ API funcionando y conectada a Supabase",
        "documentacion": "https://paquetesorpresa.onrender.com/docs",
        "pagina_inicio": "https://paquetesorpresa.onrender.com/estatico/index.html"
    }

# 📦 Rutas de API
@app.get("/api/paquetes")
def obtener_paquetes():
    respuesta = supabase.table("paquetes").select("*").execute()
    return {"datos": respuesta.data}

@app.get("/api/empresas")
def obtener_empresas():
    respuesta = supabase.table("Empresa").select("*").order("Nombre Legal", desc=False).execute()
    return {"datos": respuesta.data}

# 🌐 Ruta amigable para páginas: /index.html → busca en carpeta public
@app.get("/{nombre_pagina}")
def servir_pagina(nombre_pagina: str):
    ruta_completa = os.path.join(CARPETA_PUBLICA, nombre_pagina)
    if os.path.exists(ruta_completa):
        return FileResponse(ruta_completa)
    return {"error": f"Página '{nombre_pagina}' no encontrada"}