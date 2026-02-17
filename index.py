import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import difflib

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Carnicería - Control Total", layout="wide")
LIMITE_ALERTA = 5.0

# --- 1. SEGURO CONTRA F5 (MANEJO DE URL) ---
# Si no hay sucursal definida en la URL, ponemos "Super montaña" por defecto
if "sucursal" not in st.query_params:
    st.query_params["sucursal"] = "Super montaña"

# --- 2. SELECCIÓN DE SUCURSAL (BARRA LATERAL) ---
with st.sidebar:
    st.header("🏪 Local")
    
    opciones = ["Super montaña", "Carnicería zona norte"]
    
    # Buscamos qué índice tiene la sucursal actual para que el selectbox no se mueva
    try:
        indice_actual = opciones.index(st.query_params["sucursal"])
    except ValueError:
        indice_actual = 0

    sucursal_activa = st.selectbox(
        "Seleccionar Sucursal", 
        opciones, 
        index=indice_actual,
        key="selector_sucursal"
    )

    # Si el usuario cambia el selector, actualizamos la URL y recargamos
    if sucursal_activa != st.query_params["sucursal"]:
        st.query_params["sucursal"] = sucursal_activa
        st.rerun()

    st.warning(f"📍 ESTÁS CARGANDO EN: **{sucursal_activa.upper()}**")
    st.markdown("---")
    st.caption("Los datos corresponden solo a la sucursal seleccionada.")

# --- FUNCIONES DE BASE DE DATOS ---
def conectar_db():
    return sqlite3.connect('carniceria_datos.db')

