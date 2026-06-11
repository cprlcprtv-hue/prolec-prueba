import streamlit as st

# 1. CONFIGURACION DE PAGINA AL INICIO ABSOLUTO
st.set_page_config(page_title="Sistema Prolec - Bolivia", layout="wide")

from supabase import create_client, Client
import datetime
import pytz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, portrait
from reportlab.lib import colors
from num2words import num2words 
import io
import os

# --- INICIALIZACION SILENCIOSA DE VARIABLES ---
if "cajero" not in st.session_state: st.session_state.cajero = None
if "rol_usuario" not in st.session_state: st.session_state.rol_usuario = None
if "confirmar_pago" not in st.session_state: st.session_state.confirmar_pago = False
if "confirmar_reversion" not in st.session_state: st.session_state.confirmar_reversion = False
if "busqueda_key" not in st.session_state: st.session_state.busqueda_key = 0
if "rev_search_key" not in st.session_state: st.session_state.rev_search_key = 0

# --- CONEXION ---
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        url: str = st.secrets["SUPABASE_URL"].strip()
        key: str = st.secrets["SUPABASE_KEY"].strip()
        supabase: Client = create_client(url, key)
    else:
        st.stop()
except Exception:
    st.stop()

# --- LOGO ---
try:
    if os.path.exists("logo_izquierdo.png"):
        st.image("logo_izquierdo.png", width=200)
except:
    pass

def monto_a_letras(monto):
    entero = int(monto)
    decimales = int(round((monto - entero) * 100))
    literal = num2words(entero, lang='es').upper()
    return f"{literal} {decimales:02d}/100"

