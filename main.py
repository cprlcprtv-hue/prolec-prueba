# Importa Streamlit, framework para crear aplicaciones web interactivas en Python
# Ejemplo: st.title("Hola") mostraría un título grande en la página web
import streamlit as st

# 1. CONFIGURACION DE PAGINA AL INICIO ABSOLUTO
# Configura la página web: título de la pestaña del navegador y diseño ancho (usa todo el ancho disponible)
# Ejemplo: si layout="centered", el contenido se vería como una columna estrecha al centro
st.set_page_config(page_title="Sistema Prolec - Bolivia", layout="wide")

# Importa funciones de Supabase (base de datos en la nube similar a Firebase)
# create_client: crea conexión a la DB. Client: tipo de dato para tipado
from supabase import create_client, Client

# Módulo para trabajar con fechas y horas
# Ejemplo: datetime.date.today() retorna 2026-05-12 (la fecha actual)
import datetime

# Módulo para manejo de zonas horarias (Bolivia usa America/La_Paz, UTC-4 permanente)
# Ejemplo: pytz.timezone('America/La_Paz') crea objeto de zona horaria boliviana
import pytz

# ReportLab: librería para generar PDFs
# canvas: permite "dibujar" en un PDF (texto, líneas, imágenes)
# Ejemplo: canvas.Canvas(buf, pagesize=letter) crea un PDF tamaño carta
from reportlab.pdfgen import canvas

# pagesizes: tamaños de página predefinidos (letter = 8.5x11 pulgadas)
# portrait: función que devuelve dimensiones en orientación vertical
from reportlab.lib.pagesizes import letter, portrait

# colors: colores predefinidos para usar en PDFs (rojo, azul, negro, etc.)
from reportlab.lib import colors

# Convierte números a palabras en español (requisito legal en comprobantes bolivianos)
# Ejemplo: num2words(1250, lang='es') produce "mil doscientos cincuenta"
from num2words import num2words 

# Permite crear archivos temporales en memoria RAM sin guardar en disco
# Ejemplo: buf = io.BytesIO() crea un "archivo virtual" para el PDF
import io

# Funciones del sistema operativo (verificar si archivos existen, rutas, etc.)
# Ejemplo: os.path.exists("logo.png") verifica si el archivo logo.png existe
import os

# --- INICIALIZACION SILENCIOSA DE VARIABLES ---
# streamlit.session_state: diccionario que persiste datos entre recargas de la página
# Si no existe la clave "cajero", la crea con valor None (sin usuario logueado)
if "cajero" not in st.session_state: st.session_state.cajero = None

# Almacena el rol del usuario: "Administrador" o "Cajero" (nombre de usuario)
# Ejemplo: st.session_state.rol_usuario = "admin123" o "cajero001"
if "rol_usuario" not in st.session_state: st.session_state.rol_usuario = None

# Bandera para mostrar/ocultar botón de confirmación de pago
# False = no mostrar confirmación, True = mostrar botones SI/NO
if "confirmar_pago" not in st.session_state: st.session_state.confirmar_pago = False

# Bandera para mostrar/ocultar botón de confirmación de reversión/anulación
if "confirmar_reversion" not in st.session_state: st.session_state.confirmar_reversion = False

# Contador que fuerza la recarga del campo de búsqueda (cambia la key y se resetea el input)
# Cada vez que se incrementa, Streamlit ve un widget diferente y lo recrea vacío
if "busqueda_key" not in st.session_state: st.session_state.busqueda_key = 0

# Contador similar para el campo de búsqueda de reversiones
if "rev_search_key" not in st.session_state: st.session_state.rev_search_key = 0

# --- CONEXION ---
# Intenta conectar con Supabase usando credenciales seguras
try:
    # Verifica que existan las credenciales en secrets.toml (archivo de configuración secreto)
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        # Obtiene URL de la base de datos y elimina espacios en blanco
        # Ejemplo: url = "https://abcdefg.supabase.co"
        url: str = st.secrets["SUPABASE_URL"].strip()
        # Obtiene clave de acceso y elimina espacios
        # Ejemplo: key = "eyJhbGciOiJIUzI1NiIs..."
        key: str = st.secrets["SUPABASE_KEY"].strip()
        # Crea cliente de conexión a Supabase con las credenciales
        supabase: Client = create_client(url, key)
    else:
        # Si no hay credenciales, detiene completamente la aplicación
        st.stop()
except Exception:
    # Si hay error de conexión, también detiene la app
    st.stop()

# --- LOGO ---
# Intenta mostrar el logo de la cooperativa en la interfaz
try:
    # Verifica si existe el archivo de imagen logo_izquierdo.png en el directorio
    if os.path.exists("logo_izquierdo.png"):
        # Muestra la imagen con 200 píxeles de ancho (altura proporcional)
        st.image("logo_izquierdo.png", width=200)
except:
    # Si hay error al cargar la imagen, simplemente lo ignora y sigue
    pass

