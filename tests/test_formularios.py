"""
Los siete formularios TOP aplican las mismas reglas de validación al guardar.

Origen: el 1 de julio de 2026 la validación cruzada entre código y fecha de
nacimiento quedó como bloqueo en los formularios de México y solo como aviso en
Perú, Ecuador y El Salvador (INCIDENTES.md). Estas pruebas fallan si un
formulario vuelve a quedar distinto.
"""
import os, re
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
