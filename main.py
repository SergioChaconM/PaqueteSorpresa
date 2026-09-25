from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from supabase import create_client, Client
from passlib.context import CryptContext
from datetime import date
from jose import JWTError, jwt
from dotenv import load_dotenv
import os

# 📍 Cargar variables de entorno
carpeta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_env = os.path.join(carpeta_actual, ".env")
load_dotenv(dotenv_path=ruta_env)

# 🔑 Leer credenciales
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
ALGORITHM = "HS256"
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")

# Validar credenciales
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ ERROR: No se encontraron credenciales de Supabase")
    exit(1)

# ✅ Inicializar API
app = FastAPI(title="API Paquete Sorpresa", version="2.1-Segura")

# 🔒 Cifrado de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🌐 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔗 Conexión a Supabase
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# 📂 Servir archivos estáticos
CARPETA_PUBLICA = os.path.join(carpeta_actual, "public")
os.makedirs(CARPETA_PUBLICA, exist_ok=True)
app.mount("/estatico", StaticFiles(directory=CARPETA_PUBLICA), name="archivos_estaticos")

# ==================================================
# 🔒 SEGURIDAD — Autenticación con JWT de Supabase
# ==================================================
security = HTTPBearer()

class UsuarioActual(BaseModel):
    id: str
    email: str | None = None
    rol: str = "usuario"

async def obtener_usuario_actual(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UsuarioActual:
    """Valida el token JWT enviado desde el frontend"""
    credenciales_invalidas = HTTPException(
        status_code=401,
        detail="Token inválido o expirado — inicia sesión primero",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SUPABASE_JWT_SECRET:
        print("⚠️ SUPABASE_JWT_SECRET no configurado — saltando validación")
        return UsuarioActual(id="desarrollo", email="dev@local", rol="admin")
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"verify_aud": False}
        )
        usuario_id = payload.get("sub")
        if not usuario_id:
            raise credenciales_invalidas
        
        rol = payload.get("app_metadata", {}).get("rol", "usuario")
        email = payload.get("email")
        return UsuarioActual(id=usuario_id, email=email, rol=rol)
    except JWTError:
        raise credenciales_invalidas