# Función que convierte un monto numérico a texto literal tipo cheque
# Ejemplo: monto_a_letras(1520.50) retorna "MIL QUINIENTOS VEINTE 50/100"
def monto_a_letras(monto):
    # Obtiene la parte entera del monto: 1520.50 -> 1520
    entero = int(monto)
    # Calcula los centavos redondeando: (1520.50 - 1520) * 100 = 50
    # round() evita errores de punto flotante como 0.49999...
    decimales = int(round((monto - entero) * 100))
    # Convierte la parte entera a palabras en español y lo pone en MAYÚSCULAS
    # Ejemplo: num2words(1520, lang='es') -> "mil quinientos veinte" -> "MIL QUINIENTOS VEINTE"
    literal = num2words(entero, lang='es').upper()
    # Formatea: "MIL QUINIENTOS VEINTE 50/100" (decimales con 2 dígitos rellenos con ceros)
    return f"{literal} {decimales:02d}/100"

# --- LOGIN ---
# Si no hay cajero logueado (es None), muestra formulario de inicio de sesión
if not st.session_state.cajero:
    # Muestra título grande en la página
    st.title("Acceso al Sistema de Cobros")
    # Crea un formulario (al presionar Enter o el botón, se envían todos los campos juntos)
    with st.form("login"):
        # Campo de texto para nombre de usuario
        user_input = st.text_input("Nombre de Usuario")
        # Campo de contraseña (los caracteres se muestran como asteriscos)
        pass_input = st.text_input("Contraseña", type="password")
        # Botón de envío del formulario
        if st.form_submit_button("Ingresar"):
            # Consulta a la tabla "usuarios_cajeros" buscando coincidencia exacta de usuario Y contraseña
            # Ejemplo: SELECT * FROM usuarios_cajeros WHERE usuario='admin' AND password='123456'
            user_query = supabase.table("usuarios_cajeros").select("*").eq("usuario", user_input).eq("password", pass_input).execute()
            # Si la consulta devuelve datos (existe el usuario con esa contraseña)
            if user_query.data:
                # Guarda el nombre real del cajero (ej: "Juan Pérez") en la sesión
                st.session_state.cajero = user_query.data[0]['nombre_real']
                # Guarda el nombre de usuario (ej: "admin123") como rol
                st.session_state.rol_usuario = user_query.data[0]['usuario'] 
                # Recarga la página para mostrar el menú principal
                st.rerun()
            else:
                # Muestra mensaje de error en rojo si las credenciales son inválidas
                st.error("Usuario o contraseña incorrectos.")
