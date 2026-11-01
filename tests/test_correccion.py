# -*- coding: utf-8 -*-
"""
Corrección de registros dentro de la app (DECISIONES.md, 2026-11-01).

Revisa tres cosas: que el SQL mantenga sus reglas de seguridad, que la pestaña
lea del formulario de cada país los campos y las listas, y que las reglas de
validación sean las del formulario. Si `pgserver` está instalado, además prueba
la función `corregir_registro()` en un Postgres de verdad.
"""
import os
import re
import sys
from datetime import date

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from pipeline.panel import correccion as C  # noqa: E402

with open(os.path.join(RAIZ, 'sql', 'correccion_registros.sql'), encoding='utf-8') as _fh:
    SQL = _fh.read()

PAISES = list(C.FORMULARIO_POR_PAIS)
HOY = date(2026, 11, 1)


# ── SQL ─────────────────────────────────────────────────────────────────────

def _cuerpo(nombre):
    m = re.search(r'FUNCTION public\.' + nombre + r'\(.*?\$function\$(.*?)\$function\$', SQL, re.S)
    assert m, nombre + ' no está en el SQL'
    return m.group(0)


def test_la_funcion_solo_la_llama_la_llave_secreta():
    firma = r'public\.corregir_registro\(bigint, text, jsonb, text, text\)'
    assert re.search(r'REVOKE ALL ON FUNCTION ' + firma + r' FROM PUBLIC, anon, authenticated', SQL)
    assert re.search(r'GRANT EXECUTE ON FUNCTION ' + firma + r' TO service_role;', SQL)
    assert not re.search(r'GRANT[^;]*corregir_registro[^;]*TO (anon|authenticated)', SQL)


@pytest.mark.parametrize('tabla', ['top_correcciones', 'top_registros_auditoria'])
def test_las_bitacoras_no_se_leen_desde_afuera(tabla):
    assert f'ALTER TABLE public.{tabla} ENABLE ROW LEVEL SECURITY' in SQL
    assert f'REVOKE ALL ON public.{tabla} FROM anon, authenticated' in SQL


@pytest.mark.parametrize('nombre', ['corregir_registro', '_auditar_top_registros'])
def test_las_funciones_corren_como_su_duenio_con_search_path_fijo(nombre):
    cuerpo = _cuerpo(nombre)
    assert 'SECURITY DEFINER' in cuerpo
    assert "SET search_path TO 'public'" in cuerpo


def test_la_auditoria_cubre_toda_modificacion_y_borrado():
    assert re.search(r'CREATE TRIGGER trg_auditar_top_registros\s+AFTER UPDATE OR DELETE ON public\.top_registros', SQL)


def test_la_correccion_revisa_todo_antes_de_tocar_el_registro():
    cuerpo = _cuerpo('corregir_registro')
    actualiza = cuerpo.index("EXECUTE format('UPDATE top_registros")
    for error in ('motivo', 'sin_cambios', 'no_existe', 'otro_pais', 'campo'):
        assert cuerpo.index(f"'error', '{error}'") < actualiza, error
    assert "v_campo IN ('id', 'created_at', 'pais')" in cuerpo


def test_cada_error_del_sql_tiene_su_mensaje():
    errores = set(re.findall(r"'error', '([a-z_]+)'", SQL))
    assert errores <= set(C.MENSAJES), errores - set(C.MENSAJES)


# ── Lo que se lee del formulario de cada país ───────────────────────────────

@pytest.mark.parametrize('pais', PAISES)
def test_los_campos_salen_del_formulario(pais):
    campos = C.campos_del_formulario(pais)
    assert 'pais' not in campos
    for c in C.IDENTIFICACION + ['alcohol_s1', 'hurto', 'salud_fisica', 'calidad_vida']:
        assert c in campos, f'{pais}: falta {c}'


