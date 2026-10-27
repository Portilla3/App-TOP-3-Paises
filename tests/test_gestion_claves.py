# -*- coding: utf-8 -*-
"""
Gestión de claves de centros por cada gobierno (DECISIONES.md, 2026-10-27).

Revisa dos cosas: que el SQL versionado mantenga sus reglas de seguridad, y que
la pestaña de la app use bien las funciones, con un Supabase simulado.
"""
import os
import re
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

with open(os.path.join(RAIZ, 'sql', 'admin_claves_centros.sql'), encoding='utf-8') as _fh:
    SQL = _fh.read()

PUBLICAS = ['admin_listar_centros', 'admin_crear_clave_centro', 'admin_desactivar_clave_centro']


def _cuerpo(nombre):
    m = re.search(r'FUNCTION public\.' + nombre + r'\(.*?\$function\$(.*?)\$function\$', SQL, re.S)
    assert m, nombre + ' no está en el SQL'
    return m.group(0)


def test_la_tabla_de_administradores_no_se_lee_desde_afuera():
    assert 'ALTER TABLE public.pais_admin ENABLE ROW LEVEL SECURITY' in SQL
    assert 'REVOKE ALL ON public.pais_admin FROM anon, authenticated' in SQL
    assert 'GRANT SELECT ON public.pais_admin' not in SQL
    # Protección declarada, no por ausencia de política (DECISIONES.md, Seguridad).
    assert re.search(r'CREATE POLICY deny_all_pais_admin ON public\.pais_admin AS RESTRICTIVE\s+FOR ALL', SQL)


@pytest.mark.parametrize('nombre', PUBLICAS + ['_admin_pais_valido'])
def test_las_funciones_corren_como_su_duenio_con_search_path_fijo(nombre):
    cuerpo = _cuerpo(nombre)
    assert 'SECURITY DEFINER' in cuerpo
    assert "SET search_path TO 'public', 'extensions'" in cuerpo


@pytest.mark.parametrize('nombre', PUBLICAS)
def test_cada_funcion_publica_exige_la_clave_de_administrador(nombre):
    cuerpo = _cuerpo(nombre)
    primera = cuerpo.split('BEGIN', 1)[1].split('END IF;', 1)[0]
    assert '_admin_pais_valido(p_pais, p_clave)' in primera, 'la verificación tiene que ir primero'


def test_una_clave_incorrecta_no_levanta_excepcion():
    """Una excepción desharía el registro del intento fallido y el bloqueo no funcionaría."""
    for nombre in PUBLICAS + ['_admin_pais_valido']:
        assert 'RAISE EXCEPTION' not in _cuerpo(nombre), nombre


def test_hay_bloqueo_por_intentos_fallidos():
    cuerpo = _cuerpo('_admin_pais_valido')
    assert "accion = 'admin_fallido'" in cuerpo and "interval '15 minutes'" in cuerpo
    assert 'v_fallos >= 5' in cuerpo


def test_las_internas_no_se_pueden_llamar_desde_la_app():
    assert re.search(r'REVOKE ALL ON FUNCTION public\._admin_pais_valido\(text, text\) FROM PUBLIC, anon, authenticated', SQL)
    assert re.search(r'REVOKE ALL ON FUNCTION public\._clave_aleatoria\(integer\) FROM PUBLIC, anon, authenticated', SQL)
    assert not re.search(r'GRANT EXECUTE ON FUNCTION public\._', SQL)


def test_la_clave_nueva_no_se_guarda_ni_se_registra_en_texto():
    cuerpo = _cuerpo('admin_crear_clave_centro')
    assert 'crypt(v_nueva, gen_salt(' in cuerpo
    bitacora = re.findall(r'INSERT INTO centro_bitacora.*?;', cuerpo, re.S)
    assert bitacora and all('v_nueva' not in b for b in bitacora)


def test_ninguna_clave_de_administrador_queda_en_el_repositorio():
    assert not re.search(r"^\s*INSERT INTO pais_admin", SQL, re.M), 'el INSERT de pais_admin va solo comentado'


# ── La pestaña de la app, con un Supabase simulado ─────────────────────────

