import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import difflib

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Carnicería - Control Total", layout="wide")
LIMITE_ALERTA = 5.0

# --- FUNCIONES DE BASE DE DATOS ---
def conectar_db():
    return sqlite3.connect('carniceria_datos.db')

def crear_tablas():
    conn = conectar_db()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS stock (producto TEXT PRIMARY KEY, cantidad REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS caja (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tipo TEXT, monto REAL, motivo TEXT)')
    conn.commit()
    conn.close()

crear_tablas()

# --- FUNCIONES DE LÓGICA INTELIGENTE ---
def normalizar_nombre(nombre):
    return nombre.strip().capitalize()

def corregir_nombre(nombre_nuevo, lista_existente):
    if not lista_existente:
        return nombre_nuevo
    coincidencias = difflib.get_close_matches(nombre_nuevo, lista_existente, n=1, cutoff=0.6)
    return coincidencias[0] if coincidencias else nombre_nuevo

# --- 1. CARGA DE DATOS INICIAL ---
conn = conectar_db()
df_stock = pd.read_sql_query("SELECT * FROM stock", conn)
df_caja = pd.read_sql_query("SELECT * FROM caja", conn)
conn.close()

# --- 2. TÍTULO Y DASHBOARD ---
st.title("🥩 Gestión de la Carnicería")

dashboard = st.container()
with dashboard:
    total_ingresos = df_caja[df_caja['tipo'] == 'Ingreso']['monto'].sum()
    total_egresos = df_caja[df_caja['tipo'] == 'Egreso']['monto'].sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("💰 Dinero en Caja", f"${total_ingresos - total_egresos:,.2f}")
    m2.metric("📈 Total Ventas", f"${total_ingresos:,.2f}")
    m3.metric("📉 Gastos Totales", f"${total_egresos:,.2f}")

    if not df_stock.empty:
        bajo_stock = df_stock[df_stock['cantidad'] <= LIMITE_ALERTA]
        for _, fila in bajo_stock.iterrows():
            st.error(f"⚠️ **{fila['producto']}**: ¡Solo quedan **{fila['cantidad']} kg**! (Reponer pronto)")

st.markdown("---")

# --- 3. CUERPO PRINCIPAL ---
col_izq, col_der = st.columns([1, 1.3])

with col_izq:
    st.subheader("📝 Registrar Movimiento")
    tab1, tab2, tab3 = st.tabs(["💰 Vender", "🚚 Cargar Stock", "💸 Gastos"])

    with tab1:
        if not df_stock.empty:
            with st.form("form_venta", clear_on_submit=True):
                prod_vender = st.selectbox("¿Qué se vendió?", df_stock['producto'].tolist())
                kgs_vender = st.number_input("Kilos vendidos", min_value=0.0, step=0.1)
                precio_vender = st.number_input("Cobrado ($)", min_value=0.0)
            
                if st.form_submit_button("REGISTRAR VENTA"):
                    # --- VALIDACIÓN DE STOCK ---
                    stock_disponible = df_stock[df_stock['producto'] == prod_vender]['cantidad'].values[0]

                    if kgs_vender <= 0:
                        st.warning("⚠️ Ingresá una cantidad de kilos válida.")
                    elif kgs_vender > stock_disponible:
                        st.error(f"❌ **Stock insuficiente**. Solo tenés {stock_disponible} kg de {prod_vender}.")
                    else:
                        conn = conectar_db(); c = conn.cursor()
                        # A. Restamos los kilos del stock
                        c.execute("UPDATE stock SET cantidad = cantidad - ? WHERE producto = ?", (kgs_vender, prod_vender))
                        # B. Registramos el ingreso de dinero
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c.execute("INSERT INTO caja (fecha, tipo, monto, motivo) VALUES (?, 'Ingreso', ?, ?)", 
                                  (fecha, precio_vender, f"Venta {kgs_vender}kg {prod_vender}"))
                        conn.commit(); conn.close()
                        st.success(f"✅ Venta registrada: {kgs_vender}kg de {prod_vender}")
                        st.rerun()
        else:
            st.info("Primero cargá mercadería en la pestaña de al lado.")

    with tab2:
        with st.form("form_stock", clear_on_submit=True):
            st.write("Si el nombre es parecido a uno existente, el sistema lo unificará.")
            prod_input = st.text_input("Nombre del corte")
            cant_input = st.number_input("Kilos que entran", min_value=0.0, step=0.1)
            
            if st.form_submit_button("Cargar a Heladera"):
                if prod_input and cant_input > 0:
                    nombre_norm = normalizar_nombre(prod_input)
                    nombres_actuales = df_stock['producto'].tolist()
                    nombre_final = corregir_nombre(nombre_norm, nombres_actuales)
                    
                    conn = conectar_db(); c = conn.cursor()
                    c.execute("""INSERT INTO stock (producto, cantidad) VALUES (?, ?) 
                                 ON CONFLICT(producto) DO UPDATE SET cantidad = cantidad + ?""", 
                              (nombre_final, cant_input, cant_input))
                    conn.commit(); conn.close()
                    st.success(f"🚚 Stock actualizado: {nombre_final} (+{cant_input} kg)")
                    st.rerun()

    with tab3:
        with st.form("form_gastos", clear_on_submit=True):
            monto_g = st.number_input("Monto gasto ($)", min_value=0.0)
            motivo_g = st.text_input("¿En qué se gastó?")
            if st.form_submit_button("Guardar Gasto"):
                if monto_g > 0:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                    conn = conectar_db(); c = conn.cursor()
                    c.execute("INSERT INTO caja (fecha, tipo, monto, motivo) VALUES (?, 'Egreso', ?, ?)", (fecha, monto_g, motivo_g))
                    conn.commit(); conn.close()
                    st.success("💸 Gasto registrado.")
                    st.rerun()

with col_der:
    st.subheader("📊 Inventario Actual")
    if not df_stock.empty:
        # Gráfico de barras simple para ver el stock visualmente
        st.bar_chart(df_stock.set_index("producto"))
        st.dataframe(df_stock, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("💾 Exportar Datos")
    if st.button("Preparar planilla para descargar"):
        with pd.ExcelWriter("Cierre_Carniceria.xlsx", engine="xlsxwriter") as writer:
            df_stock.to_excel(writer, sheet_name="Stock_Actual", index=False)
            df_caja.to_excel(writer, sheet_name="Movimientos_Caja", index=False)
        
        with open("Cierre_Carniceria.xlsx", "rb") as f:
            st.download_button("📥 Descargar Archivo Excel", f, "Cierre_Carniceria.xlsx")

# HISTORIAL INFERIOR
with st.expander("🔍 Ver historial de caja (Últimos 15)"):
    if not df_caja.empty:
        st.table(df_caja.sort_values(by='id', ascending=False).head(15))
    else:
        st.write("No hay movimientos registrados aún.")