def test_cada_pais_corrige_sus_propias_sustancias():
    assert 'heroina_s1' in C.campos_del_formulario('Ecuador')
    assert 'crack_s1' in C.campos_del_formulario('El Salvador')
    assert 'pastabase_s1' not in C.campos_del_formulario('El Salvador')
    assert 'metanfetamina_s1' in C.campos_del_formulario('México CIJ')


@pytest.mark.parametrize('pais', PAISES)
def test_las_listas_salen_del_formulario(pais):
    assert C.opciones_del_formulario(pais, 'etapa') == ['ingreso', 'en_tratamiento', 'egreso', 'seguimiento']
    assert C.opciones_del_formulario(pais, 'sexo') == ['H', 'M', 'O']
    assert C.opciones_del_formulario(pais, 'centro'), f'{pais}: sin lista de centros'
    assert 'Alcohol' in C.opciones_del_formulario(pais, 'sustancia_principal')


def test_la_lista_de_centros_es_la_misma_del_modulo_de_claves():
    pytest.importorskip('streamlit')
    from pipeline.panel.gestion_claves import codigos_del_formulario
    for pais in ['Perú', 'Ecuador', 'El Salvador', 'México', 'México CIJ']:
        assert C.opciones_del_formulario(pais, 'centro') == codigos_del_formulario(pais), pais


# ── Reglas de validación ────────────────────────────────────────────────────

OPC = {'etapa': ['ingreso', 'en_tratamiento', 'egreso', 'seguimiento'], 'sexo': ['H', 'M', 'O'],
       'centro': ['TLP9480', 'TLT9330'], 'sustancia_principal': ['Alcohol', 'Otra']}
CAMPOS = C.campos_del_formulario('México CIJ')
REGISTRO = {'id': 2442, 'pais': 'México CIJ', 'centro': 'TLP9480', 'etapa': 'egreso',
            'codigo_paciente': 'JORO11051984', 'fecha_nacimiento': '1984-05-11',
            'fecha_entrevista': '2026-10-16', 'sexo': 'H', 'nombre_entrevistador': 'X',
            'sustancia_principal': 'Alcohol', 'alcohol_s1': 2, 'alcohol_s2': None,
            'alcohol_s3': None, 'alcohol_s4': None, 'alcohol_total': 2, 'hurto': 'false',
            'trabajo_na': False}


@pytest.mark.parametrize('campo, texto, valor', [
    ('alcohol_s1', '7', 7), ('alcohol_prom', '2,5', 2.5), ('alcohol_prom', '0', 0),
    ('salud_fisica', '20', 20), ('hurto', 'sí', 'S'), ('hurto', 'n', 'N'),
    ('trabajo_na', 'Sí', True), ('fecha_entrevista', '16/10/2026', '2026-10-16'),
    ('codigo_paciente', 'joro11051984', 'JORO11051984'), ('etapa', 'INGRESO', 'ingreso'),
    ('hurto', 'vacío', None),
])
def test_normaliza_lo_escrito(campo, texto, valor):
    assert C.normalizar(campo, texto, OPC) == (valor, None)


@pytest.mark.parametrize('campo, texto', [
    ('alcohol_s1', '8'), ('alcohol_s1', '-1'), ('alcohol_prom', '-0.5'), ('salud_fisica', '21'),
    ('hurto', 'tal vez'), ('fecha_entrevista', '30-02-2026'), ('codigo_paciente', 'JOR11051984'),
    ('etapa', 'seguimiento1'), ('centro', 'XXX'), ('etapa', 'vacío'),
])
def test_rechaza_lo_que_el_formulario_no_acepta(campo, texto):
    valor, error = C.normalizar(campo, texto, OPC)
    assert error, (campo, texto)


def test_corregir_la_etapa_es_un_solo_cambio():
    cambios, errores = C.construir_cambios(REGISTRO, {'etapa': 'ingreso'}, OPC, CAMPOS, hoy=HOY)
    assert (cambios, errores) == ({'etapa': 'ingreso'}, [])


