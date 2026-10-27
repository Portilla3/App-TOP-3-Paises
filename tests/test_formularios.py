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
