# backend.py
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # <--- IMPORTANTE
from pydantic import BaseModel

app = FastAPI()

# --- 1. CONFIGURACIÓN CORS (OBLIGATORIO PARA PWA) ---
# Esto permite que tu Flet (puerto 8080) hable con FastAPI (puerto 9000)
origins = [
    "*"  # En producción, cambia esto por la URL de tu dominio
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Permite POST, GET, PUT, DELETE
    allow_headers=["*"],
)

# Base de datos simulada (Menú)
productos = [
    {"id": 1, "nombre": "Chilaquiles verdes", "precio": 95.0, "seccion": "Desayunos", "descripcion": "Totopos bañados en salsa verde con pollo deshebrado, crema y queso fresco."},
    {"id": 2, "nombre": "Molletes con pico de gallo", "precio": 72.0, "seccion": "Desayunos", "descripcion": "Pan bolillo con frijoles refritos, queso gratinado y pico de gallo fresco."},
    {"id": 3, "nombre": "Omelette de espinacas", "precio": 88.0, "seccion": "Desayunos", "descripcion": "Huevos batidos con espinacas, queso panela y toque de orégano."},
    {"id": 4, "nombre": "Ensalada César con pollo", "precio": 110.0, "seccion": "Comidas", "descripcion": "Lechuga romana, aderezo casero, crutones y pechuga de pollo a la plancha."},
    {"id": 5, "nombre": "Tacos de arrachera", "precio": 125.0, "seccion": "Comidas", "descripcion": "Tres tacos en tortilla de maíz con arrachera marinada, cebolla y cilantro."},
    {"id": 6, "nombre": "Hamburguesa clásica", "precio": 118.0, "seccion": "Comidas", "descripcion": "Carne de res, queso cheddar, jitomate, lechuga y aderezo de la casa."},
    {"id": 7, "nombre": "Sopa de lentejas", "precio": 76.0, "seccion": "Cenas", "descripcion": "Caldo casero con lentejas, zanahoria y especias reconfortantes."},
    {"id": 8, "nombre": "Sandwich de pavo y queso", "precio": 82.0, "seccion": "Cenas", "descripcion": "Pan integral con pavo al horno, queso gouda y verduras frescas."},
    {"id": 9, "nombre": "Crema de champiñones", "precio": 79.0, "seccion": "Cenas", "descripcion": "Crema suave de champiñones salteados con toque de nuez moscada."},
    {"id": 10, "nombre": "Cheesecake de frutos rojos", "precio": 68.0, "seccion": "Postres", "descripcion": "Rebanada cremosa con base de galleta y compota de frutos rojos."},
    {"id": 11, "nombre": "Brownie con helado", "precio": 64.0, "seccion": "Postres", "descripcion": "Brownie de chocolate tibio acompañado de helado de vainilla."},
    {"id": 12, "nombre": "Affogato de espresso", "precio": 58.0, "seccion": "Postres", "descripcion": "Helado de vainilla bañado con un espresso recién hecho."},
    {"id": 13, "nombre": "Café Americano", "precio": 25.0, "seccion": "Bebidas", "descripcion": "Clásico café americano con granos tostados medios."},
    {"id": 14, "nombre": "Capuchino", "precio": 35.0, "seccion": "Bebidas", "descripcion": "Espresso con leche vaporizada y espuma suave."},
    {"id": 15, "nombre": "Latte de vainilla", "precio": 38.0, "seccion": "Bebidas", "descripcion": "Doble espresso con leche cremosa y jarabe de vainilla."},
]

DB_FILE = Path(__file__).resolve().parent / "pedidos.db"

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                productos TEXT NOT NULL,
                total REAL NOT NULL,
                estado TEXT NOT NULL,
                modo TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()

_init_db()

# --- Modelos ---
class Pedido(BaseModel):
    productos: List[int]
    total: float = 0.0
    estado: str = "pendiente"
    modo: Optional[str] = None

class PedidoOffline(Pedido):
    temp_id: Optional[str] = None

class PedidoEstado(BaseModel):
    estado: str

class PedidosSync(BaseModel):
    pedidos: List[PedidoOffline]