else:
    # --- MENU PRINCIPAL (usuario ya logueado) ---
    # Muestra en la barra lateral el nombre del cajero que inició sesión
    st.sidebar.info(f"Cajero: {st.session_state.cajero}")
    # Crea menú de opciones con botones de radio en la barra lateral
    # La variable 'menu' contendrá el texto de la opción seleccionada
    menu = st.sidebar.radio("Seleccione una opcion:", ["Buscador de Dividendos", "Listado de Cobros", "Reversión de Cobros", "Reporte de Reversiones"])
    
    # Botón para cerrar sesión en la barra lateral
    if st.sidebar.button("Cerrar Sesion"):
        # Elimina TODAS las variables de sesión (limpia completamente el estado)
        # list() crea una copia de las claves para evitar error al modificar el diccionario mientras se itera
        for k in list(st.session_state.keys()): del st.session_state[k]
        # Recarga la página (volverá a mostrar el login porque cajero será None)
        st.rerun()

    # --- OPCION 1: BUSCADOR DE DIVIDENDOS ---
    if menu == "Buscador de Dividendos":
        st.title("Buscador de Dividendos")
        # Verifica si hay un mensaje de éxito de un cobro reciente (después de registrar pago)
        if "mensaje_exito_cobro" in st.session_state:
            # Muestra mensaje verde de éxito con los detalles del cobro
            st.success(st.session_state.mensaje_exito_cobro)
            # Botón para descargar el PDF del comprobante generado
            # Recibe: etiqueta, datos binarios del PDF, nombre sugerido del archivo
            st.download_button("Descargar Comprobante PDF", st.session_state.pdf_exito, st.session_state.pdf_nombre)
            # Botón para limpiar el mensaje de éxito y hacer nueva búsqueda
            if st.button("Realizar nueva busqueda"):
                # Elimina las variables temporales del cobro exitoso
                del st.session_state.mensaje_exito_cobro
                del st.session_state.pdf_exito
                del st.session_state.pdf_nombre
                # Recarga para mostrar el buscador limpio
                st.rerun()
            # Detiene la ejecución aquí (no muestra el resto del buscador)
            st.stop()

        # Campo de texto para buscar por número de título
        # key dinámica: al cambiar busqueda_key, Streamlit recrea el widget vacío
        # Ejemplo: key="titulo_input_0", luego "titulo_input_1", etc.
        titulo_input = st.text_input("Ingrese Numero de Titulo:", key=f"titulo_input_{st.session_state.busqueda_key}")
        # Solo busca si el usuario escribió algo en el campo
        if titulo_input:
            try:
                # Elimina espacios al inicio y final del texto ingresado
                t_limpio = titulo_input.strip()
                # Primera búsqueda: busca el título como texto (por si tiene letras)
                # Ejemplo: SELECT * FROM riego WHERE titulo = 'A123'
                res = supabase.table("riego").select("*").eq("titulo", t_limpio).execute()
                # Si no encuentra y el texto son solo dígitos, busca como número
                # Esto maneja casos donde el título se guardó como número en la BD
                if not res.data and t_limpio.isdigit(): 
                    res = supabase.table("riego").select("*").eq("titulo", int(t_limpio)).execute()

                # Si encontró el título en la base de datos
                if res.data:
                    # Toma el primer resultado (debería ser único por título)
                    socio = res.data[0]
                    # Convierte acciones a entero: "5.0" -> 5 (maneja casos con decimales)
                    acciones = int(float(socio.get("acciones") or 0))
                    # Obtiene el valor individual de cada acción, 0 si no existe
                    importe_individual = float(socio.get("importe_accion") or 0)
                    # Calcula monto total: ej: 5 acciones * 100 Bs = 500 Bs
                    total = acciones * importe_individual
                    # Obtiene el número de formulario (puede ser None si no está pagado)
                    nro_form_raw = socio.get("nro_formulario")
                    # Mensaje verde con el nombre del socio encontrado
                    st.success(f"Socio Localizado: {socio.get('nombre')}")
                    # Crea 3 columnas para mostrar información del socio
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # Muestra datos de identificación del título
                        st.write(f"**Serie:** {socio.get('serie','')}")
                        st.write(f"**Nombre Serie:** {socio.get('nombre_serie','')}")
                        st.write(f"**Titulo:** {socio.get('titulo')}")
                        # Si hay número de formulario lo muestra con 5 dígitos (00123), sino 'PENDIENTE'
                        st.write(f"**Nro. Formulario:** {str(nro_form_raw).zfill(5) if nro_form_raw else 'PENDIENTE'}")
                    with col2:
                        # Muestra acciones y valor unitario
                        st.write(f"**Acciones:** {acciones}")
                        st.write(f"**Valor Accion:** {importe_individual:.2f} Bs.")
                    with col3:
                        # Muestra el total en formato grande (métrica destacada)
                        st.metric("Total", f"{total:.2f} Bs.")
                    st.divider()  # Línea separadora horizontal

                    # Función interna que genera el PDF del comprobante de pago
                    # Parámetros: datos del socio, monto total, nombre cajero, fecha, hora, nro formulario
                    def generar_pdf_individual(datos, monto_t, c_nombre, f_pago, h_pago, n_form):
                        # Crea buffer en memoria para el PDF (no se guarda en disco)
                        buf = io.BytesIO()
                        # Crea lienzo PDF tamaño carta vertical
                        c_pdf = canvas.Canvas(buf, pagesize=portrait(letter))
                        # Obtiene ancho y alto de la página carta en puntos (612 x 792)
                        w, h = portrait(letter)
                        # Formatea número de formulario a 5 dígitos: 123 -> "00123"
                        f_num = str(n_form).zfill(5)
                        # Márgenes: superior e izquierdo de 20 puntos
                        m_sup = 20
                        m_izq = 20
                        m_der = w - 20  # Margen derecho = ancho - 20
                        # Dibuja rectángulo principal del comprobante
                        c_pdf.setLineWidth(0.8)
                        c_pdf.rect(m_izq, h - (m_sup + 360), m_der - m_izq, 360)
                        # Líneas divisoras horizontales dentro del comprobante
                        c_pdf.line(m_izq, h - (m_sup + 100), m_der, h - (m_sup + 100))  # Línea 1
                        c_pdf.line(m_izq, h - (m_sup + 160), m_der, h - (m_sup + 160))  # Línea 2
                        c_pdf.line(m_izq, h - (m_sup + 250), m_der, h - (m_sup + 250))  # Línea 3
                        c_pdf.line(m_izq, h - (m_sup + 310), m_der, h - (m_sup + 310))  # Línea 4
                        c_pdf.line(m_izq + 120, h - (m_sup + 310), m_izq + 120, h - (m_sup + 360))  # Línea vertical
                        # Encabezado: nombre cooperativa, ciudad, fecha y hora
                        c_pdf.setFont("Helvetica", 9)
                        c_pdf.drawString(m_izq + 10, h - (m_sup + 25), "COOPROLE R.L.")
                        c_pdf.drawString(m_izq + 10, h - (m_sup + 40), "COCHABAMBA - BOLIVIA")
                        c_pdf.drawString(m_izq + 10, h - (m_sup + 55), f"Fecha : {f_pago}")
                        c_pdf.drawString(m_izq + 10, h - (m_sup + 70), f"Hora  : {h_pago}")
                        # Título centrado del comprobante
                        c_pdf.setFont("Helvetica-Bold", 12)
                        c_pdf.drawCentredString(w/2, h - (m_sup + 50), "COMPROBANTE DE PAGO")
                        # Información de serie en esquina superior derecha
                        c_pdf.setFont("Helvetica", 10)
                        c_pdf.drawString(m_der - 150, h - (m_sup + 25), f"SERIE:    {socio.get('serie','')}")
                        c_pdf.drawString(m_der - 150, h - (m_sup + 40), f"{socio.get('nombre_serie','')}")
                        c_pdf.setFont("Helvetica-Bold", 11)
                        c_pdf.drawString(m_der - 150, h - (m_sup + 60), f"Nro :    {f_num}")
                        # Datos del título y acciones
                        c_pdf.setFont("Helvetica", 10)
                        c_pdf.drawString(m_izq + 120, h - (m_sup + 120), f"TITULO:    {datos.get('titulo')}")
                        c_pdf.drawString(m_izq + 10, h - (m_sup + 140), f"Numero de Acciones:    {acciones}")
                        c_pdf.drawString(w/2 + 40, h - (m_sup + 140), f"Importe por accion:    {importe_individual:.2f}")
                        # Monto total en números
                        c_pdf.setFont("Helvetica-Bold", 11)
                        c_pdf.drawString(w/2 - 40, h - (m_sup + 190), f"Monto Total (Bs.):    {monto_t:.2f}")
                        c_pdf.line(w/2 - 40, h - (m_sup + 205), w/2 + 100, h - (m_sup + 205))  # Subrayado
                        c_pdf.drawString(w/2 - 40, h - (m_sup + 230), f"Importe a Pagar Bs.:    {monto_t:.2f}")
                        # Monto en letras (requisito legal)
                        c_pdf.setFont("Helvetica", 10)
                        c_pdf.drawString(m_izq + 10, h - (m_sup + 270), f"Son:    {monto_a_letras(monto_t)}")
                        c_pdf.drawString(m_der - 80, h - (m_sup + 270), "(Bs.-)")
                        # Concepto y gestión
                        c_pdf.drawString(m_izq + 10, h - (m_sup + 295), "Concepto: PAGO DE DIVIDENDOS PROLEC S.A.")
                        c_pdf.drawString(w/2 + 20, h - (m_sup + 295), "Gestion:    2025")
                        # Pie: cajero, firma del socio, CI
                        c_pdf.setFont("Helvetica", 8)
                        c_pdf.drawString(m_izq + 5, h - (m_sup + 345), f"Cajero: {c_nombre}")
                        c_pdf.setFont("Helvetica", 9)
                        c_pdf.drawString(m_izq + 130, h - (m_sup + 330), f"Recibi Conforme:    {datos.get('nombre')}")
                        c_pdf.drawString(m_izq + 130, h - (m_sup + 350), "Firma: ...............................................")
                        c_pdf.drawString(m_der - 140, h - (m_sup + 350), "C.I. ..........................")
                        # Finaliza la página y guarda el PDF en el buffer
                        c_pdf.showPage()
                        c_pdf.save()
                        # Retorna el contenido binario completo del PDF
                        return buf.getvalue()

                    # Verifica si el socio ya pagó (campo 'pagado' es True)
                    if socio.get("pagado"):
                        # Muestra quién, cuándo y con qué formulario se pagó
                        st.subheader(" YA FUE PAGADO POR")
                        st.warning(f"Cajero: {socio.get('cajero')} | Fecha: {socio.get('fecha')} | Hora: {socio.get('hora')} | Formulario: {str(socio.get('nro_formulario')).zfill(5)}")
                        # Genera PDF con los datos históricos del pago
                        pdf_byte = generar_pdf_individual(socio, total, socio.get('cajero'), socio.get('fecha'), socio.get('hora'), socio.get('nro_formulario'))
                        # Botón para descargar el comprobante existente
                        st.download_button("Descargar Comprobante PDF", pdf_byte, f"comprobante_{t_limpio}.pdf")
                    else:
                        # El socio no ha pagado aún
                        st.error("Estado: Pendiente de cobro")
                        # Si NO estamos en modo confirmación, muestra botón para iniciar pago
                        if not st.session_state.confirmar_pago:
                            # Botón que activa la confirmación de pago
                            if st.button("REGISTRAR PAGO AHORA"): 
                                st.session_state.confirmar_pago = True
                                st.rerun()
                        else:
                            # Modo confirmación: pregunta si está seguro de realizar el pago
                            st.warning(f"CONFIRMACION: ¿Pagar a {socio.get('nombre')}?")
                            c_s, c_n = st.columns(2)  # Dos columnas para botones SI/NO
                            with c_s:
                                # Botón de confirmación definitiva
                                if st.button("SI, CONFIRMAR"):
                                    # Busca el máximo número de formulario en la tabla riego (excluyendo nulos)
                                    res_max_ri = supabase.table("riego").select("nro_formulario").not_.is_("nro_formulario", "null").order("nro_formulario", desc=True).limit(1).execute()
                                    # También busca en reversiones para evitar duplicados de numeración
                                    res_max_re = supabase.table("reversiones").select("nro_formulario").not_.is_("nro_formulario", "null").order("nro_formulario", desc=True).limit(1).execute()
                                    # Calcula el nuevo número: máximo de ambas tablas + 1
                                    # Ej: si riego tiene 150 y reversiones 148, nuevo será 151
                                    nuevo_nro = max(int(res_max_ri.data[0]['nro_formulario']) if res_max_ri.data else 0, int(res_max_re.data[0]['nro_formulario']) if res_max_re.data else 0) + 1
                                    # Obtiene fecha y hora actual en zona horaria de Bolivia
                                    tz_bol = pytz.timezone('America/La_Paz')
                                    ahora = datetime.datetime.now(tz_bol)
                                    f_hoy = ahora.strftime("%d/%m/%Y")  # Formato: "12/05/2026"
                                    h_hoy = ahora.strftime("%H:%M:%S")  # Formato: "14:30:45"
                                    # Actualiza registro en BD: marca como pagado, asigna cajero, fecha, hora y nº formulario
                                    supabase.table("riego").update({"pagado": True, "cajero": st.session_state.cajero, "fecha": f_hoy, "hora": h_hoy, "nro_formulario": nuevo_nro}).eq("titulo", socio.get("titulo")).execute()
                                    # Prepara mensaje de éxito
                                    st.session_state.mensaje_exito_cobro = f"COBRO EXITOSO: {socio.get('nombre')} | Form: {str(nuevo_nro).zfill(5)}"
                                    # Genera el PDF del comprobante recién creado
                                    st.session_state.pdf_exito = generar_pdf_individual(socio, total, st.session_state.cajero, f_hoy, h_hoy, nuevo_nro)
                                    st.session_state.pdf_nombre = f"comprobante_{socio.get('titulo')}.pdf"
                                    # Resetea banderas y fuerza recarga del buscador
                                    st.session_state.confirmar_pago = False
                                    st.session_state.busqueda_key += 1
                                    st.rerun()
                            with c_n:
                                # Botón para cancelar la confirmación y volver atrás
                                if st.button("NO, VOLVER"): 
                                    st.session_state.confirmar_pago = False
                                    st.rerun()
                else:
                    # El título buscado no existe en la base de datos
                    st.error("El título buscado no existe en la lista")
            except Exception as e: 
                # Captura cualquier error inesperado y lo muestra
                st.error(f"Error: {e}")

    # --- OPCION 2: LISTADO DE COBROS ---
    elif menu == "Listado de Cobros":
        # Título de la sección de reportes
        st.title("Reporte de Cobros Realizados")
        # Crea dos columnas para seleccionar rango de fechas
        c1, c2 = st.columns(2)
        with c1: 
            # Selector de fecha inicial, por defecto hoy
            f_ini = st.date_input("Fecha Inicial", datetime.date.today())
        with c2: 
            # Selector de fecha final, por defecto hoy
            f_fin = st.date_input("Fecha Final", datetime.date.today())
        # Consulta todas las series y cajeros que tienen pagos registrados
        # SELECT serie, cajero FROM riego WHERE pagado = true
        res_opciones = supabase.table("riego").select("serie, cajero").eq("pagado", True).execute()
        # Extrae series únicas (sin repetir), ordenadas alfabéticamente
        opciones_serie = sorted(list(set([s['serie'] for s in res_opciones.data if s['serie']])))
        # Extrae nombres de cajeros únicos, ordenados alfabéticamente
        opciones_cajero = sorted(list(set([c['cajero'] for c in res_opciones.data if c['cajero']])))
        # Selector múltiple para filtrar por series (puede elegir varias o ninguna = todas)
        series_sel = st.multiselect("Series:", opciones_serie)
        # Selector múltiple para filtrar por cajeros
        cajeros_sel = st.multiselect("Cajeros:", opciones_cajero)
        # Botón para generar el reporte PDF con los filtros seleccionados
        if st.button("Generar Reporte PDF"):
            # Obtiene todos los pagos realizados
            res_pagos = supabase.table("riego").select("*").eq("pagado", True).execute()
            if res_pagos.data:
                # Filtra por rango de fechas y opcionalmente por series y cajeros
                # La comprensión de lista crea una nueva lista solo con los que cumplen condiciones
                filtrados = [p for p in res_pagos.data if f_ini <= datetime.datetime.strptime(p['fecha'], "%d/%m/%Y").date() <= f_fin and (not series_sel or p['serie'] in series_sel) and (not cajeros_sel or p['cajero'] in cajeros_sel)]
                if filtrados:
                    # Ordena por número de formulario (los None van al final con valor 0)
                    filtrados.sort(key=lambda x: x.get('nro_formulario') or 0)
                    # Crea buffer para PDF en memoria
                    buf_list = io.BytesIO()
                    # Crea lienzo PDF tamaño carta
                    c_list = canvas.Canvas(buf_list, pagesize=portrait(letter))
                    w, h = portrait(letter)  # 612 x 792 puntos
                    items_per_page = 40  # Máximo 40 registros por página
                    # Divide la lista filtrada en páginas de 40 elementos
                    # Ej: si hay 85 registros: pag1[0:40], pag2[40:80], pag3[80:85]
                    pages = [filtrados[i:i + items_per_page] for i in range(0, len(filtrados), items_per_page)]
                    # Calcula el total de dinero de todos los registros filtrados
                    total_dinero = sum(float(x.get('importe_accion') or 0) * int(float(x.get('acciones') or 0)) for x in filtrados)
                    # Itera sobre cada página para dibujarla
                    for idx, page_data in enumerate(pages):
                        # Dibuja el logo si existe el archivo
                        if os.path.exists("logo_izquierdo.png"): 
                            c_list.drawImage("logo_izquierdo.png", 40, h - 65, width=65, height=65, preserveAspectRatio=True, mask='auto')
                        # Título del reporte
                        c_list.setFont("Helvetica-Bold", 14)
                        c_list.drawCentredString(w/2, h - 35, "REPORTE DE COBROS DE DIVIDENDOS")
                        # Subtítulo con período
                        c_list.setFont("Helvetica", 9)
                        c_list.drawCentredString(w/2, h - 50, f"Periodo: {f_ini.strftime('%d/%m/%Y')} al {f_fin.strftime('%d/%m/%Y')}")
                        # Texto de filtros aplicados
                        txt_series = ", ".join(series_sel) if series_sel else "TODAS"
                        txt_cajeros = ", ".join(cajeros_sel) if cajeros_sel else "TODOS"
                        c_list.setFont("Helvetica", 8)
                        c_list.drawCentredString(w/2, h - 62, f"Series: {txt_series}")
                        c_list.drawCentredString(w/2, h - 72, f"Cajeros: {txt_cajeros}")
                        # Numeración de página: "1-3", "2-3", "3-3"
                        c_list.drawRightString(w - 40, h - 35, f"{idx+1}-{len(pages)}")
                        # Posición Y inicial de la tabla
                        y_t = h - 95
                        # Línea superior de la tabla
                        c_list.setLineWidth(1)
                        c_list.line(40, y_t + 12, w - 40, y_t + 12)
                        # Encabezados de columnas
                        c_list.setFont("Helvetica-Bold", 7.5)
                        c_list.drawString(45, y_t, "FECHA")
                        c_list.drawString(85, y_t, "HORA")
                        c_list.drawString(120, y_t, "NOMBRE SOCIO")
                        c_list.drawCentredString(260, y_t, "SERIE")
                        c_list.drawCentredString(310, y_t, "TITULO")
                        c_list.drawCentredString(370, y_t, "CAJERO")
                        c_list.drawCentredString(440, y_t, "VALOR")
                        c_list.drawCentredString(495, y_t, "FORM.")
                        c_list.drawCentredString(545, y_t, "TOTAL")
                        # Línea inferior del encabezado
                        c_list.line(40, y_t - 5, w - 40, y_t - 5)
                        # Posición inicial para la primera fila de datos
                        y_row = y_t - 20
                        # Dibuja cada registro de la página actual
                        for item in page_data:
                            # Calcula subtotal: valor acción * cantidad acciones
                            sub = float(item.get('importe_accion') or 0) * int(float(item.get('acciones') or 0))
                            c_list.setFont("Helvetica", 6.5)  # Fuente pequeña para que quepa
                            # Dibuja cada campo en su posición X correspondiente
                            c_list.drawString(45, y_row, str(item.get('fecha') or ""))
                            c_list.drawString(85, y_row, str(item.get('hora') or ""))
                            # Trunca nombre a 26 caracteres para que no se salga del espacio
                            c_list.drawString(120, y_row, (item.get('nombre') or "")[:26])
                            c_list.drawCentredString(260, y_row, str(item.get('serie') or ""))
                            c_list.drawCentredString(310, y_row, str(item.get('titulo')))
                            c_list.drawCentredString(370, y_row, (item.get('cajero') or "")[:15])
                            c_list.drawCentredString(440, y_row, f"{float(item.get('importe_accion')):.2f}")
                            c_list.drawCentredString(495, y_row, f"{item.get('nro_formulario')}")
                            c_list.drawCentredString(545, y_row, f"{sub:.2f}")
                            # Baja 15 puntos para la siguiente fila
                            y_row -= 15 
                        # Si es la última página, agrega el resumen final
                        if idx+1 == len(pages):
                            # Si no hay espacio suficiente, crea nueva página
                            if y_row < 60: 
                                c_list.showPage()
                                y_row = h - 50
                            # Línea de total
                            c_list.setLineWidth(1.2)
                            c_list.line(350, y_row, 560, y_row)
                            c_list.setFont("Helvetica-Bold", 10)
                            c_list.drawString(80, y_row - 15, f"Boletas: {len(filtrados)}")
                            c_list.drawString(350, y_row - 15, "TOTAL BS.")
                            c_list.drawRightString(560, y_row - 15, f"{total_dinero:.2f}")
                        # Finaliza la página actual
                        c_list.showPage()
                    # Guarda el PDF completo
                    c_list.save()
                    # Muestra botón de descarga
                    st.download_button("Descargar Reporte PDF", buf_list.getvalue(), "reporte_cobros.pdf")
                else: 
                    # No hay registros que cumplan los filtros
                    st.warning("No hay registros.")

    # --- OPCION 3: REVERSION DE COBROS ---
    elif menu == "Reversión de Cobros":
        # Título de la sección
        st.title("Reversión / Anulación")
        # Si hay mensaje de éxito de reversión, lo muestra y lo elimina
        if "mensaje_exito_rev" in st.session_state: 
            st.success(st.session_state.mensaje_exito_rev)
            del st.session_state.mensaje_exito_rev
        # Campo de texto para buscar el número de formulario a anular
        form_busca_text = st.text_input("Nro Formulario a anular:", key=f"rev_input_{st.session_state.rev_search_key}")
        # Solo procesa si el usuario ingresó algo
        if form_busca_text:
            # Elimina espacios
            t_busca = form_busca_text.strip()
            # Verifica que sea un número (solo dígitos)
            if t_busca.isdigit():
                try:
                    # Busca en riego un registro pagado con ese número de formulario
                    res_rev = supabase.table("riego").select("*").eq("nro_formulario", int(t_busca)).eq("pagado", True).execute()
                    if res_rev.data:
                        # Obtiene datos del socio a anular
                        socio_rev = res_rev.data[0]
                        # Zona horaria de Bolivia
                        tz_bol = pytz.timezone('America/La_Paz')
                        # Fecha actual en formato "12/05/2026"
                        hoy_bol = datetime.datetime.now(tz_bol).strftime("%d/%m/%Y")
                        # Obtiene el rol del usuario actual (sin espacios)
                        rol = str(st.session_state.rol_usuario).strip()
                        # Verifica permisos: Administrador puede anular cualquier cosa
                        # Cajero solo puede anular SUS PROPIOS cobros realizados HOY
                        if rol == "Administrador" or (socio_rev.get('cajero') == st.session_state.cajero and socio_rev.get('fecha') == hoy_bol):
                            # Muestra información del formulario a anular
                            st.warning(f"Form: {t_busca} - Socio: {socio_rev.get('nombre')}")
                            # Si no está en modo confirmación
                            if not st.session_state.confirmar_reversion:
                                # Botón para iniciar proceso de anulación
                                if st.button("ANULAR FORMULARIO"): 
                                    st.session_state.confirmar_reversion = True
                                    st.rerun()
                            else:
                                # Modo confirmación
                                st.error("¿SEGURO?")
                                c_s, c_n = st.columns(2)
                                with c_s:
                                    if st.button("SI, ANULAR"):
                                        # Obtiene fecha/hora exacta de la reversión
                                        ahora = datetime.datetime.now(tz_bol)
                                        # Copia todos los datos del socio
                                        datos_anulados = socio_rev.copy()
                                        # Agrega campos de reversión
                                        datos_anulados.update({
                                            "fecha_reversion": ahora.strftime("%d/%m/%Y"),
                                            "hora_reversion": ahora.strftime("%H:%M:%S"),
                                            "cajero_reversion": st.session_state.cajero
                                        })
                                        # Inserta en tabla de reversiones (histórico)
                                        supabase.table("reversiones").insert(datos_anulados).execute()
                                        # Limpia campos de pago en tabla riego (deja como no pagado)
                                        supabase.table("riego").update({
                                            "pagado": False,
                                            "cajero": None,
                                            "fecha": None,
                                            "hora": None,
                                            "nro_formulario": None
                                        }).eq("nro_formulario", int(t_busca)).execute()
                                        # Mensaje de éxito y reseteo
                                        st.session_state.mensaje_exito_rev = f"Anulado nro {t_busca}"
                                        st.session_state.confirmar_reversion = False
                                        st.session_state.rev_search_key += 1  # Limpia campo búsqueda
                                        st.rerun()
                                with c_n:
                                    # Cancela la reversión
                                    if st.button("NO, CANCELAR"): 
                                        st.session_state.confirmar_reversion = False
                                        st.rerun()
                        else: 
                            # No tiene permisos (cajero intenta anular cobro de otro día o de otro cajero)
                            st.error("ERROR: Solo Administrador puede anular otros días/cajeros.")
                    else: 
                        # No encontró formulario activo con ese número
                        st.error("No se encontró un cobro activo con ese número de formulario.")
                except Exception as e: 
                    st.error(f"Error en la base de datos: {e}")
            else: 
                # No ingresó un número válido
                st.error("Por favor, ingrese solo números para el formulario.")

    # --- OPCION 4: REPORTE DE REVERSIONES ---
    elif menu == "Reporte de Reversiones":
        # Título de la sección
        st.title("Reporte de Anulados")
        # Selectores de fecha en dos columnas
        c1, c2 = st.columns(2)
        with c1: 
            f_ini = st.date_input("Inicio", datetime.date.today())
        with c2: 
            f_fin = st.date_input("Fin", datetime.date.today())
        # Botón para generar el reporte
        if st.button("Generar Reporte"):
            # Consulta todas las reversiones registradas
            res_p = supabase.table("reversiones").select("*").execute()
            if res_p.data:
                # Filtra por rango de fechas de reversión
                filtrados = [p for p in res_p.data if f_ini <= datetime.datetime.strptime(p['fecha_reversion'], "%d/%m/%Y").date() <= f_fin]
                if filtrados:
                    # Crea PDF en memoria
                    buf_list = io.BytesIO()
                    c_list = canvas.Canvas(buf_list, pagesize=portrait(letter))
                    w, h = portrait(letter)
                    # Paginación: 40 registros por página
                    pages = [filtrados[i:i + 40] for i in range(0, len(filtrados), 40)]
                    # Calcula total anulado
                    total_dinero = sum(float(x.get('importe_accion') or 0) * int(float(x.get('acciones') or 0)) for x in filtrados)
                    # Itera por cada página
                    for idx, page_data in enumerate(pages):
                        # Logo si existe
                        if os.path.exists("logo_izquierdo.png"): 
                            c_list.drawImage("logo_izquierdo.png", 40, h - 65, width=65, height=65, preserveAspectRatio=True, mask='auto')
                        # Encabezado del reporte
                        c_list.setFont("Helvetica-Bold", 14)
                        c_list.drawCentredString(w/2, h - 35, "REPORTE DE ANULACIONES")
                        c_list.setFont("Helvetica", 9)
                        c_list.drawCentredString(w/2, h - 50, f"Periodo: {f_ini.strftime('%d/%m/%Y')} al {f_fin.strftime('%d/%m/%Y')}")
                        c_list.drawRightString(w - 40, h - 35, f"{idx+1}-{len(pages)}")
                        # Posición inicial de tabla
                        y_t = h - 85
                        c_list.setLineWidth(1)
                        c_list.line(40, y_t + 12, w - 40, y_t + 12)
                        # Encabezados de columnas (más compactos que el reporte de cobros)
                        c_list.setFont("Helvetica-Bold", 7)
                        c_list.drawString(45, y_t, "F. REV")        # Fecha reversión
                        c_list.drawString(90, y_t, "H. REV")        # Hora reversión
                        c_list.drawString(135, y_t, "SOCIO")        # Nombre socio
                        c_list.drawCentredString(260, y_t, "TITULO")
                        c_list.drawCentredString(310, y_t, "CAJ. COBRO")  # Cajero que cobró originalmente
                        c_list.drawCentredString(380, y_t, "CAJ. REV")    # Cajero que anuló
                        c_list.drawCentredString(450, y_t, "F. PAGO")     # Fecha del pago original
                        c_list.drawCentredString(510, y_t, "FORM.")       # Número formulario
                        c_list.drawCentredString(555, y_t, "TOTAL")
                        c_list.line(40, y_t - 5, w - 40, y_t - 5)
                        y_row = y_t - 20
                        # Dibuja cada registro
                        for item in page_data:
                            sub = float(item.get('importe_accion') or 0) * int(float(item.get('acciones') or 0))
                            c_list.setFont("Helvetica", 6.5)
                            c_list.drawString(45, y_row, str(item.get('fecha_reversion')))
                            c_list.drawString(90, y_row, str(item.get('hora_reversion')))
                            c_list.drawString(135, y_row, (item.get('nombre') or "")[:25])
                            c_list.drawCentredString(260, y_row, str(item.get('titulo')))
                            c_list.drawCentredString(310, y_row, str(item.get('cajero'))[:12])
                            c_list.drawCentredString(380, y_row, str(item.get('cajero_reversion'))[:12])
                            c_list.drawCentredString(450, y_row, str(item.get('fecha') or ""))
                            c_list.drawCentredString(510, y_row, f"{item.get('nro_formulario')}")
                            c_list.drawCentredString(555, y_row, f"{sub:.2f}")
                            y_row -= 16
                        # Totales en última página
                        if idx+1 == len(pages):
                            if y_row < 60: 
                                c_list.showPage()
                                y_row = h - 50
                            c_list.setLineWidth(1.2)
                            c_list.line(350, y_row, 560, y_row)
                            c_list.setFont("Helvetica-Bold", 10)
                            c_list.drawString(350, y_row - 15, "TOTAL ANULADO BS.")
                            c_list.drawRightString(560, y_row - 15, f"{total_dinero:.2f}")
                        c_list.showPage()
                    c_list.save()
                    # Botón de descarga
                    st.download_button("Descargar Reporte", buf_list.getvalue(), "reporte_reversiones.pdf")
                else: 
                    st.warning("Sin datos.")
