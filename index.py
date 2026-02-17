import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Carnicería - Rendimiento por Ventas", layout="wide")

# --- 1. SEGURO CONTRA F5 ---
if "sucursal" not in st.query_params:
    st.query_params["sucursal"] = "Super montaña"

# --- 2. SELECCIÓN DE SUCURSAL ---
with st.sidebar:
    st.header("🏪 Local")
    opciones = ["Super montaña", "Carnicería zona norte"]
    try:
        indice_actual = opciones.index(st.query_params["sucursal"])
    except ValueError:
        indice_actual = 0

    sucursal_activa = st.selectbox("Seleccionar Sucursal", opciones, index=indice_actual, key="selector_sucursal")

    if sucursal_activa != st.query_params["sucursal"]:
        st.query_params["sucursal"] = sucursal_activa
        st.rerun()

    st.warning(f"📍 ANALIZANDO: **{sucursal_activa.upper()}**")
    st.markdown("---")

# --- FUNCIONES DE BASE DE DATOS ---
def conectar_db():
    return sqlite3.connect('carniceria_datos.db')

def crear_tablas():
    conn = conectar_db()
    c = conn.cursor()
    # Cambiamos 'vendida' (kgs) por 'recaudado' (dinero total por producto)
    c.execute('''CREATE TABLE IF NOT EXISTS stock 
                 (producto TEXT, recaudado REAL DEFAULT 0, sucursal TEXT, 
                 PRIMARY KEY (producto, sucursal))''')
    c.execute('''CREATE TABLE IF NOT EXISTS caja 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tipo TEXT, 
                 monto REAL, motivo TEXT, sucursal TEXT)''')
    conn.commit()
    conn.close()

crear_tablas()

# --- 3. CARGA DE DATOS ---
conn = conectar_db()
df_productos = pd.read_sql_query("SELECT * FROM stock WHERE sucursal = ?", conn, params=(sucursal_activa,))
df_caja = pd.read_sql_query("SELECT * FROM caja WHERE sucursal = ?", conn, params=(sucursal_activa,))
conn.close()

# --- 4. DASHBOARD ECONÓMICO ---
st.title(f"🥩 Rendimiento de Ventas: {sucursal_activa}")

total_ingresos = df_caja[df_caja['tipo'] == 'Ingreso']['monto'].sum()
total_egresos = df_caja[df_caja['tipo'] == 'Egreso']['monto'].sum()
saldo_caja = total_ingresos - total_egresos

m1, m2, m3 = st.columns(3)
m1.metric("💰 Saldo Actual en Caja", f"$ {saldo_caja:,.2f}")
m2.metric("📈 Total Recaudado", f"$ {total_ingresos:,.2f}")
m3.metric("📉 Gastos Totales", f"$ {total_egresos:,.2f}")

st.markdown("---")

# --- 5. CUERPO PRINCIPAL ---
col_izq, col_der = st.columns([1, 1.2])

