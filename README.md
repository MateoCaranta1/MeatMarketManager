<b>🥩 MeatMarketManager</b>

MeatMarketManager es una solución ligera y eficiente diseñada para carnicerías con múltiples sucursales. Permite un control estricto del stock, gestión de caja (ingresos/egresos) y visualización de datos en tiempo real, todo con una interfaz ultra-sencilla pensada para usuarios finales.

<b>✨ Características Principales</b>
- 🏢 Gestión Multisucursal: Control independiente para "Super Montaña" y "Zona Norte" sin cruce de datos.

- ⚖️ Control de Stock Inteligente: * Validación de ventas: No permite vender más kg de los disponibles.

- Filtro "Fuzzy Matching": Corrige automáticamente nombres similares para evitar duplicados (ej: "Asado" vs "asado").

- 📊 Dashboard en Vivo: Métricas de dinero en caja, ventas totales y gastos por sucursal.

- 🚨 Alertas Visuales: Resaltado automático en rojo para productos con stock menor a 5kg.

- 💾 Exportación a Excel: Genera reportes de cierre listos para descargar.

- 🔄 Persistencia de Sesión: Sistema de seguridad contra recargas (F5) que mantiene la sucursal activa.

<b>🛠️ Tecnologías Usadas</b>
- Backend: Python 3.

- Frontend: Streamlit (UI Reactiva).

- Base de Datos: SQLite3 (Local, no requiere servidor externo).

- Procesamiento: Pandas (Manejo de DataFrames).

