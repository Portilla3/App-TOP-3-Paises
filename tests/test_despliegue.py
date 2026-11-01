"""Reglas de despliegue (DECISIONES.md, "Las versiones se fijan exactas").

Producción instala lo que dice requirements.txt cada vez que la app se
reinicia. Con rangos, cada reinicio podía traer una versión que nadie probó.
"""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _leer(*partes):
    with open(os.path.join(RAIZ, *partes), encoding='utf-8') as f:
        return f.read()


def _requisitos():
    lineas = [l.split('#')[0].strip() for l in _leer('requirements.txt').splitlines()]
    return [l for l in lineas if l]


def test_cada_requisito_tiene_version_exacta():
    for linea in _requisitos():
        assert re.fullmatch(r'[A-Za-z0-9_.\-]+==[0-9][0-9A-Za-z.]*', linea), linea


def test_cada_requisito_aparece_una_sola_vez():
    nombres = [l.split('==')[0].lower().replace('_', '-') for l in _requisitos()]
    assert len(nombres) == len(set(nombres))


def test_pyarrow_queda_bajo_la_version_que_se_cae():
    version = dict(l.split('==') for l in _requisitos())['pyarrow']
    assert int(version.split('.')[0]) < 25


def test_las_pruebas_automaticas_usan_python_314_y_las_versiones_de_produccion():
    flujo = _leer('.github', 'workflows', 'pruebas.yml')
    assert "python-version: '3.14'" in flujo
    assert 'pip install -r requirements.txt' in flujo
    assert 'pytest tests/' in flujo


def test_no_se_usa_use_container_width():
    """Streamlit lo marcó para retirar; cuando lo retire, la app no arranca."""
    archivos = [os.path.join(RAIZ, 'app.py')]
    for base, _, nombres in os.walk(os.path.join(RAIZ, 'pipeline')):
        archivos += [os.path.join(base, n) for n in nombres if n.endswith('.py')]
    for ruta in archivos:
        with open(ruta, encoding='utf-8') as f:
            assert 'use_container_width' not in f.read(), ruta
