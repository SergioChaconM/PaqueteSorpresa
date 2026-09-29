import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware
from datetime import date

# Cargar variables de entorno
load_dotenv()

# Instancia de FastAPI
app = FastAPI(title="Sistema Empresa-Sucursal")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Credenciales Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

print("🔍 URL Supabase:", SUPABASE_URL if SUPABASE_URL else "❌ Faltante")
print("🔍 Clave Anon:", "✅ Cargada" if SUPABASE_ANON_KEY else "❌ Faltante")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("❌ Completa SUPABASE_URL y SUPABASE_ANON_KEY en .env")

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Archivos estáticos y plantillas
CARPETA_PUBLICA = "public"
os.makedirs(CARPETA_PUBLICA, exist_ok=True)
app.mount("/estatico", StaticFiles(directory=CARPETA_PUBLICA), name="archivos_estaticos")
templates = Jinja2Templates(directory="templates")

# ==============================================
# PÁGINAS HTML
# ==============================================
@app.get("/", response_class=HTMLResponse)
async def pagina_principal(request: Request):
    return templates.TemplateResponse(request, "index.html", {})

@app.get("/NITSucursal", response_class=HTMLResponse)
async def pagina_nitsucursal(request: Request):
    return templates.TemplateResponse(request, "NITSucursal.html", {})

@app.get("/SucursalesConPaquetesAnteriores", response_class=HTMLResponse)
async def pagina_sucursales_paquetes(request: Request):
    return templates.TemplateResponse(request, "SucursalesConPaquetesAnteriores.html", {})

@app.get("/MantenimientoEmpresa", response_class=HTMLResponse)
async def pagina_mant_empresa(request: Request):
    return templates.TemplateResponse(request, "MantenimientoEmpresa.html", {})

@app.get("/NIT", response_class=HTMLResponse)
async def pagina_nit(request: Request):
    return templates.TemplateResponse(request, "NIT.html", {})

@app.get("/NITSucursalPaquete", response_class=HTMLResponse)
async def pagina_nit_suc_paq(request: Request):
    return templates.TemplateResponse(request, "NITSucursalPaquete.html", {})

@app.get("/MantenimientoAlimentos", response_class=HTMLResponse)
async def pagina_mant_alimentos(request: Request):
    return templates.TemplateResponse(request, "MantenimientoAlimentos.html", {})

# ==============================================
# API — Paquetes anteriores
# ==============================================
@app.get("/api/sucursales-con-paquetes-anteriores")
def listar_sucursales_paquetes_anteriores(supabase: Client = Depends(get_supabase)):
    try:
        hoy = date.today()
        hoy_iso = hoy.isoformat()

        nombres_meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        fecha_formateada = f"{hoy.day} {nombres_meses[hoy.month]} {hoy.year}"

        # 1. Paquetes finalizados
        res_paquetes = supabase.table("PaqueteOferton")\
            .select("NIT, Sucursal, IDPaquete, Estado, DiaPromocion")\
            .lt("DiaPromocion", hoy_iso)\
            .execute()
        paquetes = [p for p in (res_paquetes.data or []) if str(p.get("Estado","")).strip() == "D"]

        if not paquetes:
            return {"datos": [], "fecha_hoy": hoy_iso, "fecha_formateada": fecha_formateada}

        # 2. Empresas
        nits_unicos = list({p["NIT"] for p in paquetes})
        res_emp = supabase.table("Empresa")\
            .select('"NIT", "Nombre Comercial", "Nombre Legal"')\
            .in_("NIT", nits_unicos)\
            .execute()
        empresas = res_emp.data or []

        mapa_emp = {}
        for e in empresas:
            clave_nit = str(e.get("NIT", "")).strip()
            nombre_comercial = (e.get("Nombre Comercial") or e.get('"Nombre Comercial"', "")).strip()
            nombre_legal = (e.get("Nombre Legal") or e.get('"Nombre Legal"', "")).strip()
            mapa_emp[clave_nit] = nombre_comercial or nombre_legal or "Sin nombre"

        # 3. Sucursales — probamos con formato exacto con comillas
        sucursales = []
        for nombre_tabla in ['"Sucursal"', "Sucursal", "sucursal"]:
            try:
                res = supabase.table(nombre_tabla).select("*").execute()
                if res.data:
                    sucursales = res.data
                    print(f"✅ TABLA ENCONTRADA: {nombre_tabla} → {len(sucursales)} filas")
                    for s in sucursales:
                        print(f"   → Fila: {s}")
                    break
            except Exception as e:
                print(f"❌ {nombre_tabla}: {e}")

        if not sucursales:
            print("⚠️ No se encontró la tabla con ningún nombre")

        # 4. Cruce
        resultado = []
        for p in paquetes:
            p_nit = str(p["NIT"]).strip()
            p_suc = str(p["Sucursal"]).strip()
            ubicacion = "Sin ubicación"

            for s in sucursales:
                s_nit = str(s.get("NIT", "")).strip()
                s_suc = str(s.get("Sucursal", "")).strip()
                if s_nit == p_nit and s_suc == p_suc:
                    ubicacion = (s.get("Localización", "") or "Sin ubicación").strip()
                    print(f"✅ Coincidencia: NIT={p_nit}, Suc={p_suc} → {ubicacion}")
                    break

            resultado.append({
                "nit": p["NIT"],
                "sucursal": p["Sucursal"],
                "nombre_comercial": mapa_emp.get(p_nit, "Sin nombre"),
                "localizacion": ubicacion,
                "total_paquetes": 1
            })

        return {
            "datos": resultado,
            "fecha_hoy": hoy_iso,
            "fecha_formateada": fecha_formateada
        }
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/SucursalesConPaquetesAnteriores.html", response_class=HTMLResponse)
async def pagina_sucursales_paquetes_html(request: Request):
    return templates.TemplateResponse(request, "SucursalesConPaquetesAnteriores.html", {})

# ==============================================
# Ejecución
# ==============================================
if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Servidor: http://127.0.0.1:8000")
    print("📄 Principal: http://127.0.0.1:8000/")
    print("📄 Paquetes ant: http://127.0.0.1:8000/SucursalesConPaquetesAnteriores")
    print("🔌 API: http://127.0.0.1:8000/api/sucursales-con-paquetes-anteriores\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)