# --- LOGIN ---
if not st.session_state.cajero:
    st.title("Acceso al Sistema de Cobros")
    with st.form("login"):
        user_input = st.text_input("Nombre de Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            user_query = supabase.table("usuarios_cajeros").select("*").eq("usuario", user_input).eq("password", pass_input).execute()
            if user_query.data:
                st.session_state.cajero = user_query.data[0]['nombre_real']
                st.session_state.rol_usuario = user_query.data[0]['usuario'] 
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
else:
    st.sidebar.info(f"Cajero: {st.session_state.cajero}")
    menu = st.sidebar.radio("Seleccione una opcion:", ["Buscador de Dividendos", "Listado de Cobros", "Reversión de Cobros", "Reporte de Reversiones"])
    
    if st.sidebar.button("Cerrar Sesion"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

    # --- OPCION 1: BUSCADOR ---
    if menu == "Buscador de Dividendos":
        st.title("Buscador de Dividendos")
        if "mensaje_exito_cobro" in st.session_state:
            st.success(st.session_state.mensaje_exito_cobro)
            st.download_button("Descargar Comprobante PDF", st.session_state.pdf_exito, st.session_state.pdf_nombre)
            if st.button("Realizar nueva busqueda"):
                del st.session_state.mensaje_exito_cobro
                del st.session_state.pdf_exito
                del st.session_state.pdf_nombre
                st.rerun()
            st.stop()

        titulo_input = st.text_input("Ingrese Numero de Titulo:", key=f"titulo_input_{st.session_state.busqueda_key}")
        if titulo_input:
            try:
                t_limpio = titulo_input.strip()
                res = supabase.table("riego").select("*").eq("titulo", t_limpio).execute()
                if not res.data and t_limpio.isdigit(): res = supabase.table("riego").select("*").eq("titulo", int(t_limpio)).execute()

                if res.data:
                    socio = res.data[0]
                    acciones = int(float(socio.get("acciones") or 0))
                    importe_individual = float(socio.get("importe_accion") or 0)
                    total = acciones * importe_individual
                    nro_form_raw = socio.get("nro_formulario")
                    st.success(f"Socio Localizado: {socio.get('nombre')}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Serie:** {socio.get('serie','')}")
                        st.write(f"**Nombre Serie:** {socio.get('nombre_serie','')}")
                        st.write(f"**Titulo:** {socio.get('titulo')}")
                        st.write(f"**Nro. Formulario:** {str(nro_form_raw).zfill(5) if nro_form_raw else 'PENDIENTE'}")
                    with col2:
                        st.write(f"**Acciones:** {acciones}"); st.write(f"**Valor Accion:** {importe_individual:.2f} Bs.")
                    with col3:
                        st.metric("Total", f"{total:.2f} Bs.")
                    st.divider()

                    def generar_pdf_individual(datos, monto_t, c_nombre, f_pago, h_pago, n_form):
                        buf = io.BytesIO(); c_pdf = canvas.Canvas(buf, pagesize=portrait(letter)); w, h = portrait(letter)
                        f_num = str(n_form).zfill(5); m_sup = 20; m_izq = 20; m_der = w - 20
                        c_pdf.setLineWidth(0.8); c_pdf.rect(m_izq, h - (m_sup + 360), m_der - m_izq, 360)
                        c_pdf.line(m_izq, h - (m_sup + 100), m_der, h - (m_sup + 100)) 
                        c_pdf.line(m_izq, h - (m_sup + 160), m_der, h - (m_sup + 160)) 
                        c_pdf.line(m_izq, h - (m_sup + 250), m_der, h - (m_sup + 250)) 
                        c_pdf.line(m_izq, h - (m_sup + 310), m_der, h - (m_sup + 310)) 
                        c_pdf.line(m_izq + 120, h - (m_sup + 310), m_izq + 120, h - (m_sup + 360)) 
                        c_pdf.setFont("Helvetica", 9); c_pdf.drawString(m_izq + 10, h - (m_sup + 25), "COOPROLE R.L."); c_pdf.drawString(m_izq + 10, h - (m_sup + 40), "COCHABAMBA - BOLIVIA"); c_pdf.drawString(m_izq + 10, h - (m_sup + 55), f"Fecha : {f_pago}"); c_pdf.drawString(m_izq + 10, h - (m_sup + 70), f"Hora  : {h_pago}")
                        c_pdf.setFont("Helvetica-Bold", 12); c_pdf.drawCentredString(w/2, h - (m_sup + 50), "COMPROBANTE DE PAGO")
                        c_pdf.setFont("Helvetica", 10); c_pdf.drawString(m_der - 150, h - (m_sup + 25), f"SERIE:    {socio.get('serie','')}"); c_pdf.drawString(m_der - 150, h - (m_sup + 40), f"{socio.get('nombre_serie','')}"); c_pdf.setFont("Helvetica-Bold", 11); c_pdf.drawString(m_der - 150, h - (m_sup + 60), f"Nro :    {f_num}")
                        c_pdf.setFont("Helvetica", 10); c_pdf.drawString(m_izq + 120, h - (m_sup + 120), f"TITULO:    {datos.get('titulo')}"); c_pdf.drawString(m_izq + 10, h - (m_sup + 140), f"Numero de Acciones:    {acciones}"); c_pdf.drawString(w/2 + 40, h - (m_sup + 140), f"Importe por accion:    {importe_individual:.2f}")
                        c_pdf.setFont("Helvetica-Bold", 11); c_pdf.drawString(w/2 - 40, h - (m_sup + 190), f"Monto Total (Bs.):    {monto_t:.2f}"); c_pdf.line(w/2 - 40, h - (m_sup + 205), w/2 + 100, h - (m_sup + 205)); c_pdf.drawString(w/2 - 40, h - (m_sup + 230), f"Importe a Pagar Bs.:    {monto_t:.2f}")
                        c_pdf.setFont("Helvetica", 10); c_pdf.drawString(m_izq + 10, h - (m_sup + 270), f"Son:    {monto_a_letras(monto_t)}"); c_pdf.drawString(m_der - 80, h - (m_sup + 270), "(Bs.-)")
                        c_pdf.drawString(m_izq + 10, h - (m_sup + 295), "Concepto: PAGO DE DIVIDENDOS PROLEC S.A."); c_pdf.drawString(w/2 + 20, h - (m_sup + 295), "Gestion:    2025")
                        c_pdf.setFont("Helvetica", 8); c_pdf.drawString(m_izq + 5, h - (m_sup + 345), f"Cajero: {c_nombre}"); c_pdf.setFont("Helvetica", 9); c_pdf.drawString(m_izq + 130, h - (m_sup + 330), f"Recibi Conforme:    {datos.get('nombre')}"); c_pdf.drawString(m_izq + 130, h - (m_sup + 350), "Firma: ..............................................."); c_pdf.drawString(m_der - 140, h - (m_sup + 350), "C.I. ..........................")
                        c_pdf.showPage(); c_pdf.save(); return buf.getvalue()

                    if socio.get("pagado"):
                        st.subheader(" YA FUE PAGADO POR")
                        st.warning(f"Cajero: {socio.get('cajero')} | Fecha: {socio.get('fecha')} | Hora: {socio.get('hora')} | Formulario: {str(socio.get('nro_formulario')).zfill(5)}")
                        pdf_byte = generar_pdf_individual(socio, total, socio.get('cajero'), socio.get('fecha'), socio.get('hora'), socio.get('nro_formulario'))
                        st.download_button("Descargar Comprobante PDF", pdf_byte, f"comprobante_{t_limpio}.pdf")
                    else:
                        st.error("Estado: Pendiente de cobro")
                        if not st.session_state.confirmar_pago:
                            if st.button("REGISTRAR PAGO AHORA"): st.session_state.confirmar_pago = True; st.rerun()
                        else:
                            st.warning(f"CONFIRMACION: ¿Pagar a {socio.get('nombre')}?"); c_s, c_n = st.columns(2)
                            with c_s:
                                if st.button("SI, CONFIRMAR"):
                                    res_max_ri = supabase.table("riego").select("nro_formulario").not_.is_("nro_formulario", "null").order("nro_formulario", desc=True).limit(1).execute()
                                    res_max_re = supabase.table("reversiones").select("nro_formulario").not_.is_("nro_formulario", "null").order("nro_formulario", desc=True).limit(1).execute()
                                    max_ri = int(res_max_ri.data[0]['nro_formulario']) if res_max_ri.data and res_max_ri.data[0]['nro_formulario'] else 0
                                    max_re = int(res_max_re.data[0]['nro_formulario']) if res_max_re.data and res_max_re.data[0]['nro_formulario'] else 0
                                    nuevo_nro = str(max(max_ri, max_re) + 1).zfill(5)
                                    tz_bol = pytz.timezone('America/La_Paz'); ahora = datetime.datetime.now(tz_bol); f_hoy = ahora.strftime("%d/%m/%Y"); h_hoy = ahora.strftime("%H:%M:%S")
                                    supabase.table("riego").update({"pagado": True, "cajero": st.session_state.cajero, "fecha": f_hoy, "hora": h_hoy, "nro_formulario": nuevo_nro}).eq("titulo", socio.get("titulo")).execute()
                                    st.session_state.mensaje_exito_cobro = f"COBRO EXITOSO: {socio.get('nombre')} | Form: {str(nuevo_nro).zfill(5)}"
                                    st.session_state.pdf_exito = generar_pdf_individual(socio, total, st.session_state.cajero, f_hoy, h_hoy, nuevo_nro)
                                    st.session_state.pdf_nombre = f"comprobante_{socio.get('titulo')}.pdf"
                                    st.session_state.confirmar_pago = False; st.session_state.busqueda_key += 1; st.rerun()
                            with c_n:
                                if st.button("NO, VOLVER"): st.session_state.confirmar_pago = False; st.rerun()
                else:
                    st.error("El título buscado no existe en la lista")
            except Exception as e: st.error(f"Error: {e}")

    # --- OPCION 2: LISTADO DE COBROS ---
    elif menu == "Listado de Cobros":
        st.title("Reporte de Cobros Realizados")
        c1, c2 = st.columns(2)
        with c1: f_ini = st.date_input("Fecha Inicial", datetime.date.today())
        with c2: f_fin = st.date_input("Fecha Final", datetime.date.today())
        res_opciones = supabase.table("riego").select("serie, cajero").eq("pagado", True).execute()
        opciones_serie = sorted(list(set([s['serie'] for s in res_opciones.data if s['serie']])))
        opciones_cajero = sorted(list(set([c['cajero'] for c in res_opciones.data if c['cajero']])))
        series_sel = st.multiselect("Series:", opciones_serie); cajeros_sel = st.multiselect("Cajeros:", opciones_cajero)
        if st.button("Generar Reporte PDF"):
            res_pagos = supabase.table("riego").select("*").eq("pagado", True).execute()
            if res_pagos.data:
                filtrados = [p for p in res_pagos.data if f_ini <= datetime.datetime.strptime(p['fecha'], "%d/%m/%Y").date() <= f_fin and (not series_sel or p['serie'] in series_sel) and (not cajeros_sel or p['cajero'] in cajeros_sel)]
                if filtrados:
                    filtrados.sort(key=lambda x: int(str(x.get('nro_formulario') or '0'))); buf_list = io.BytesIO(); c_list = canvas.Canvas(buf_list, pagesize=portrait(letter)); w, h = portrait(letter); items_per_page = 40; pages = [filtrados[i:i + items_per_page] for i in range(0, len(filtrados), items_per_page)]; total_dinero = sum(float(x.get('importe_accion') or 0) * int(float(x.get('acciones') or 0)) for x in filtrados)
                    for idx, page_data in enumerate(pages):
                        if os.path.exists("logo_izquierdo.png"): c_list.drawImage("logo_izquierdo.png", 40, h - 65, width=65, height=65, preserveAspectRatio=True, mask='auto')
                        c_list.setFont("Helvetica-Bold", 14); c_list.drawCentredString(w/2, h - 35, "REPORTE DE COBROS DE DIVIDENDOS"); c_list.setFont("Helvetica", 9); c_list.drawCentredString(w/2, h - 50, f"Periodo: {f_ini.strftime('%d/%m/%Y')} al {f_fin.strftime('%d/%m/%Y')}")
                        txt_series = ", ".join(series_sel) if series_sel else "TODAS"
                        txt_cajeros = ", ".join(cajeros_sel) if cajeros_sel else "TODOS"
                        c_list.setFont("Helvetica", 8)
                        c_list.drawCentredString(w/2, h - 62, f"Series: {txt_series}")
                        c_list.drawCentredString(w/2, h - 72, f"Cajeros: {txt_cajeros}")
                        c_list.drawRightString(w - 40, h - 35, f"{idx+1}-{len(pages)}")
                        y_t = h - 95; c_list.setLineWidth(1); c_list.line(40, y_t + 12, w - 40, y_t + 12); c_list.setFont("Helvetica-Bold", 7.5)
                        c_list.drawString(45, y_t, "FECHA"); c_list.drawString(85, y_t, "HORA"); c_list.drawString(120, y_t, "NOMBRE SOCIO")
                        c_list.drawCentredString(260, y_t, "SERIE"); c_list.drawCentredString(310, y_t, "TITULO"); c_list.drawCentredString(370, y_t, "CAJERO")
                        c_list.drawCentredString(440, y_t, "VALOR"); c_list.drawCentredString(495, y_t, "FORM."); c_list.drawCentredString(545, y_t, "TOTAL"); c_list.line(40, y_t - 5, w - 40, y_t - 5); y_row = y_t - 20
                        for item in page_data:
                            sub = float(item.get('importe_accion') or 0) * int(float(item.get('acciones') or 0))
                            c_list.setFont("Helvetica", 6.5)
                            c_list.drawString(45, y_row, str(item.get('fecha') or ""))
                            c_list.drawString(85, y_row, str(item.get('hora') or ""))
                            c_list.drawString(120, y_row, (item.get('nombre') or "")[:26])
                            c_list.drawCentredString(260, y_row, str(item.get('serie') or ""))
                            c_list.drawCentredString(310, y_row, str(item.get('titulo')))
                            c_list.drawCentredString(370, y_row, (item.get('cajero') or "")[:15])
                            c_list.drawCentredString(440, y_row, f"{float(item.get('importe_accion')):.2f}")
                            c_list.drawCentredString(495, y_row, str(item.get('nro_formulario') or '').zfill(5))
                            c_list.drawCentredString(545, y_row, f"{sub:.2f}")
                            y_row -= 15 
                        if idx+1 == len(pages):
                            if y_row < 60: c_list.showPage(); y_row = h - 50
                            c_list.setLineWidth(1.2); c_list.line(350, y_row, 560, y_row); c_list.setFont("Helvetica-Bold", 10); c_list.drawString(80, y_row - 15, f"Boletas: {len(filtrados)}"); c_list.drawString(350, y_row - 15, "TOTAL BS."); c_list.drawRightString(560, y_row - 15, f"{total_dinero:.2f}")
                        c_list.showPage()
                    c_list.save(); st.download_button("Descargar Reporte PDF", buf_list.getvalue(), "reporte_cobros.pdf")
                else: st.warning("No hay registros.")

    # --- OPCION 3: REVERSION DE COBROS ---
    elif menu == "Reversión de Cobros":
        st.title("Reversión / Anulación")
        if "mensaje_exito_rev" in st.session_state: st.success(st.session_state.mensaje_exito_rev); del st.session_state.mensaje_exito_rev
        form_busca_text = st.text_input("Nro Formulario a anular:", key=f"rev_input_{st.session_state.rev_search_key}")
        if form_busca_text:
            t_busca = form_busca_text.strip()
            if t_busca.isdigit():
                try:
                    res_rev = supabase.table("riego").select("*").eq("nro_formulario", str(int(t_busca)).zfill(5)).eq("pagado", True).execute()
                    if res_rev.data:
                        socio_rev = res_rev.data[0]; tz_bol = pytz.timezone('America/La_Paz'); hoy_bol = datetime.datetime.now(tz_bol).strftime("%d/%m/%Y")
                        rol = str(st.session_state.rol_usuario).strip()
                        if rol == "Administrador" or (socio_rev.get('cajero') == st.session_state.cajero and socio_rev.get('fecha') == hoy_bol):
                            st.warning(f"Form: {t_busca} - Socio: {socio_rev.get('nombre')}"); 
                            if not st.session_state.confirmar_reversion:
                                if st.button("ANULAR FORMULARIO"): st.session_state.confirmar_reversion = True; st.rerun()
                            else:
                                st.error("¿SEGURO?"); c_s, c_n = st.columns(2)
                                with c_s:
                                    if st.button("SI, ANULAR"):
                                        ahora = datetime.datetime.now(tz_bol); datos_anulados = socio_rev.copy()
                                        datos_anulados.update({"fecha_reversion": ahora.strftime("%d/%m/%Y"), "hora_reversion": ahora.strftime("%H:%M:%S"), "cajero_reversion": st.session_state.cajero})
                                        supabase.table("reversiones").insert(datos_anulados).execute()
                                        supabase.table("riego").update({"pagado": False, "cajero": None, "fecha": None, "hora": None, "nro_formulario": None}).eq("nro_formulario", str(int(t_busca)).zfill(5)).execute()
                                        st.session_state.mensaje_exito_rev = f"Anulado nro {t_busca}"; st.session_state.confirmar_reversion = False; st.session_state.rev_search_key += 1; st.rerun()
                                with c_n:
                                    if st.button("NO, CANCELAR"): st.session_state.confirmar_reversion = False; st.rerun()
                        else: st.error("ERROR: Solo Administrador puede anular otros días/cajeros.")
                    else: st.error("No se encontró un cobro activo con ese número de formulario.")
                except Exception as e: st.error(f"Error en la base de datos: {e}")
            else: st.error("Por favor, ingrese solo números para el formulario.")

    # --- OPCION 4: REPORTE DE REVERSIONES ---
    elif menu == "Reporte de Reversiones":
        st.title("Reporte de Anulados")
        c1, c2 = st.columns(2)
        with c1: f_ini = st.date_input("Inicio", datetime.date.today())
        with c2: f_fin = st.date_input("Fin", datetime.date.today())
        if st.button("Generar Reporte"):
            res_p = supabase.table("reversiones").select("*").execute()
            if res_p.data:
                filtrados = [p for p in res_p.data if f_ini <= datetime.datetime.strptime(p['fecha_reversion'], "%d/%m/%Y").date() <= f_fin]
                if filtrados:
                    buf_list = io.BytesIO(); c_list = canvas.Canvas(buf_list, pagesize=portrait(letter)); w, h = portrait(letter); pages = [filtrados[i:i + 40] for i in range(0, len(filtrados), 40)]; total_dinero = sum(float(x.get('importe_accion') or 0) * int(float(x.get('acciones') or 0)) for x in filtrados)
                    for idx, page_data in enumerate(pages):
                        if os.path.exists("logo_izquierdo.png"): c_list.drawImage("logo_izquierdo.png", 40, h - 65, width=65, height=65, preserveAspectRatio=True, mask='auto')
                        c_list.setFont("Helvetica-Bold", 14); c_list.drawCentredString(w/2, h - 35, "REPORTE DE ANULACIONES"); c_list.setFont("Helvetica", 9); c_list.drawCentredString(w/2, h - 50, f"Periodo: {f_ini.strftime('%d/%m/%Y')} al {f_fin.strftime('%d/%m/%Y')}"); c_list.drawRightString(w - 40, h - 35, f"{idx+1}-{len(pages)}")
                        y_t = h - 85; c_list.setLineWidth(1); c_list.line(40, y_t + 12, w - 40, y_t + 12); c_list.setFont("Helvetica-Bold", 7)
                        c_list.drawString(45, y_t, "F. REV"); c_list.drawString(90, y_t, "H. REV"); c_list.drawString(135, y_t, "SOCIO"); c_list.drawCentredString(260, y_t, "TITULO"); c_list.drawCentredString(310, y_t, "CAJ. COBRO"); c_list.drawCentredString(380, y_t, "CAJ. REV"); c_list.drawCentredString(450, y_t, "F. PAGO"); c_list.drawCentredString(510, y_t, "FORM."); c_list.drawCentredString(555, y_t, "TOTAL"); c_list.line(40, y_t - 5, w - 40, y_t - 5); y_row = y_t - 20
                        for item in page_data:
                            sub = float(item.get('importe_accion') or 0) * int(float(item.get('acciones') or 0))
                            c_list.setFont("Helvetica", 6.5); c_list.drawString(45, y_row, str(item.get('fecha_reversion'))); c_list.drawString(90, y_row, str(item.get('hora_reversion'))); c_list.drawString(135, y_row, (item.get('nombre') or "")[:25]); c_list.drawCentredString(260, y_row, str(item.get('titulo'))); c_list.drawCentredString(310, y_row, str(item.get('cajero'))[:12]); c_list.drawCentredString(380, y_row, str(item.get('cajero_reversion'))[:12]); c_list.drawCentredString(450, y_row, str(item.get('fecha') or "")); c_list.drawCentredString(510, y_row, f"{item.get('nro_formulario')}"); c_list.drawCentredString(555, y_row, f"{sub:.2f}"); y_row -= 16
                        if idx+1 == len(pages):
                            if y_row < 60: c_list.showPage(); y_row = h - 50
                            c_list.setLineWidth(1.2); c_list.line(350, y_row, 560, y_row); c_list.setFont("Helvetica-Bold", 10); c_list.drawString(350, y_row - 15, "TOTAL ANULADO BS."); c_list.drawRightString(560, y_row - 15, f"{total_dinero:.2f}")
                        c_list.showPage()
                    c_list.save(); st.download_button("Descargar Reporte", buf_list.getvalue(), "reporte_reversiones.pdf")
                else: st.warning("Sin datos.")
