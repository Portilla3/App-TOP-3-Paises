"""
pipeline.panel.correccion — Pestaña "Corrección de registros" del perfil de país.

El gobierno busca un TOP de su país, cambia los datos que estén mal, escribe el
motivo y guarda. La corrección la aplica la función `corregir_registro()` de la
base, que comprueba que el registro sea del país y anota cada campo cambiado en
`top_correcciones`. Ver DECISIONES.md, "Los registros se corrigen dentro de la
app, con bitácora", y `sql/correccion_registros.sql`.

Qué campos se pueden corregir y qué valores admite cada lista salen del
formulario TOP del país, que es la fuente de verdad: si el formulario cambia, la
corrección cambia con él. Las reglas de validación son las mismas del formulario.

Función expuesta: render(pais, etiquetas=None, realizado_por='', al_guardar=None, api=None)
`api` permite probar sin Supabase (ver tests/test_correccion.py).
"""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime

RAIZ_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FORMULARIO_POR_PAIS = {
    'Perú':               'index.html',
    'Ecuador':            'index_ecuador.html',
    'El Salvador':        'index_elsalvador.html',
    'México':             'index_mexico.html',
    'México CIJ':         'index_mexicocij.html',
    'México Monte Fénix': 'index_montefenix.html',
    'México Mahanaim':    'index_mahanaim.html',
}

SI_NO = {'hurto', 'robo', 'venta_droga', 'rina_pelea', 'otra_accion',
         'vivienda_estable', 'vivienda_basica'}
BOOLEANOS = {'trabajo_na', 'educacion_na'}
ESCALAS = {'salud_psicologica', 'salud_fisica', 'calidad_vida'}
FECHAS = {'fecha_entrevista', 'fecha_nacimiento'}
LISTAS = ('centro', 'etapa', 'sexo', 'sustancia_principal')
OBLIGATORIOS = {'centro', 'etapa', 'codigo_paciente', 'fecha_entrevista',
                'fecha_nacimiento', 'sexo', 'nombre_entrevistador', 'sustancia_principal'}
IDENTIFICACION = ['centro', 'etapa', 'codigo_paciente', 'fecha_entrevista',
                  'fecha_nacimiento', 'sexo', 'nombre_entrevistador', 'sustancia_principal']
TRANSGRESION = ['hurto', 'robo', 'venta_droga', 'rina_pelea', 'otra_accion',
                'otra_accion_desc', 'vif_s4', 'vif_s3', 'vif_s2', 'vif_s1']
VACIO = 'vacío'
RE_CODIGO = re.compile(r'^[A-ZÁÉÍÓÚÑ]{4}\d{8}$')
FECHA_MINIMA = date(2020, 1, 1)

MENSAJES = {
    'motivo':      'Falta el motivo de la corrección.',
    'sin_cambios': 'No hay cambios para guardar.',
    'no_existe':   'Ese registro ya no existe.',
    'otro_pais':   'Ese registro es de otro país o institución.',
    'campo':       'Uno de los campos no se puede corregir.',
}


# ── Lo que se lee del formulario del país ───────────────────────────────────

def _html(pais, raiz=RAIZ_REPO):
    archivo = FORMULARIO_POR_PAIS.get(pais)
    if not archivo:
        return ''
    try:
        with open(os.path.join(raiz, archivo), encoding='utf-8') as fh:
            return fh.read()
    except OSError:
        return ''


def campos_del_formulario(pais, raiz=RAIZ_REPO):
    """Columnas que el formulario del país envía a la base, en su orden."""
    html = _html(pais, raiz)
    m = re.search(r'const payload\s*=\s*\{(.*?)\n\s*\};', html, re.S)
    if not m:
        return []
    campos = []
    for c in re.findall(r'\b([a-z][a-z0-9_]*)\s*:', m.group(1)):
        if c != 'pais' and c not in campos:
            campos.append(c)
    return campos