# --- Helpers ---
def _producto_por_id(pid: int) -> Optional[Dict[str, object]]:
    return next((p for p in productos if p["id"] == pid), None)

def _serializar_pedido(data: Dict[str, object]) -> Dict[str, object]:
    nombres = []
    lista_ids = data["productos"] if isinstance(data["productos"], list) else []
    
    for pid in lista_ids:
        prod = _producto_por_id(pid)
        if prod:
            nombres.append(prod.get("nombre"))
    return {
        **data,
        "productos_nombres": nombres,
    }

def _row_to_pedido(row: sqlite3.Row) -> Dict[str, object]:
    productos_ids = []
    try:
        productos_ids = json.loads(row["productos"])
    except Exception:
        productos_ids = []
    return {
        "id": row["id"],
        "productos": productos_ids,
        "total": row["total"],
        "estado": row["estado"],
        "modo": row["modo"],
        "created_at": row["created_at"],
    }

def _insert_pedido(data: Pedido) -> int:
    with _get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO pedidos (productos, total, estado, modo, created_at) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                json.dumps(data.productos),
                float(data.total or 0),
                data.estado,
                data.modo,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        print(f"✅ Pedido guardado en DB. ID: {cur.lastrowid}") # LOG
        return int(cur.lastrowid)

def _update_estado(pedido_id: int, estado: str) -> bool:
    print(f"🔄 Intentando actualizar pedido {pedido_id} a {estado}") # LOG
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE pedidos SET estado = ? WHERE id = ?",
            (estado, pedido_id),
        )
        conn.commit()
        return cur.rowcount > 0

def _get_pedido(pedido_id: int) -> Optional[Dict[str, object]]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
        if not row:
            return None
        return _row_to_pedido(row)

def _get_all_pedidos() -> List[Dict[str, object]]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
        return [_row_to_pedido(r) for r in rows]

# --- Endpoints ---

@app.get("/api/menu")
async def get_menu():
    return sorted(productos, key=lambda p: (p.get("seccion", ""), p.get("nombre", "")))

@app.post("/api/pedidos")
async def create_pedido(pedido: Pedido):
    print(f"📥 Recibiendo pedido nuevo: {pedido}") # LOG
    # Recalcular total para seguridad (opcional)
    total_calc = 0.0
    for pid in pedido.productos:
        prod = _producto_por_id(pid)
        if prod:
            total_calc += float(prod.get("precio", 0))
    
    # Si el cálculo coincide más o menos, o si confiamos en el front, usamos el del front
    # Aquí forzamos el cálculo del backend si no viene total
    if total_calc > 0:
        pedido.total = total_calc

    pedido_id = _insert_pedido(pedido)
    return {"mensaje": "Pedido creado", "id": pedido_id}

@app.get("/api/pedidos")
async def get_pedidos():
    return [_serializar_pedido(p) for p in _get_all_pedidos()]

@app.get("/api/pedidos/{pedido_id}")
async def get_pedido(pedido_id: int):
    pedido = _get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return _serializar_pedido(pedido)

@app.put("/api/pedidos/{pedido_id}/estado")
async def update_estado_endpoint(pedido_id: int, data: PedidoEstado):
    nuevo_estado = (data.estado or "").strip().lower()
    if not nuevo_estado:
        raise HTTPException(status_code=400, detail="Estado inválido")

    if not _update_estado(pedido_id, nuevo_estado):
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    pedido = _get_pedido(pedido_id)
    return {"mensaje": "Estado actualizado", "estado": pedido["estado"]}

@app.post("/api/pedidos/sync")
async def sync_pedidos(payload: PedidosSync):
    ids_map: Dict[str, int] = {}
    print(f"🔄 Sincronizando {len(payload.pedidos)} pedidos offline")
    for item in payload.pedidos:
        pedido = Pedido(
            productos=item.productos,
            total=item.total,
            estado=item.estado,
            modo=item.modo,
        )
        new_id = _insert_pedido(pedido)
        if item.temp_id:
            ids_map[item.temp_id] = new_id
    return {"mensaje": "Pedidos sincronizados", "ids": ids_map}

# Instrucciones para correr:
# pip install fastapi uvicorn
# uvicorn backend:app --reload --port 9000