def test_el_total_de_semanas_se_recalcula_solo():
    cambios, errores = C.construir_cambios(REGISTRO, {'alcohol_s2': '3'}, OPC, CAMPOS, hoy=HOY)
    assert errores == []
    assert cambios == {'alcohol_s2': 3, 'alcohol_total': 5}


def test_el_total_no_se_escribe_a_mano():
    cambios, _ = C.construir_cambios(REGISTRO, {'alcohol_total': '9'}, OPC, CAMPOS, hoy=HOY)
    assert cambios == {}


def test_escribir_lo_mismo_no_es_un_cambio():
    """'false' guardado por la migración y 'N' escrito son el mismo dato."""
    cambios, errores = C.construir_cambios(REGISTRO, {'hurto': 'N', 'alcohol_s1': '2', 'sexo': 'h'},
                                           OPC, CAMPOS, hoy=HOY)
    assert (cambios, errores) == ({}, [])


def test_el_codigo_tiene_que_coincidir_con_la_fecha_de_nacimiento():
    _, errores = C.construir_cambios(REGISTRO, {'fecha_nacimiento': '1984-05-12'}, OPC, CAMPOS, hoy=HOY)
    assert any('código' in e for _, e in errores)
    cambios, errores = C.construir_cambios(
        REGISTRO, {'fecha_nacimiento': '1984-05-12', 'codigo_paciente': 'JORO12051984'}, OPC, CAMPOS, hoy=HOY)
    assert errores == [] and set(cambios) == {'fecha_nacimiento', 'codigo_paciente'}


@pytest.mark.parametrize('texto', ['2026-11-05', '2019-12-31'])
def test_la_fecha_de_entrevista_no_puede_ser_futura_ni_anterior_a_2020(texto):
    _, errores = C.construir_cambios(REGISTRO, {'fecha_entrevista': texto}, OPC, CAMPOS, hoy=HOY)
    assert errores


def test_la_edad_va_de_5_a_100_anios():
    for fn, cod in [('2023-01-01', 'JORO01012023'), ('1920-01-01', 'JORO01011920')]:
        _, errores = C.construir_cambios(REGISTRO, {'fecha_nacimiento': fn, 'codigo_paciente': cod},
                                         OPC, CAMPOS, hoy=HOY)
        assert any('edad' in e for _, e in errores), fn


# ── La función en un Postgres de verdad ─────────────────────────────────────

@pytest.fixture(scope='module')
def pg(tmp_path_factory):
    pgserver = pytest.importorskip('pgserver')
    srv = pgserver.get_server(str(tmp_path_factory.mktemp('pg')), cleanup_mode='stop')
    srv.psql("""
        CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN; CREATE ROLE service_role NOLOGIN;
        CREATE TABLE public.top_registros (id bigserial primary key, created_at timestamptz default now(),
          pais text not null, centro text not null, codigo_paciente text not null, fecha_entrevista date,
          etapa text not null, alcohol_s2 smallint, alcohol_total smallint, hurto text, trabajo_na boolean);
        INSERT INTO top_registros (pais, centro, codigo_paciente, fecha_entrevista, etapa, alcohol_total, hurto)
        VALUES ('México CIJ','TLP9480','JORO11051984','2026-10-16','egreso',2,'N'),
               ('Perú','EESS02SB','BBBB01011990','2026-09-01','ingreso',null,'S');
    """)
    srv.psql(SQL)
    return srv.psql