def opciones_del_formulario(pais, campo, raiz=RAIZ_REPO):
    """Valores que ofrece la lista desplegable `campo` del formulario del país."""
    html = _html(pais, raiz)
    m = re.search(r'<select[^>]*\bid="%s"[^>]*>(.*?)</select>' % re.escape(campo), html, re.S)
    if not m:
        return []
    valores = []
    # Una opción sin `value` vale su texto; la de `value=""` es el "Seleccione".
    for attr, valor, texto in re.findall(r'<option(\s+value="([^"]*)")?[^>]*>(.*?)</option>', m.group(1), re.S):
        v = (valor if attr else texto).strip()
        if v and not v.startswith('—') and v not in valores:
            valores.append(v)
    return valores


# ── Reglas de cada campo ────────────────────────────────────────────────────

def tipo_de(campo):
    if campo in SI_NO:
        return 'si_no'
    if campo in BOOLEANOS:
        return 'booleano'
    if campo in ESCALAS:
        return 'escala'
    if campo in FECHAS:
        return 'fecha'
    if campo in LISTAS:
        return 'lista'
    if campo == 'codigo_paciente':
        return 'codigo'
    if re.search(r'_s[1-4]$', campo):
        return 'semana'
    if campo.endswith('_total'):
        return 'total'
    if campo.endswith('_prom'):
        return 'promedio'
    return 'texto'


def grupo_de(campo):
    if campo in IDENTIFICACION:
        return 'Identificación'
    if campo in TRANSGRESION or campo.startswith('vif_'):
        return 'Transgresión a la norma social'
    if campo in ESCALAS or campo in BOOLEANOS or campo.startswith(('dias_', 'vivienda_')):
        return 'Salud y vida social'
    return 'Consumo de sustancias'


def permitidos(campo, opciones):
    t = tipo_de(campo)
    if t == 'lista':
        return ', '.join(opciones.get(campo, []))
    return {
        'si_no': 'S o N', 'booleano': 'Sí o No', 'escala': 'entero de 0 a 20',
        'fecha': 'AAAA-MM-DD', 'codigo': '4 letras y 8 números (DDMMAAAA)',
        'semana': 'entero de 0 a 7', 'promedio': 'número, 0 o más', 'texto': 'texto libre',
    }.get(t, '')


def a_texto(campo, valor):
    """Cómo se muestra el valor guardado."""
    if valor is None:
        return ''
    t = tipo_de(campo)
    if t == 'si_no':
        s = str(valor).strip().lower()
        return 'S' if s in ('s', 'true', 'sí', 'si') else ('N' if s in ('n', 'false', 'no') else str(valor))
    if t == 'booleano':
        return 'Sí' if valor in (True, 'true') else 'No'
    if t == 'fecha':
        return str(valor)[:10]
    if isinstance(valor, float) and valor == int(valor):
        return str(int(valor))
    return str(valor)


def _fecha(texto):
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            pass
    return None


def normalizar(campo, texto, opciones):
    """
    Valor escrito → (valor para la base, mensaje de error o None).
    `vacío` borra el dato, salvo en los campos obligatorios.
    """
    s = str(texto).strip()
    if s.lower() == VACIO:
        if campo in OBLIGATORIOS:
            return None, 'es obligatorio y no se puede dejar vacío'
        return None, None
    t = tipo_de(campo)
    if t == 'si_no':
        v = s.lower()
        if v in ('s', 'sí', 'si'):
            return 'S', None
        if v in ('n', 'no'):
            return 'N', None
        return None, 'tiene que ser S o N'
    if t == 'booleano':
        v = s.lower()
        if v in ('sí', 'si', 's'):
            return True, None
        if v in ('no', 'n'):
            return False, None
        return None, 'tiene que ser Sí o No'
    if t in ('escala', 'semana'):
        tope = 20 if t == 'escala' else 7
        if not re.fullmatch(r'\d+', s) or int(s) > tope:
            return None, f'tiene que ser un número entero de 0 a {tope}'
        return int(s), None
    if t == 'promedio':
        try:
            n = float(s.replace(',', '.'))
        except ValueError:
            return None, 'tiene que ser un número'
        if n < 0:
            return None, 'no puede ser negativo'
        return (int(n) if n == int(n) else n), None
    if t == 'fecha':
        f = _fecha(s)
        if not f:
            return None, 'no es una fecha válida (AAAA-MM-DD)'
        return f.isoformat(), None
    if t == 'codigo':
        c = s.upper()
        if not RE_CODIGO.match(c):
            return None, 'tiene que tener 4 letras y 8 números'
        return c, None
    if t == 'lista':
        validos = opciones.get(campo, [])
        for v in validos:
            if v.upper() == s.upper():
                return v, None
        return None, 'no está en la lista del formulario: ' + ', '.join(validos)
    if not s:
        return None, 'está vacío'
    return s, None