class SupabaseFalso:
    def __init__(self):
        self.llamadas = []
        self.centros = [
            {'centro': 'EESS02SB', 'registros': 30, 'ultimo_top': '2026-10-01', 'tiene_clave': True,
             'clave_activa': True, 'correo': 'a@b.pe', 'responsable': 'Gladys',
             'ultimo_ingreso': '2026-10-20T10:00:00'},
            {'centro': 'EESS13C', 'registros': 12, 'ultimo_top': '2026-09-30', 'tiene_clave': False,
             'clave_activa': False, 'correo': None, 'responsable': None, 'ultimo_ingreso': None},
        ]

    def __call__(self, nombre, payload):
        self.llamadas.append((nombre, payload))
        if payload.get('p_clave') != 'admin':
            return {'ok': False, 'error': 'clave'}
        if nombre == 'admin_listar_centros':
            return {'ok': True, 'centros': self.centros}
        if nombre == 'admin_crear_clave_centro':
            return {'ok': True, 'accion': 'clave_creada', 'centro': payload['p_centro'], 'clave': 'Xy7kP2mQ9a'}
        return {'ok': True}


def test_la_tabla_muestra_el_estado_de_cada_clave():
    pytest.importorskip('streamlit')
    from pipeline.panel.gestion_claves import tabla_centros
    df = tabla_centros(SupabaseFalso().centros)
    assert list(df['Clave']) == ['Activa', 'Sin clave']
    assert list(df['Último ingreso']) == ['2026-10-20', '—']


def test_cada_error_tiene_su_mensaje():
    pytest.importorskip('streamlit')
    from pipeline.panel.gestion_claves import MENSAJES, mensaje_error
    for codigo in ('clave', 'centro', 'correo', 'otro_pais', 'sin_clave'):
        assert mensaje_error({'ok': False, 'error': codigo}) == MENSAJES[codigo]
    errores_sql = set(re.findall(r"'error', '([a-z_]+)'", SQL))
    assert errores_sql <= set(MENSAJES), 'errores del SQL sin mensaje: ' + str(errores_sql - set(MENSAJES))


def _app_claves():
    import sys
    sys.path.insert(0, RAIZ_APP)
    import streamlit as st
    from pipeline.panel.gestion_claves import render
    from tests.test_gestion_claves import SupabaseFalso
    if 'falso' not in st.session_state:
        st.session_state['falso'] = SupabaseFalso()
    render('Perú', llamar=st.session_state['falso'])


def test_la_pestania_pide_la_clave_y_muestra_la_nueva_una_sola_vez():
    pytest.importorskip('streamlit')
    from streamlit.testing.v1 import AppTest
    src = 'RAIZ_APP = ' + repr(RAIZ) + '\n'
    import inspect
    src += inspect.getsource(_app_claves).replace('def _app_claves():', 'def _app():') + '\n_app()\n'
    at = AppTest.from_string(src, default_timeout=30)
    at.run()
    assert not at.exception
    assert at.text_input[0].label == 'Clave de administrador'

    at.text_input[0].input('mala')
    at.button[0].click().run()
    assert any('incorrecta' in e.value for e in at.error)

    at.text_input[0].input('admin')
    at.button[0].click().run()
    assert not at.exception
    assert at.dataframe, 'no se muestra la tabla de centros'

    at.selectbox[0].select('EESS13C')
    at.text_input[1].input('c@minsa.pe')
    at.button[0].click().run()
    assert any('Xy7kP2mQ9a' in c.value for c in at.code), 'no se muestra la clave nueva'
    at.run()
    assert not any('Xy7kP2mQ9a' in c.value for c in at.code), 'la clave nueva se vuelve a mostrar'


def test_monte_fenix_y_mahanaim_no_administran_claves():
    """Cada una es un solo centro: su perfil de institución ya es el del centro."""
    import ast
    with open(os.path.join(RAIZ, 'app.py'), encoding='utf-8') as fh:
        arbol = ast.parse(fh.read())
    valores = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 and \
                getattr(nodo.targets[0], 'id', None) in ('SIN_GESTION_DE_CLAVES', 'PAISES_CON_CLAVES'):
            valores[nodo.targets[0].id] = ast.literal_eval(nodo.value)
    assert valores['SIN_GESTION_DE_CLAVES'] == {'México Monte Fénix', 'México Mahanaim'}
    assert not set(valores['PAISES_CON_CLAVES']) & valores['SIN_GESTION_DE_CLAVES']