def test_corrige_y_anota_cada_campo(pg):
    out = pg("SELECT corregir_registro(1, 'México CIJ', '{\"etapa\":\"ingreso\",\"alcohol_s2\":3,"
             "\"alcohol_total\":5}', 'confirmado por el centro', 'gobierno:México CIJ');")
    assert '"ok": true' in out and '"cambios": 3' in out
    assert 'ingreso | 3 | 5' in re.sub(r'\s+\|\s+', ' | ', pg("SELECT etapa, alcohol_s2, alcohol_total FROM top_registros WHERE id=1;"))
    bitacora = pg("SELECT campo, valor_anterior, valor_nuevo FROM top_correcciones WHERE registro_id=1 ORDER BY campo;")
    assert 'egreso' in bitacora and 'alcohol_total' in bitacora
    assert '1' in pg("SELECT count(*) FROM top_registros_auditoria WHERE registro_id=1 AND operacion='UPDATE';")


@pytest.mark.parametrize('llamada, error', [
    ("2, 'México CIJ', '{\"etapa\":\"egreso\"}', 'x', 'y'", 'otro_pais'),
    ("1, 'México CIJ', '{\"etapa\":\"egreso\"}', ' ', 'y'", 'motivo'),
    ("1, 'México CIJ', '{\"pais\":\"Perú\"}', 'x', 'y'", 'campo'),
    ("1, 'México CIJ', '{\"etapa\":\"egreso\",\"no_existe\":1}', 'x', 'y'", 'campo'),
    ("1, 'México CIJ', '{}', 'x', 'y'", 'sin_cambios'),
    ("99, 'México CIJ', '{\"etapa\":\"egreso\"}', 'x', 'y'", 'no_existe'),
])
def test_rechaza_sin_tocar_nada(pg, llamada, error):
    antes = pg("SELECT to_jsonb(t) FROM top_registros t ORDER BY id;")
    assert f'"error": "{error}"' in pg(f"SELECT corregir_registro({llamada});")
    assert pg("SELECT to_jsonb(t) FROM top_registros t ORDER BY id;") == antes


def test_la_llave_publica_no_puede_corregir(pg):
    out = pg("SELECT has_function_privilege('anon', 'public.corregir_registro(bigint,text,jsonb,text,text)', "
             "'EXECUTE'), has_function_privilege('service_role', "
             "'public.corregir_registro(bigint,text,jsonb,text,text)', 'EXECUTE');")
    assert re.search(r'\bf\s*\|\s*t\b', out)


def test_un_borrado_tambien_queda_en_la_auditoria(pg):
    pg("DELETE FROM top_registros WHERE id = 2;")
    assert 'Perú' in pg("SELECT antes->>'pais' FROM top_registros_auditoria WHERE operacion='DELETE';")


# ── La pestaña, con una base simulada ───────────────────────────────────────

def _app_correccion():
    import sys
    sys.path.insert(0, RAIZ_APP)
    import streamlit as st
    from pipeline.panel.correccion import render
    from tests.test_correccion import REGISTRO

    class APIFalsa:
        def buscar(self, pais, codigo=None, ident=None):
            return [dict(REGISTRO)]

        def historial(self, ident):
            return [{'fecha': '2026-11-01T10:00:00', 'campo': 'etapa', 'valor_anterior': 'egreso',
                     'valor_nuevo': 'ingreso', 'motivo': 'prueba', 'realizado_por': 'UNODC'}]

        def corregir(self, payload):
            return {'ok': True, 'cambios': len(payload['p_cambios'])}

    st.session_state.setdefault('corr_México CIJ_res', [dict(REGISTRO)])
    render('México CIJ', etiquetas={'etapa': 'Etapa'}, realizado_por='UNODC', api=APIFalsa())


def test_la_pestania_muestra_el_registro_y_su_historial():
    pytest.importorskip('streamlit')
    from streamlit.testing.v1 import AppTest
    import inspect
    src = 'RAIZ_APP = ' + repr(RAIZ) + '\n'
    src += inspect.getsource(_app_correccion).replace('def _app_correccion():', 'def _app():') + '\n_app()\n'
    at = AppTest.from_string(src, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    assert at.selectbox and 'N.º 2442' in at.selectbox[0].options[0]
    assert any('Correcciones anteriores' in e.label for e in at.expander)
