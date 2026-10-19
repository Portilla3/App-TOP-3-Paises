# -*- coding: utf-8 -*-
"""
Pruebas de la función de login de centro.

La función vive en Supabase, no en Python, así que estas pruebas no pueden
ejecutarla: verifican que el archivo versionado en `sql/` siga conteniendo las
decisiones tomadas. Es una red menos fina que una prueba de comportamiento, pero
cubre el caso real: que alguien cambie la función en producción y el repositorio
quede diciendo otra cosa, o al revés.

La verificación de comportamiento se hace contra la base, con el conector de
Supabase, y queda registrada en INCIDENTES.md con sus resultados.
"""
import os
import re

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA = os.path.join(RAIZ, 'sql', 'validar_login_centro.sql')


@pytest.fixture(scope='module')
def fuente():
    assert os.path.exists(RUTA), (
        'La función de login no está versionada. Su única copia sería la de '
        'producción, y un cambio se perdería sin dejar rastro.'
    )
    with open(RUTA, encoding='utf-8') as fh:
        return fh.read()


def test_el_codigo_de_centro_no_distingue_mayusculas(fuente):
    """Decidido el 2026-10-18: llegaban intentos con `csp`, `Csp` y `sja`."""
    assert re.search(r'v_entrada\s*:=\s*upper\(trim\(', fuente), \
        'la entrada del usuario ya no se normaliza'
    assert re.search(r'upper\(trim\(cc\.centro\)\)\s*=\s*v_entrada', fuente), \
        'la columna ya no se normaliza, así que la comparación vuelve a ser exacta'


def test_la_clave_sigue_distinguiendo_mayusculas(fuente):
    """bcrypt compara exacto. Normalizar la clave debilitaría el login."""
    assert re.search(r'crypt\(p_password,\s*cc\.password_hash\)', fuente)
    assert not re.search(r'(upper|lower)\s*\(\s*p_password', fuente), \
        'la clave se está normalizando: eso reduce el espacio de contraseñas'


def test_la_funcion_conserva_sus_defensas(fuente):
    """SECURITY DEFINER sin search_path fijo es escalable por el llamador."""
    assert 'SECURITY DEFINER' in fuente
    assert re.search(r"SET\s+search_path\s+TO\s+'public',\s*'extensions'", fuente)
    assert 'cc.activo' in fuente, 'dejó de filtrar por credencial activa'


def test_la_bitacora_guarda_lo_que_la_persona_escribio(fuente):
    """Esa columna es la que permitió medir por qué fallan los logins: 15 de 31
    intentos eran texto pegado desde WhatsApp, no códigos mal escritos."""
    assert re.search(r"left\(coalesce\(p_correo", fuente)
    assert "'login_fallido'" in fuente