with col_izq:
    st.subheader("📝 Cargar Operación")
    tab1, tab2, tab3 = st.tabs(["💰 Venta", "💸 Gasto", "⚙️ Productos"])

    with tab1:
        if not df_productos.empty:
            with st.form("form_venta", clear_on_submit=True):
                prod_vender = st.selectbox("Corte vendido", df_productos['producto'].tolist())
                # Pedimos los datos, pero lo que impacta en el ranking es el precio_vender
                kgs_vender = st.number_input("Kilos vendidos (informativo)", min_value=0.0, step=0.1, format="%.2f")
                precio_vender = st.number_input("Precio Total Cobrado ($)", min_value=0.0, format="%.2f")
                
                if st.form_submit_button("REGISTRAR VENTA"):
                    if precio_vender > 0:
                        conn = conectar_db(); c = conn.cursor()
                        # Sumamos el monto al acumulado del producto
                        c.execute("UPDATE stock SET recaudado = recaudado + ? WHERE producto = ? AND sucursal = ?", 
                                  (precio_vender, prod_vender, sucursal_activa))
                        # Registramos el movimiento en la caja
                        c.execute("INSERT INTO caja (fecha, tipo, monto, motivo, sucursal) VALUES (?, 'Ingreso', ?, ?, ?)", 
                                  (datetime.now().strftime("%Y-%m-%d %H:%M"), precio_vender, f"Venta {kgs_vender}kg {prod_vender}", sucursal_activa))
                        conn.commit(); conn.close()
                        st.success(f"✅ Venta de {prod_vender} registrada")
                        st.rerun()
        else:
            st.info("Agregá cortes en la pestaña 'Productos'.")

    with tab2:
        with st.form("form_gastos", clear_on_submit=True):
            monto_g = st.number_input("Monto del gasto ($)", min_value=0.0, format="%.2f")
            motivo_g = st.text_input("¿En qué se gastó?")
            if st.form_submit_button("REGISTRAR GASTO"):
                if monto_g > 0:
                    conn = conectar_db(); c = conn.cursor()
                    c.execute("INSERT INTO caja (fecha, tipo, monto, motivo, sucursal) VALUES (?, 'Egreso', ?, ?, ?)", 
                              (datetime.now().strftime("%Y-%m-%d %H:%M"), monto_g, motivo_g, sucursal_activa))
                    conn.commit(); conn.close()
                    st.success("💸 Gasto guardado")
                    st.rerun()

    with tab3:
        st.write("🔧 Configuración de Productos")
        nuevo_p = st.text_input("Nuevo corte (ej: Vacío)")
        if st.button("Añadir a la lista"):
            if nuevo_p:
                conn = conectar_db(); c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO stock (producto, recaudado, sucursal) VALUES (?, 0, ?)", 
                          (nuevo_p.strip().capitalize(), sucursal_activa))
                conn.commit(); conn.close(); st.rerun()

        if not df_productos.empty:
            st.divider()
            prod_sel = st.selectbox("Acción sobre producto", df_productos['producto'].tolist())
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🔄 Reiniciar Recaudación"):
                    conn = conectar_db(); c = conn.cursor()
                    c.execute("UPDATE stock SET recaudado = 0 WHERE producto = ? AND sucursal = ?", (prod_sel, sucursal_activa))
                    conn.commit(); conn.close(); st.rerun()
            with col_b2:
                if st.button("🗑️ Eliminar Producto"):
                    conn = conectar_db(); c = conn.cursor()
                    c.execute("DELETE FROM stock WHERE producto = ? AND sucursal = ?", (prod_sel, sucursal_activa))
                    conn.commit(); conn.close(); st.rerun()

with col_der:
    st.subheader(f"📊 Ranking por Recaudación ($)")
    if not df_productos.empty:
        # Ordenamos por los que más dinero generaron
        df_ranking = df_productos.sort_values(by='recaudado', ascending=False)
        
        st.dataframe(
            df_ranking,
            use_container_width=True, hide_index=True,
            column_config={
                "producto": "Corte de Carne",
                "recaudado": st.column_config.NumberColumn("Dinero Total Generado ($)", format="$ %.2f"),
                "sucursal": None
            }
        )
        
        st.write("---")
        # EXPORTACIÓN
        if st.button("📊 Descargar Reporte Completo (Excel)"):
            nombre_archivo = f"Cierre_{sucursal_activa}_{datetime.now().strftime('%d-%m-%Y')}.xlsx"
            with pd.ExcelWriter(nombre_archivo, engine="xlsxwriter") as writer:
                df_ranking.to_excel(writer, sheet_name="Ranking_Dinero", index=False)
                df_caja.to_excel(writer, sheet_name="Movimientos_Caja", index=False)
            with open(nombre_archivo, "rb") as f:
                st.download_button("📥 Guardar Excel", f, file_name=nombre_archivo)
    else:
        st.info("No hay productos registrados.")

# HISTORIAL VISUAL
with st.expander("🔍 Historial rápido de movimientos"):
    if not df_caja.empty:
        st.table(df_caja.sort_values(by='id', ascending=False).drop(columns=['sucursal']).head(10))