def _iguales(campo, actual, nuevo):
    if actual is None or nuevo is None:
        return actual is None and nuevo is None
    t = tipo_de(campo)
    if t in ('escala', 'semana', 'promedio', 'total'):
        try:
            return float(actual) == float(nuevo)
        except (TypeError, ValueError):
            return False
    return a_texto(campo, actual) == a_texto(campo, nuevo)


def construir_cambios(registro, escritos, opciones, campos, hoy=None):
    """
    Ediciones del gobierno → (cambios para la base, errores).

    `escritos` es {campo: texto escrito}; lo vacío no cuenta como cambio. Los
    totales de semanas se recalculan solos, como en el formulario. Al final se
    revisan las reglas que cruzan campos: el código con la fecha de nacimiento, y
    las fechas entre sí.
    """
    hoy = hoy or date.today()
    cambios, errores = {}, []
    for campo, texto in escritos.items():
        if texto is None or str(texto).strip() == '' or campo not in campos:
            continue
        if tipo_de(campo) == 'total':
            continue
        valor, error = normalizar(campo, texto, opciones)
        if error:
            errores.append((campo, error))
            continue
        if not _iguales(campo, registro.get(campo), valor):
            cambios[campo] = valor

    # Totales de semanas: suma de las cuatro, con las vacías en cero.
    prefijos = {re.sub(r'_s[1-4]$', '', c) for c in cambios if tipo_de(c) == 'semana'}
    for p in sorted(prefijos):
        total = f'{p}_total'
        if total not in campos:
            continue
        semanas = [cambios.get(f'{p}_s{i}', registro.get(f'{p}_s{i}')) for i in range(1, 5)]
        nuevo = None if all(s is None for s in semanas) else int(sum(int(s or 0) for s in semanas))
        if not _iguales(total, registro.get(total), nuevo):
            cambios[total] = nuevo

    final = dict(registro, **cambios)
    if {'codigo_paciente', 'fecha_nacimiento'} & set(cambios):
        cod, fn = final.get('codigo_paciente'), final.get('fecha_nacimiento')
        if cod and fn and RE_CODIGO.match(str(cod)):
            esperado = f'{str(fn)[8:10]}{str(fn)[5:7]}{str(fn)[0:4]}'
            if str(cod)[4:] != esperado:
                errores.append(('codigo_paciente',
                                'los 8 números del código no coinciden con la fecha de nacimiento'))
    if 'fecha_entrevista' in cambios and final.get('fecha_entrevista'):
        fe = _fecha(str(final['fecha_entrevista'])[:10])
        if fe and fe > hoy:
            errores.append(('fecha_entrevista', 'no puede ser futura'))
        elif fe and fe < FECHA_MINIMA:
            errores.append(('fecha_entrevista', 'no puede ser anterior a 2020'))
    if {'fecha_nacimiento', 'fecha_entrevista'} & set(cambios) and final.get('fecha_nacimiento'):
        fn = _fecha(str(final['fecha_nacimiento'])[:10])
        fe = _fecha(str(final.get('fecha_entrevista') or '')[:10])
        if fn:
            edad = (hoy - fn).days / 365.25
            if edad < 5:
                errores.append(('fecha_nacimiento', 'la edad mínima es 5 años'))
            elif edad > 100:
                errores.append(('fecha_nacimiento', 'la edad máxima es 100 años'))
            elif fe and fn >= fe:
                errores.append(('fecha_nacimiento', 'tiene que ser anterior a la fecha de entrevista'))
    return cambios, errores