async def solo_admin(usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    """Restringe acceso solo a usuarios con rol 'admin'"""
    if usuario.rol != "admin":
        raise HTTPException(
            status_code=403,
            detail="Se requiere permiso de administrador"
        )
    return usuario

# ==================================================
# 📋 ESQUEMAS DE VALIDACIÓN
# ==================================================
class EmpresaCreate(BaseModel):
    NIT: str
    Razon_Social: str = Field(..., alias="Nombre Legal")
    Nombre_Comercial: str | None = Field(None, alias="Nombre Comercial")
    Direccion: str | None = None
    Telefono: str | None = None
    Correo: str | None = None
    Activa: int = 1

class EmpresaUpdate(BaseModel):
    NIT: str | None = None
    Razon_Social: str | None = Field(None, alias="Nombre Legal")
    Nombre_Comercial: str | None = Field(None, alias="Nombre Comercial")
    Direccion: str | None = None
    Telefono: str | None = None
    Correo: str | None = None
    Activa: int | None = None

class SucursalCreate(BaseModel):
    NIT: str
    Sucursal: int | None = None
    Localización: str = Field(..., alias="Localización")
    Contacto: str | None = None
    Celular: int | None = None
    Correo: str | None = None
    activa: int = 1
    Contraseña: str | None = None

class SucursalUpdate(SucursalCreate):
    NIT: str | None = None
    Sucursal: int | None = None

class HorarioEntregaCreate(BaseModel):
    nit: str
    sucursal: int
    grupo: int
    entrega: str | None = None

class HorarioEntregaUpdate(BaseModel):
    entrega: str | None = None

class PaqueteOfertonCreate(BaseModel):
    NIT: str
    Sucursal: int
    IDPaquete: int
    secuencia: int
    Productos: str
    PrecioNormal: float
    PrecioOferton: float
    Estado: str = "D"
    Grupo: int
    disponible: int = 1
    DiaPromocion: str | None = None
    detalle: str | None = None

class PaqueteOfertonUpdate(BaseModel):
    Productos: str | None = None
    secuencia: int | None = None
    PrecioNormal: float | None = None
    PrecioOferton: float | None = None
    Estado: str | None = None
    Grupo: int | None = None
    disponible: int | None = None
    DiaPromocion: str | None = None
    detalle: str | None = None

class AlimentoCreate(BaseModel):
    variedad: str

class AlimentoUpdate(BaseModel):
    variedad: str | None = None

# ==================================================
# 🏠 RUTAS PÚBLICAS — Sin token, acceso directo
# ==================================================


@app.get("/")
def raiz():
    return RedirectResponse(url="/estatico/index.html")

@app.get("/api/public/empresas")
def listar_empresas_publicas(supabase: Client = Depends(get_supabase)):
    try:
        respuesta = supabase.table("Empresa").select("*").order('"Nombre Legal"', desc=False).execute()
        return {"datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/public/sucursales")
def listar_sucursales_publicas(nit: str | None = None, supabase: Client = Depends(get_supabase)):
    try:
        consulta = supabase.table("Sucursal").select("*")
        if nit:
            consulta = consulta.eq("NIT", nit)
        respuesta = consulta.order("Sucursal").execute()
        return {"datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/public/horarios")
def listar_horarios_publicos(
    nit: str | None = None,
    sucursal: int | None = None,
    supabase: Client = Depends(get_supabase)
):
    try:
        consulta = supabase.table("HorarioEntrega").select("*")
        if nit: consulta = consulta.eq("nit", nit)
        if sucursal is not None: consulta = consulta.eq("sucursal", sucursal)
        respuesta = consulta.order("grupo").execute()
        return {"datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/public/alimentos")
def listar_alimentos_publicos(supabase: Client = Depends(get_supabase)):
    try:
        respuesta = supabase.table("alimento").select("*").order("secuencia").execute()
        return {"datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/public/sucursal-datos")
def obtener_datos_sucursal_publica(
    nit: str,
    sucursal: int,
    supabase: Client = Depends(get_supabase)
):
    try:
        respuesta = supabase.table("Sucursal").select("*").eq("NIT", nit).eq("Sucursal", sucursal).execute()
        return {"datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/public/paquetes-oferton/siguiente-id")
def siguiente_id_paquete_publico(
    nit: str, sucursal: int,
    supabase: Client = Depends(get_supabase)
):
    try:
        respuesta = supabase.table("PaqueteOferton")\
            .select("IDPaquete")\
            .eq("NIT", nit)\
            .eq("Sucursal", sucursal)\
            .execute()
        siguiente = 1
        if respuesta.data and len(respuesta.data) > 0:
            ids = [fila["IDPaquete"] for fila in respuesta.data]
            siguiente = max(ids) + 1
        return {"siguiente_id": siguiente}
    except Exception as e:
        print(f"🔴 ERROR siguiente-id: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/public/paquetes-oferton")
def listar_paquetes_publicos(
    nit: str,
    sucursal: int,
    supabase: Client = Depends(get_supabase)
):
    try:
        respuesta = supabase.table("PaqueteOferton").select("*").execute()
        filtrados = []
        for fila in (respuesta.data or []):
            fila_nit = fila.get("NIT") or fila.get("nit")
            fila_suc = fila.get("Sucursal") or fila.get("sucursal")
            if str(fila_nit) == str(nit) and int(fila_suc) == int(sucursal):
                filtrados.append(fila)
        filtrados.sort(key=lambda x: x.get("IDPaquete") or 0)
        return {"datos": filtrados}
    except Exception as e:
        print(f"🔴 ERROR: {type(e).__name__} - {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/public/paquetes-oferton")
def crear_paquete_publico(
    datos: PaqueteOfertonCreate,
    supabase: Client = Depends(get_supabase)
):
    try:
        respuesta = supabase.table("PaqueteOferton").insert(datos.model_dump()).execute()
        return {"mensaje": "Paquete registrado ✅", "datos": respuesta.data[0]}
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower() or "23505" in error_msg:
            raise HTTPException(status_code=409, detail="El ID de paquete ya existe para esta sucursal")
        raise HTTPException(status_code=500, detail=error_msg)

# ==================================================
# 🍽️ ALIMENTOS POR EMPRESA — PÚBLICA
# ==================================================
@app.get("/api/public/alimentos-por-empresa")
def listar_alimentos_por_empresa(
    nit: str,
    supabase: Client = Depends(get_supabase)
):
    try:
        # PASO 1: Obtener los números de secuencia asociados a la empresa
        resp_asoc = supabase.table("empresalimento")\
            .select("secuencia")\
            .eq("NIT", nit)\
            .order("secuencia")\
            .execute()
        
        lista_secuencias = [fila["secuencia"] for fila in resp_asoc.data]
        
        if not lista_secuencias:
            return {"datos": []}
        
        # PASO 2: Obtener los nombres desde la tabla alimento
        resp_nombres = supabase.table("alimento")\
            .select("secuencia, variedad")\
            .in_("secuencia", lista_secuencias)\
            .order("secuencia")\
            .execute()
        
        return {"datos": resp_nombres.data}
        
    except Exception as e:
        print("❌ ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================================================
# 🏢 EMPRESAS — PROTEGIDAS (requieren sesión)
# ==================================================
@app.get("/api/public/empresas")
def listar_empresas_publica(
    supabase: Client = Depends(get_supabase)
):
    try:
        respuesta = supabase.table("Empresa")\
            .select("*")\
            .order('"Nombre Legal"', desc=False)\
            .execute()
        return {"datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/empresas/{nit}")
def obtener_empresa(
    nit: str,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("Empresa").select("*").eq('"NIT"', nit).single().execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/empresas")
def crear_empresa(
    datos: EmpresaCreate,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        datos_insertar = datos.model_dump(by_alias=True, exclude_unset=True)
        respuesta = supabase.table("Empresa").insert(datos_insertar).execute()
        return {"mensaje": "Empresa creada ✅", "datos": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/empresas/{nit}")
def actualizar_empresa(
    nit: str,
    datos: EmpresaUpdate,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        datos_actualizar = datos.model_dump(by_alias=True, exclude_unset=True)
        respuesta = supabase.table("Empresa").update(datos_actualizar).eq("NIT", nit).execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        return {"mensaje": "Empresa actualizada ✅", "datos": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/empresas/{nit}")
def eliminar_empresa(
    nit: str,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(solo_admin)
):
    try:
        respuesta = supabase.table("Empresa").delete().eq("NIT", nit).execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        return {"mensaje": "Empresa eliminada ✅"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================================================
# 🏪 SUCURSALES — PROTEGIDAS
# ==================================================
@app.get("/api/sucursales")
def listar_sucursales(
    nit: str | None = None,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        consulta = supabase.table("Sucursal").select("*")
        if nit: consulta = consulta.eq("NIT", nit)
        respuesta = consulta.order("Sucursal").execute()
        return {"datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sucursales/siguiente-numero")
def siguiente_numero_sucursal(
    nit: str,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("Sucursal").select("Sucursal", count="exact", head=True).eq("NIT", nit)
        return {"siguiente_numero": (respuesta.count or 0) + 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sucursales/{nit}/{numero}")
def obtener_sucursal(
    nit: str, numero: int,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("Sucursal").select("*").eq("NIT", nit).eq("Sucursal", numero).single().execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Sucursal no encontrada")
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sucursales")
def crear_sucursal(
    datos: SucursalCreate,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        datos_insertar = datos.model_dump(by_alias=True, exclude_unset=True)
        if datos_insertar.get("Contraseña"):
            if len(datos_insertar["Contraseña"]) < 8:
                raise HTTPException(status_code=400, detail="Contraseña mínimo 8 caracteres")
            datos_insertar["Contraseña"] = pwd_context.hash(datos_insertar["Contraseña"])
        else:
            raise HTTPException(status_code=400, detail="La contraseña es obligatoria")
        respuesta = supabase.table("Sucursal").insert(datos_insertar).execute()
        return {"mensaje": "Sucursal creada ✅", "datos": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/sucursales/{nit}/{numero}")
def actualizar_sucursal(
    nit: str, numero: int,
    datos: SucursalUpdate,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        datos_actualizar = datos.model_dump(by_alias=True, exclude_unset=True)
        if datos_actualizar.get("Contraseña"):
            if len(datos_actualizar["Contraseña"]) < 8:
                raise HTTPException(status_code=400, detail="Contraseña mínimo 8 caracteres")
            datos_actualizar["Contraseña"] = pwd_context.hash(datos_actualizar["Contraseña"])
        else:
            datos_actualizar.pop("Contraseña", None)
        respuesta = supabase.table("Sucursal").update(datos_actualizar).eq("NIT", nit).eq("Sucursal", numero).execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Sucursal no encontrada")
        return {"mensaje": "Sucursal actualizada ✅", "datos": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sucursales/{nit}/{numero}")
def eliminar_sucursal(
    nit: str, numero: int,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(solo_admin)
):
    try:
        respuesta = supabase.table("Sucursal").delete().eq("NIT", nit).eq("Sucursal", numero).execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Sucursal no encontrada")
        return {"mensaje": "Sucursal eliminada ✅"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================================================
# 🕒 HORARIOS — PROTEGIDAS
# ==================================================
@app.get("/api/horarios")
def listar_horarios(
    nit: str | None = None,
    sucursal: int | None = None,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        consulta = supabase.table("HorarioEntrega").select("*")
        if nit: consulta = consulta.eq("nit", nit)
        if sucursal is not None: consulta = consulta.eq("sucursal", sucursal)
        respuesta = consulta.order("grupo").execute()
        return {"datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/horarios")
def crear_horario(
    datos: HorarioEntregaCreate,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("HorarioEntrega").insert(datos.model_dump()).execute()
        return {"mensaje": "Horario registrado ✅", "datos": respuesta.data[0]}
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower() or "23505" in error_msg:
            raise HTTPException(status_code=409, detail=f"El Grupo {datos.grupo} ya existe para esta sucursal")
        raise HTTPException(status_code=500, detail=error_msg)

@app.put("/api/horarios/{nit}/{sucursal}/{grupo}")
def actualizar_horario(
    nit: str, sucursal: int, grupo: int,
    datos: HorarioEntregaUpdate,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("HorarioEntrega").update(datos.model_dump(exclude_unset=True)).eq("nit", nit).eq("sucursal", sucursal).eq("grupo", grupo).execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        return {"mensaje": "Horario actualizado ✅", "datos": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/horarios/{nit}/{sucursal}/{grupo}")
def eliminar_horario(
    nit: str, sucursal: int, grupo: int,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(solo_admin)
):
    try:
        respuesta = supabase.table("HorarioEntrega").delete().eq("nit", nit).eq("sucursal", sucursal).eq("grupo", grupo).execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        return {"mensaje": "Horario eliminado ✅"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================================================
# 🎁 PAQUETES OFERTÓN — PROTEGIDAS
# ==================================================
@app.get("/api/paquetes-oferton/siguiente-id")
def siguiente_id_paquete(
    nit: str, sucursal: int,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("PaqueteOferton")\
            .select("IDPaquete")\
            .eq("NIT", nit)\
            .eq("Sucursal", sucursal)\
            .execute()
        siguiente = 1
        if respuesta.data and len(respuesta.data) > 0:
            ids = [fila["IDPaquete"] for fila in respuesta.data]
            siguiente = max(ids) + 1
        return {"siguiente_id": siguiente}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/paquetes-oferton")
def listar_paquetes(
    nit: str, sucursal: int,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("PaqueteOferton")\
            .select("*")\
            .eq("NIT", nit)\
            .eq("Sucursal", sucursal)\
            .execute()
        datos = respuesta.data or []
        datos.sort(key=lambda x: x.get("IDPaquete", 0))
        return {"datos": datos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/paquetes-oferton")
def crear_paquete(
    datos: PaqueteOfertonCreate,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("PaqueteOferton").insert(datos.model_dump()).execute()
        return {"mensaje": "Paquete registrado ✅", "datos": respuesta.data[0]}
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower() or "23505" in error_msg:
            raise HTTPException(status_code=409, detail="El ID de paquete ya existe para esta sucursal")
        raise HTTPException(status_code=500, detail=error_msg)

@app.put("/api/paquetes-oferton/{nit}/{sucursal}/{idpaquete}")
def actualizar_paquete(
    nit: str, sucursal: int, idpaquete: int,
    datos: PaqueteOfertonUpdate,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("PaqueteOferton")\
            .update(datos.model_dump(exclude_unset=True))\
            .eq("NIT", nit)\
            .eq("Sucursal", sucursal)\
            .eq("IDPaquete", idpaquete)\
            .execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Paquete no encontrado")
        return {"mensaje": "Paquete actualizado ✅", "datos": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/paquetes-oferton/{nit}/{sucursal}/{idpaquete}")
def eliminar_paquete(
    nit: str, sucursal: int, idpaquete: int,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(solo_admin)
):
    try:
        respuesta = supabase.table("PaqueteOferton")\
            .delete()\
            .eq("NIT", nit)\
            .eq("Sucursal", sucursal)\
            .eq("IDPaquete", idpaquete)\
            .execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Paquete no encontrado")
        return {"mensaje": "Paquete eliminado ✅"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/paquetes-oferton/anteriores")
def listar_paquetes_anteriores(
    nit: str, sucursal: int,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        hoy = date.today().isoformat()
        respuesta = supabase.table("PaqueteOferton")\
            .select("IDPaquete, Productos, PrecioNormal, PrecioOferton, DiaPromoción, detalle, disponible")\
            .eq("NIT", nit)\
            .eq("Sucursal", sucursal)\
            .eq("Estado", "D")\
            .lt("DiaPromoción", hoy)\
            .execute()
        datos = respuesta.data or []
        datos.sort(key=lambda x: x.get("DiaPromoción", ""), reverse=True)
        return {"datos": datos, "fecha_hoy": hoy}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/paquetes-oferton/reactivar/{nit}/{sucursal}/{idpaquete}")
def reactivar_paquete(
    nit: str, sucursal: int, idpaquete: int,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        hoy = date.today().isoformat()
        respuesta = supabase.table("PaqueteOferton")\
            .update({"DiaPromoción": hoy})\
            .eq("NIT", nit)\
            .eq("Sucursal", sucursal)\
            .eq("IDPaquete", idpaquete)\
            .execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Paquete no encontrado")
        return {"mensaje": "Paquete reactivado ✅", "datos": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/paquetes-oferton/actualizar-precio/{nit}/{sucursal}/{idpaquete}")
def actualizar_precio(
    nit: str, sucursal: int, idpaquete: int, nuevo_precio: float,
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        respuesta = supabase.table("PaqueteOferton")\
            .update({"PrecioOferton": nuevo_precio})\
            .eq("NIT", nit)\
            .eq("Sucursal", sucursal)\
            .eq("IDPaquete", idpaquete)\
            .execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Paquete no encontrado")
        return {"mensaje": "Precio actualizado ✅", "datos": respuesta.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================================================
# 🍽️ ALIMENTOS
# ==================================================
@app.get("/api/alimentos")
def listar_alimentos(supabase: Client = Depends(get_supabase)):
    try:
        respuesta = supabase.table("alimento").select("*").order("secuencia").execute()
        return {"datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alimentos")
def crear_alimento(
    datos: AlimentoCreate,
    supabase: Client = Depends(get_supabase),
):
    try:
        res_max = supabase.table("alimento").select("secuencia").order("secuencia", desc=True).limit(1).execute()
        siguiente_secuencia = 1 if not res_max.data or len(res_max.data) == 0 else res_max.data[0]["secuencia"] + 1
        registro = {"secuencia": siguiente_secuencia, "variedad": datos.variedad}
        respuesta = supabase.table("alimento").insert(registro).execute()
        return {"mensaje": "Alimento creado ✅", "datos": respuesta.data[0]}
    except Exception as e:
        print(f"🔴 Error crear alimento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/alimentos/{secuencia}")
def actualizar_alimento(
    secuencia: int, datos: AlimentoUpdate,
    supabase: Client = Depends(get_supabase),
):
    try:
        respuesta = supabase.table("alimento").update(datos.model_dump(exclude_unset=True)).eq("secuencia", secuencia).execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Alimento no encontrado")
        return {"mensaje": "Alimento actualizado ✅", "datos": respuesta.data[0]}
    except Exception as e:
        print(f"🔴 Error actualizar alimento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/alimentos/{secuencia}")
def eliminar_alimento(
    secuencia: int,
    supabase: Client = Depends(get_supabase),
):
    try:
        respuesta = supabase.table("alimento").delete().eq("secuencia", secuencia).execute()
        if not respuesta.data:
            raise HTTPException(status_code=404, detail="Alimento no encontrado")
        return {"mensaje": "Alimento eliminado ✅"}
    except Exception as e:
        print(f"🔴 Error eliminar alimento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================================================
# 📊 SUCURSALES CON PAQUETES ANTERIORES
# ==================================================
@app.get("/api/sucursales-con-paquetes-anteriores")
def listar_sucursales_paquetes_anteriores(
    supabase: Client = Depends(get_supabase),
    _: UsuarioActual = Depends(obtener_usuario_actual)
):
    try:
        hoy = date.today().isoformat()
        res_paquetes = supabase.table("PaqueteOferton").select("NIT, Sucursal, IDPaquete, Estado").lt("DiaPromoción", hoy).execute()
        paquetes_todos = res_paquetes.data or []
        paquetes = [p for p in paquetes_todos if str(p.get("Estado","")).strip() == "D"]
        if not paquetes:
            return {"datos": [], "fecha_hoy": hoy}
        nits_unicos = list({p["NIT"] for p in paquetes})
        res_empresas = supabase.table("Empresa").select(NIT, '"Nombre Comercial"', '"Nombre Legal"').in_("NIT", nits_unicos).execute()
        empresas = res_empresas.data or []
        res_sucursales = supabase.table("Sucursal").select("NIT, Sucursal, Localización").execute()
        sucursales = res_sucursales.data or []
        mapa_empresas = {e["NIT"]: ((e.get("Nombre Comercial") or "").strip() or (e.get("Nombre Legal") or "").strip() or "Sin nombre") for e in empresas}
        mapa_sucursales = {(s["NIT"], s["Sucursal"]): (s.get("Localización") or "").strip() or "Sin ubicación" for s in sucursales}
        agrupado = {}
        for p in paquetes:
            clave = (p["NIT"], p["Sucursal"])
            if clave not in agrupado:
                agrupado[clave] = {"nit": p["NIT"], "sucursal": p["Sucursal"], "nombre_comercial": mapa_empresas.get(p["NIT"], "Sin nombre"), "localizacion": mapa_sucursales.get(clave, "Sin ubicación"), "total_paquetes": 0}
            agrupado[clave]["total_paquetes"] += 1
        return {"datos": list(agrupado.values()), "fecha_hoy": hoy}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================================================
# 📄 SERVIR PÁGINAS
# ==================================================
@app.get("/{nombre_pagina}")
def servir_pagina(nombre_pagina: str):
    if "." not in nombre_pagina:
        return RedirectResponse(url=f"/estatico/{nombre_pagina}.html")
    ruta_completa = os.path.join(CARPETA_PUBLICA, nombre_pagina)
    if os.path.exists(ruta_completa):
        return FileResponse(ruta_completa)
    return {"error": f"Página '{nombre_pagina}' no encontrada"}

if __name__ == "__main__":
    import uvicorn
    puerto = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=puerto)