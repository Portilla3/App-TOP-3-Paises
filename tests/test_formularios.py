"""
Los siete formularios TOP aplican las mismas reglas de validación al guardar.

Origen: el 1 de julio de 2026 la validación cruzada entre código y fecha de
nacimiento quedó como bloqueo en los formularios de México y solo como aviso en
Perú, Ecuador y El Salvador (INCIDENTES.md). Estas pruebas fallan si un
formulario vuelve a quedar distinto.
"""
import os, re, sys
import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMULARIOS = ['index.html', 'index_ecuador.html', 'index_elsalvador.html',
               'index_mexico.html', 'index_mexicocij.html',
               'index_montefenix.html', 'index_mahanaim.html']


def _leer(nombre):
    with open(os.path.join(RAIZ, nombre), encoding='utf-8') as f:
        return f.read()


@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_bloquea_codigo_distinto_de_fecha_de_nacimiento(nombre):
    """Al enviar, el cruce código-fecha de nacimiento impide guardar."""
    html = _leer(nombre)
    assert re.search(r'if\s*\(\s*!\s*validarCruceCodigoFecha\(false\)\s*\)', html), \
        f'{nombre} no bloquea el envío cuando el código no coincide con la fecha de nacimiento'


@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_mismo_formato_de_codigo(nombre):
    """El formato del código es el mismo en los siete: 4 letras y 8 números."""
    assert '/^[A-ZÁÉÍÓÚÑ]{4}\\d{8}$/' in _leer(nombre)


@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_mismas_reglas_de_fecha(nombre):
    """Fecha de entrevista no futura ni anterior a 2020; edad entre 5 y 100 años."""
    html = _leer(nombre)
    assert "new Date('2020-01-01')" in html
    assert 'La edad mínima del paciente es 5 años.' in html
    assert 'La edad máxima del paciente es 100 años.' in html
    assert 'La fecha de entrevista no puede ser futura.' in html


@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_el_promedio_por_dia_no_acepta_negativos(nombre):
    """DECISIONES.md, 2026-10-27: negativos bloqueados, sin máximo."""
    html = _leer(nombre)
    entradas = re.findall(r'<input[^>]*class="prom-inp"[^>]*>', html)
    assert entradas, f'{nombre} no tiene campos de promedio'
    assert all('min="0"' in e for e in entradas), f'{nombre}: hay un promedio sin min="0"'
    assert not any('max=' in e for e in entradas), f'{nombre}: el promedio no lleva máximo'
    assert "errMsg.push('El promedio por día no puede ser negativo')" in html, \
        f'{nombre} no bloquea el envío con un promedio negativo'


# ── La base de pacientes no se lee ni se modifica con la llave pública ────────
# DECISIONES.md. Desde el 2026-10-31 el rol público solo puede agregar registros
# (sql/permisos_top_registros.sql). Estas pruebas fallan si un formulario vuelve a
# leer o modificar la base, o si la app vuelve a enlazar los formularios de
# corrección, que ya no pueden funcionar.

@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_el_formulario_de_captura_solo_agrega_registros(nombre):
    html = _leer(nombre)
    llamadas = [m.start() for m in re.finditer(r'rest/v1/top_registros', html)]
    assert llamadas, f'{nombre} no envía a top_registros'
    for i in llamadas:
        tramo = html[i:i + 300]
        assert re.search(r"method\s*:\s*'POST'", tramo), \
            f'{nombre} llama a top_registros con algo distinto de POST'
        assert 'return=minimal' in tramo, \
            f'{nombre} pide de vuelta el registro, y eso exige permiso de lectura'


def test_la_app_no_enlaza_los_formularios_de_correccion():
    assert 'correccion_top_' not in _leer('app.py')


def test_el_permiso_publico_sobre_la_base_es_solo_agregar():
    sql = _leer(os.path.join('sql', 'permisos_top_registros.sql'))
    activo = '\n'.join(l for l in sql.splitlines() if not l.strip().startswith('--'))
    assert 'GRANT INSERT ON public.top_registros TO anon;' in activo
    assert 'REVOKE ALL ON public.top_registros FROM anon, authenticated;' in activo
    assert not re.search(r'GRANT\s+[^;]*(SELECT|UPDATE|DELETE)[^;]*top_registros\s+TO\s+anon', activo)


CORRECCION = ['correccion_top_peru.html', 'correccion_top_ecuador.html',
              'correccion_top_elsalvador.html', 'correccion_top_mexico.html',
              'correccion_top_mexicocij.html', 'correccion_top_montefenix.html',
              'correccion_top_mahanaim.html']


@pytest.mark.parametrize('nombre', CORRECCION)
def test_los_formularios_de_correccion_viejos_solo_remiten_a_la_app(nombre):
    """Desde el 2026-11-01 son un aviso: no llevan llave ni hablan con la base."""
    html = _leer(nombre)
    assert 'monitoreo-tratamiento-top3.streamlit.app' in html
    for prohibido in ('sb_publishable', 'SUPABASE', 'rest/v1', 'fetch('):
        assert prohibido not in html, f'{nombre} todavía contiene {prohibido}'


# ── El rol público solo tiene lo que usa (DECISIONES.md, 2026-11-01) ─────────