def mensaje_error(res):
    return MENSAJES.get((res or {}).get('error'), 'No se pudo guardar la corrección.')


# ── Supabase, con la llave secreta del servidor ─────────────────────────────

class SupabaseAPI:
    def __init__(self, url, llave):
        self.url, self.llave = url.rstrip('/'), llave

    def _pedir(self, ruta, datos=None, metodo='GET'):
        req = urllib.request.Request(
            f'{self.url}/rest/v1/{ruta}', method=metodo,
            data=None if datos is None else json.dumps(datos).encode('utf-8'),
            headers={'apikey': self.llave, 'Authorization': f'Bearer {self.llave}',
                     'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8') or 'null')

    def buscar(self, pais, codigo=None, ident=None):
        filtro = f'pais=eq.{urllib.parse.quote(pais)}'
        if ident is not None:
            filtro += f'&id=eq.{int(ident)}'
        else:
            filtro += f'&codigo_paciente=eq.{urllib.parse.quote(codigo)}'
        return self._pedir(f'top_registros?{filtro}&select=*&order=fecha_entrevista.asc,id.asc') or []

    def historial(self, ident):
        return self._pedir(f'top_correcciones?registro_id=eq.{int(ident)}&select=*&order=fecha.desc') or []

    def corregir(self, payload):
        return self._pedir('rpc/corregir_registro', payload, 'POST') or {}


# ── La pestaña ──────────────────────────────────────────────────────────────

