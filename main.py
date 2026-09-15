from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# 📍 Definimos EXACTAMENTE dónde está el .env
carpeta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_env = os.path.join(carpeta_actual, ".env")

print(f"📁 Buscando en: {ruta_env}")
print(f"✅ Archivo existe: {os.path.exists(ruta_env)}")

# ✅ Cargamos desde la ruta EXACTA
load_dotenv(dotenv_path=ruta_env)

# Leemos los valores
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# 🧪 Verificación
print("\n🔍 VALORES CARGADOS:")
print(f"  SUPABASE_URL: {'✅ ' + SUPABASE_URL if SUPABASE_URL else '❌ NO ENCONTRADO'}")
print(f"  SUPABASE_ANON_KEY: {'✅ ' + SUPABASE_ANON_KEY[:25] + '...' if SUPABASE_ANON_KEY else '❌ NO ENCONTRADO'}")

# ❌ Detener si faltan valores
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("\n❌ ERROR: No se pudieron leer las variables.")
    print("👉 Revisa que dentro del archivo .env no haya espacios alrededor del =")
    exit(1)

# ✅ Todo listo, arrancamos
app = FastAPI(title="API de Mi Proyecto")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@app.get("/")
def raiz():
    return {"mensaje": "✅ API funcionando y conectada a Supabase"}

@app.get("/paquetes")
def obtener_paquetes():
    respuesta = supabase.table("paquetes").select("*").execute()
    return {"datos": respuesta.data}

@app.get("/empresas")
def obtener_empresas():
    respuesta = supabase.table("empresas").select("*").execute()
    return {"datos": respuesta.data}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Servir archivos HTML en la raíz
@app.get("/{nombre_pagina}")
def servir_pagina(nombre_pagina: str):
    if os.path.exists(nombre_pagina):
        return FileResponse(nombre_pagina)
    return {"error": "Página no encontrada"}

# Página principal
@app.get("/paginas/{nombre}")
def ver_pagina(nombre: str):
    ruta = f"{nombre}.html"
    if os.path.exists(ruta):
        return FileResponse(ruta)
    return {"error": "Página no encontrada"}