def crear_tablas():
    conn = conectar_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stock 
                 (producto TEXT, cantidad REAL, sucursal TEXT, 
                 PRIMARY KEY (producto, sucursal))''')
    c.execute('''CREATE TABLE IF NOT EXISTS caja 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tipo TEXT, 
                 monto REAL, motivo TEXT, sucursal TEXT)''')
    conn.commit()
    conn.close()

crear_tablas()

# --- FUNCIONES DE LÓGICA ---
def normalizar_nombre(nombre):
    return nombre.strip().capitalize()

def corregir_nombre(nombre_nuevo, lista_existente):
    if not lista_existente:
        return nombre_nuevo
    coincidencias = difflib.get_close_matches(nombre_nuevo, lista_existente, n=1, cutoff=0.6)
    return coincidencias[0] if coincidencias else nombre_nuevo

# --- 3. CARGA DE DATOS FILTRADOS ---
conn = conectar_db()
df_stock = pd.read_sql_query("SELECT * FROM stock WHERE sucursal = ?", conn, params=(sucursal_activa,))
df_caja = pd.read_sql_query("SELECT * FROM caja WHERE sucursal = ?", conn, params=(sucursal_activa,))
conn.close()

# --- 4. TÍTULO Y DASHBOARD ---
st.title(f"🥩 Gestión: {sucursal_activa}")

dashboard = st.container()
with dashboard:
    total_ingresos = df_caja[df_caja['tipo'] == 'Ingreso']['monto'].sum()
    total_egresos = df_caja[df_caja['tipo'] == 'Egreso']['monto'].sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("💰 Dinero en Caja", f"$ {total_ingresos - total_egresos:,.2f}")
    m2.metric("📈 Total Ventas", f"$ {total_ingresos:,.2f}")
    m3.metric("📉 Gastos Totales", f"$ {total_egresos:,.2f}")

    if not df_stock.empty:
        bajo_stock = df_stock[df_stock['cantidad'] <= LIMITE_ALERTA]
        for _, fila in bajo_stock.iterrows():
            st.error(f"⚠️ **{fila['producto']}**: ¡Solo quedan **{fila['cantidad']:.2f} kg**! (Reponer pronto)")

st.markdown("---")

# --- 5. CUERPO PRINCIPAL ---
col_izq, col_der = st.columns([1, 1.3])

with col_izq:
    st.subheader("📝 Registrar Movimiento")
    tab1, tab2, tab3 = st.tabs(["💰 Vender", "🚚 Cargar Stock", "💸 Gastos"])

    with tab1:
        if not df_stock.empty:
            with st.form("form_venta", clear_on_submit=True):
                prod_vender = st.selectbox("¿Qué se vendió?", df_stock['producto'].tolist())
                kgs_vender = st.number_input("Kilos vendidos", min_value=0.0, step=0.1, format="%.2f")
                precio_vender = st.number_input("Cobrado ($)", min_value=0.0, format="%.2f")
            
                if st.form_submit_button("REGISTRAR VENTA"):
                    stock_disponible = df_stock[df_stock['producto'] == prod_vender]['cantidad'].values[0]

                    if kgs_vender <= 0:
                        st.warning("⚠️ Ingresá una cantidad válida.")
                    elif kgs_vender > stock_disponible:
                        st.error(f"❌ Stock insuficiente en {sucursal_activa}. Solo hay {stock_disponible:.2f} kg.")
                    else:
                        conn = conectar_db(); c = conn.cursor()
                        c.execute("UPDATE stock SET cantidad = cantidad - ? WHERE producto = ? AND sucursal = ?", 
                                  (kgs_vender, prod_vender, sucursal_activa))
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c.execute("INSERT INTO caja (fecha, tipo, monto, motivo, sucursal) VALUES (?, 'Ingreso', ?, ?, ?)", 
                                  (fecha, precio_vender, f"Venta {kgs_vender}kg {prod_vender}", sucursal_activa))
                        conn.commit(); conn.close()
                        st.success(f"✅ Venta registrada en {sucursal_activa}")
                        st.rerun()
        else:
            st.info("Primero cargá mercadería para esta sucursal.")

    with tab2:
        with st.form("form_stock", clear_on_submit=True):
            st.write(f"Cargando stock para: **{sucursal_activa}**")
            prod_input = st.text_input("Nombre del corte")
            cant_input = st.number_input("Kilos que entran", min_value=0.0, step=0.1, format="%.2f")
            
            if st.form_submit_button("CARGAR STOCK"):
                if prod_input and cant_input > 0:
                    nombre_norm = normalizar_nombre(prod_input)
                    nombre_final = corregir_nombre(nombre_norm, df_stock['producto'].tolist())
                    
                    conn = conectar_db(); c = conn.cursor()
                    c.execute("""INSERT INTO stock (producto, cantidad, sucursal) VALUES (?, ?, ?) 
                                 ON CONFLICT(producto, sucursal) DO UPDATE SET cantidad = cantidad + ?""", 
                              (nombre_final, cant_input, sucursal_activa, cant_input))
                    conn.commit(); conn.close()
                    st.success(f"🚚 Stock actualizado en {sucursal_activa}")
                    st.rerun()

    with tab3:
        with st.form("form_gastos", clear_on_submit=True):
            monto_g = st.number_input("Monto gasto ($)", min_value=0.0, format="%.2f")
            motivo_g = st.text_input("¿En qué se gastó?")
            if st.form_submit_button("GUARDAR GASTO"):
                if monto_g > 0:
                    conn = conectar_db(); c = conn.cursor()
                    c.execute("INSERT INTO caja (fecha, tipo, monto, motivo, sucursal) VALUES (?, 'Egreso', ?, ?, ?)", 
                              (datetime.now().strftime("%Y-%m-%d %H:%M"), monto_g, motivo_g, sucursal_activa))
                    conn.commit(); conn.close()
                    st.success(f"💸 Gasto registrado en {sucursal_activa}")
                    st.rerun()

with col_der:
    st.subheader(f"📊 Stock: {sucursal_activa}")
    if not df_stock.empty:
        df_ord = df_stock.sort_values(by='cantidad', ascending=True)
        
        def resaltar_bajo(s):
            return ['background-color: #ff4b4b; color: white' if v <= 5 else '' for v in s]

        st.dataframe(
            df_ord.style.apply(resaltar_bajo, subset=['cantidad']),
            use_container_width=True, 
            hide_index=True,
            column_config={
                "producto": "Producto",
                "cantidad": st.column_config.NumberColumn("Kgs Disponibles", format="%.2f"),
                "sucursal": None
            }
        )
        
        st.write("---")
        st.caption("Gráfico visual de stock:")
        st.bar_chart(df_ord.set_index("producto")['cantidad'])
    else:
        st.info(f"No hay productos registrados en {sucursal_activa}.")

with st.expander(f"🔍 Historial de caja - {sucursal_activa}"):
    if not df_caja.empty:
        df_hist = df_caja.sort_values(by='id', ascending=False).head(15)
        st.dataframe(df_hist.drop(columns=['sucursal']), use_container_width=True, hide_index=True)
    else:
        st.write("Sin movimientos aún.")