def render(pais, etiquetas=None, realizado_por='', al_guardar=None, api=None):
    import pandas as pd
    import streamlit as st

    etiquetas = etiquetas or {}
    if api is None:
        api = SupabaseAPI(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])
    k = f'corr_{pais}'
    campos = campos_del_formulario(pais)
    if not campos:
        st.error('No se encontró el formulario TOP de este país.')
        return
    opciones = {c: opciones_del_formulario(pais, c) for c in LISTAS}

    st.markdown(
        '<div style="background:#E3F2FD;border-left:4px solid #004AAD;padding:.7rem 1.2rem;'
        'border-radius:6px;margin-bottom:1rem;font-size:.85rem;">'
        '<b>✏️ Corrección de registros.</b> Busque el TOP, escriba solo los datos que hay que '
        'cambiar y el motivo. Cada corrección queda registrada con el valor anterior y el nuevo.'
        '</div>', unsafe_allow_html=True)

    hecho = st.session_state.pop(f'{k}_hecho', None)
    if hecho:
        st.success(f'Corrección guardada en el registro {hecho["id"]}: '
                   f'{hecho["n"]} dato{"s" if hecho["n"] != 1 else ""} cambiado{"s" if hecho["n"] != 1 else ""}.')

    with st.form(f'{k}_buscar'):
        c1, c2 = st.columns([3, 2])
        codigo = c1.text_input('Código del paciente', placeholder='Ej.: ROPE15031985')
        numero = c2.text_input('o N.º de registro', placeholder='Ej.: 2442')
        if st.form_submit_button('Buscar'):
            try:
                if numero.strip():
                    if not numero.strip().isdigit():
                        st.error('El N.º de registro es un número.')
                        return
                    res = api.buscar(pais, ident=int(numero.strip()))
                elif codigo.strip():
                    res = api.buscar(pais, codigo=codigo.strip().upper())
                else:
                    st.warning('Escriba un código o un N.º de registro.')
                    return
            except Exception as e:  # noqa: BLE001
                st.error(f'No se pudo conectar con la base: {str(e)[:150]}')
                return
            st.session_state[f'{k}_res'] = res
            st.session_state.pop(f'{k}_sel', None)

    res = st.session_state.get(f'{k}_res')
    if res is None:
        return
    if not res:
        st.info(f'No hay TOP de {pais} con ese dato.')
        return

    nombres = {r['id']: f'N.º {r["id"]} · {r.get("centro")} · {str(r.get("fecha_entrevista") or "sin fecha")[:10]} · '
               f'{a_texto("etapa", r.get("etapa")) or "sin etapa"}' for r in res}
    sel = st.selectbox(f'{len(res)} TOP encontrado{"s" if len(res) != 1 else ""}. Elija cuál corregir:',
                       list(nombres), format_func=nombres.get, key=f'{k}_sel')
    registro = next(r for r in res if r['id'] == sel)

    try:
        historial = api.historial(sel)
    except Exception:  # noqa: BLE001
        historial = []
    if historial:
        with st.expander(f'Correcciones anteriores de este registro ({len(historial)})'):
            st.dataframe(pd.DataFrame([{
                'Fecha': str(h.get('fecha'))[:16].replace('T', ' '),
                'Dato': etiquetas.get(h.get('campo'), h.get('campo')),
                'Antes': h.get('valor_anterior') or '—', 'Después': h.get('valor_nuevo') or '—',
                'Motivo': h.get('motivo'), 'Quién': h.get('realizado_por')} for h in historial]),
                hide_index=True, width='stretch')


    editables = [c for c in campos if tipo_de(c) != 'total']
    filas = [{'campo': c, 'Grupo': grupo_de(c), 'Dato': etiquetas.get(c, c),
              'Valor actual': a_texto(c, registro.get(c)), 'Valor nuevo': '',
              'Valores permitidos': permitidos(c, opciones)} for c in editables]
    df = pd.DataFrame(filas)
    st.caption('Escriba en "Valor nuevo" solo lo que cambia. Para borrar un dato que no es '
               f'obligatorio, escriba "{VACIO}". Los totales de semanas se recalculan solos.')
    editado = st.data_editor(
        df, key=f'{k}_editor_{sel}', hide_index=True, width='stretch',
        disabled=['Grupo', 'Dato', 'Valor actual', 'Valores permitidos'],
        column_config={'campo': None}, height=420)

    escritos = dict(zip(editado['campo'], editado['Valor nuevo'].fillna('')))
    cambios, errores = construir_cambios(registro, escritos, opciones, campos)
    for campo, error in errores:
        st.error(f'{etiquetas.get(campo, campo)}: {error}.')
    if not cambios:
        return

    st.markdown('**Cambios que se van a guardar**')
    st.dataframe(pd.DataFrame([{'Dato': etiquetas.get(c, c),
                                'Antes': a_texto(c, registro.get(c)) or '—',
                                'Después': a_texto(c, v) or '—'} for c, v in cambios.items()]),
                 hide_index=True, width='stretch')
    with st.form(f'{k}_guardar_{sel}'):
        motivo = st.text_area('Motivo de la corrección (obligatorio)',
                              placeholder='Ej.: el centro confirmó que el paciente ingresaba ese día.')
        if st.form_submit_button('Guardar corrección', disabled=bool(errores)):
            if not motivo.strip():
                st.error(MENSAJES['motivo'])
                return
            try:
                r = api.corregir({'p_id': int(sel), 'p_pais': pais, 'p_cambios': cambios,
                                  'p_motivo': motivo.strip(), 'p_realizado_por': realizado_por})
            except Exception as e:  # noqa: BLE001
                st.error(f'La base rechazó la corrección: {str(e)[:200]}')
                return
            if not r.get('ok'):
                st.error(mensaje_error(r))
                return
            if al_guardar:
                al_guardar()
            st.session_state[f'{k}_hecho'] = {'id': sel, 'n': r.get('cambios', len(cambios))}
            st.session_state.pop(f'{k}_res', None)
            st.rerun()