def test_el_rol_publico_no_ejecuta_las_funciones_de_ingreso_ni_de_claves():
    sql = _leer(os.path.join('sql', 'permisos_publicos.sql'))
    for f in ('validar_login_centro(text, text)', 'admin_listar_centros(text, text)',
              'admin_crear_clave_centro(text, text, text, text, text)',
              'admin_desactivar_clave_centro(text, text, text)'):
        assert f'REVOKE ALL ON FUNCTION public.{f} FROM PUBLIC, anon, authenticated;' in sql, f
        assert f'GRANT EXECUTE ON FUNCTION public.{f} TO service_role;' in sql, f
    assert 'ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;' in sql


def test_ningun_sql_vuelve_a_abrir_funciones_al_rol_publico():
    carpeta = os.path.join(RAIZ, 'sql')
    for nombre in os.listdir(carpeta):
        if not nombre.endswith('.sql'):
            continue
        sql = _leer(os.path.join('sql', nombre))
        activo = '\n'.join(l for l in sql.splitlines() if not l.strip().startswith('--'))
        assert not re.search(r'GRANT\s+EXECUTE[^;]*TO\s+[^;]*\b(anon|authenticated)\b', activo), nombre


# ── TOP versión 2: etapas con nombre nuevo y fecha de ingreso ─────────────────
# DECISIONES.md, 2026-11-17, "TOP versión 2". Cambia el texto que se ve, no el
# valor que se guarda: los reportes y la base siguen leyendo los mismos valores.

ETAPAS_V2 = [
    ('ingreso', 'Ingreso (inicio del tratamiento)'),
    ('en_tratamiento', 'Revisión durante el tratamiento'),
    ('egreso', 'Egreso (alta o término)'),
    ('seguimiento', 'Después del egreso (post-tratamiento, seguimiento)'),
]
TEXTO_FECHA_INGRESO = ('TOP de ingreso: todas las preguntas se refieren a las 4 semanas '
                       'previas a la fecha de ingreso. Lo ideal es aplicarlo dentro de las '
                       'primeras 2 semanas.')


@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_las_cuatro_etapas_con_su_nombre_nuevo_y_el_mismo_valor(nombre):
    m = re.search(r'<select[^>]*\bid="etapa"[^>]*>(.*?)</select>', _leer(nombre), re.S)
    assert m, f'{nombre} no tiene la lista de etapas'
    opciones = [(v, t.strip()) for v, t in
                re.findall(r'<option value="([^"]*)">(.*?)</option>', m.group(1)) if v]
    assert opciones == ETAPAS_V2, f'{nombre}: {opciones}'


@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_pide_la_fecha_de_ingreso_con_su_texto(nombre):
    html = _leer(nombre)
    assert re.search(r'<input type="date" id="fecha_ingreso"', html), \
        f'{nombre} no tiene el campo fecha_ingreso'
    assert 'Fecha de ingreso al tratamiento' in html
    assert TEXTO_FECHA_INGRESO in re.sub(r'\s+', ' ', html)
    # Oculto hasta que se elige Ingreso.
    assert re.search(r'id="campo_fecha_ingreso" style="display:none', html)


@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_la_fecha_de_ingreso_es_obligatoria_solo_en_ingreso_y_no_posterior(nombre):
    html = _leer(nombre)
    assert "if (document.getElementById('etapa').value === 'ingreso') {" in html
    assert 'Ingrese la fecha de ingreso al tratamiento.' in html
    assert 'La fecha de ingreso no puede ser posterior a la fecha de entrevista.' in html
    # El límite de 30 días se aplica en el análisis, no en el formulario: la
    # validación de la fecha de ingreso no calcula días entre fechas.
    bloque = re.search(r'const fechaIngresoEl = .*?return errores;', html, re.S)
    assert bloque, f'{nombre} no valida la fecha de ingreso'
    assert not re.search(r'\b30\b|getTime|1000\s*\*\s*60|new Date', bloque.group(0)), \
        f'{nombre} pone un límite de días a la fecha de ingreso'


@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_envia_la_fecha_de_ingreso_solo_en_la_etapa_ingreso(nombre):
    html = _leer(nombre)
    assert re.search(r"fecha_ingreso:\s*\(s\('etapa'\)\s*===\s*'ingreso'\)\s*\?\s*"
                     r"s\('fecha_ingreso'\)\s*:\s*null,", html), \
        f'{nombre} no envía fecha_ingreso, o la envía también fuera de Ingreso'
    # La pestaña Corrección de registros lee el payload para saber qué se corrige.
    sys.path.insert(0, RAIZ)
    from pipeline.panel import correccion as C
    pais = {v: k for k, v in C.FORMULARIO_POR_PAIS.items()}[nombre]
    assert 'fecha_ingreso' in C.campos_del_formulario(pais)


@pytest.mark.parametrize('nombre', FORMULARIOS)
def test_el_aviso_de_etapa_explica_reingresos_y_derivaciones(nombre):
    html = _leer(nombre)
    assert 'primer TOP de este tratamiento' in html
    assert 'vuelve después de varios meses o llega derivada de otro lugar' in html
    assert 'acaba de ingresar al centro' not in html
