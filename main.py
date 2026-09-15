from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

# 🏠 Ruta de bienvenida
@app.get("/")
def raiz():
    return {"mensaje": "✅ API funcionando y conectada a Supabase"}

# 📦 Datos
@app.get("/paquetes")
def obtener_paquetes():
    respuesta = supabase.table("paquetes").select("*").execute()
    return {"datos": respuesta.data}

@app.get("/empresas")
def obtener_empresas():
    respuesta = supabase.table("empresas").select("*").execute()
    return {"datos": respuesta.data}

# 🌐 SERVIR TUS PÁGINAS HTML ✨
@app.get("/{nombre_pagina}")
def servir_pagina(nombre_pagina: str):
    """Abre cualquier página: /index.html, /MantenimientoEmpresa.html ..."""
    if os.path.exists(nombre_pagina):
        return FileResponse(nombre_pagina)
    return {"error": f"Página '{nombre_pagina}' no encontrada"}