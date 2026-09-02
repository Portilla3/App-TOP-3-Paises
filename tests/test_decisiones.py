# -*- coding: utf-8 -*-
"""
Cada prueba de este archivo corresponde a una entrada de DECISIONES.md.

No prueban que el código funcione: prueban que el código sigue obedeciendo una
decisión ya tomada. Si una falla, o alguien rompió la regla sin darse cuenta, o
la decisión cambió y falta su entrada nueva en DECISIONES.md.

Correr con:  python -m pytest tests/test_decisiones.py -v
"""
import os
import re
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.validacion_top import (  # noqa: E402
    CATEGORIAS_POR_PAIS, OTRA_SUSTANCIA, SUSTANCIA_A_COLUMNA,
    categorias_pais, clasificar_sustancia, detectar_pais, es_flag_activo,
    normalizar_sexo_valor,
)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULOS_VIVOS = ['caract_excel', 'seg_excel', 'word_caract', 'word_seg',
                 'pptx_caract', 'pptx_seg']


def _fuente(modulo):
    ruta = os.path.join(RAIZ, 'pipeline', modulo + '.py')
    with open(ruta, encoding='utf-8') as fh:
        return fh.read()


# ── El campo sexo usa H/M/O en los cuatro países ────────────────────────────

@pytest.mark.parametrize('valor,esperado', [
    ('H', 'H'), ('h', 'H'), ('Hombre', 'H'), ('M', 'M'), ('Mujer', 'M'),
    ('O', 'O'), ('Otro', 'O'), ('', None), (None, None),
])
def test_sexo_convencion_unica(valor, esperado):
    assert normalizar_sexo_valor(valor) == esperado


def test_sexo_no_se_reimplementa_en_los_modulos():
    """La normalización del sexo vive solo en validacion_top.py."""
    for m in MODULOS_VIVOS:
        src = _fuente(m)
        assert "== 'M'" not in src.replace(' ', ''), (
            f'{m}.py compara el sexo a mano en vez de usar normalizar_sexo()'
        )


# ── La sustancia fuera de la lista del país va a Otra sustancia ─────────────

@pytest.mark.parametrize('texto,pais,esperado', [
    ('heroina',      'Ecuador',     'Heroína'),
    ('heroina',      'México',      OTRA_SUSTANCIA),
    ('crack',        'El Salvador', 'Crack'),
    ('crack',        'Perú',        OTRA_SUSTANCIA),
    ('tusi',         'Perú',        OTRA_SUSTANCIA),
    ('cristal',      'México',      'Metanfetamina'),
    ('cristal',      'Perú',        OTRA_SUSTANCIA),
    ('pasta basica', 'Perú',        'Pasta Base'),
    ('Marihuana',    'Perú',        'Marihuana'),
])
def test_sustancia_fuera_de_lista_va_a_otra(texto, pais, esperado):
    assert clasificar_sustancia(texto, pais) == esperado


@pytest.mark.parametrize('texto', ['ninguna', 'niega', 'ludopatia', '', '0', None])
def test_lo_que_no_es_sustancia_no_va_a_otra_sino_a_nulo(texto):
    """Ausencia de dato es None, y queda fuera del denominador. No es 'Otra'."""
    assert clasificar_sustancia(texto, 'Perú') is None


def test_toda_categoria_de_todo_pais_tiene_columna_de_dias():
    """Una categoría sin columna dibujaría una barra vacía o un cero falso."""
    for pais, cats in CATEGORIAS_POR_PAIS.items():
        for cat in cats:
            assert cat in SUSTANCIA_A_COLUMNA, f'{cat} ({pais}) no tiene columna'


def test_otra_sustancia_es_siempre_la_ultima_categoria():
    for pais, cats in CATEGORIAS_POR_PAIS.items():
        assert cats[-1] == OTRA_SUSTANCIA, f'{pais} no cierra con Otra sustancia'


def test_cada_pais_tiene_seis_categorias_menos_ecuador_que_tiene_siete():
    for pais, cats in CATEGORIAS_POR_PAIS.items():
        esperado = 7 if pais == 'Ecuador' else 6
        assert len(cats) == esperado, f'{pais} tiene {len(cats)}, se esperaban {esperado}'


def test_las_categorias_del_pais_no_dependen_del_dato():
    """Se dibujan siempre todas, aunque el centro no tenga ningún caso."""
    assert categorias_pais('Perú') == CATEGORIAS_POR_PAIS['Perú']
    assert len(categorias_pais('Ecuador')) == 7


# ── validacion_top.py es la única fuente de criterios ───────────────────────

@pytest.mark.xfail(strict=True, reason=(
    'Deuda conocida al 2026-09-02: clasificar_sustancia() ya existe en '
    'validacion_top.py pero los seis módulos siguen con su copia. El reemplazo '
    'mueve números en reportes ya entregados y espera la comparación panel '
    'contra Wide. Cuando se pague, esta prueba pasa y strict=True obliga a '
    'quitar el xfail.'))
def test_el_clasificador_de_sustancias_no_esta_duplicado():
    """Diez copias con tres vocabularios distintos dejaban fuera al 12 %."""
    culpables = [m for m in MODULOS_VIVOS
                 if re.search(r"\[.*'heroina'.*\].*return", _fuente(m))]
    assert not culpables, (
        'estos módulos reimplementan el clasificador: ' + ', '.join(culpables)
    )


def test_el_criterio_de_flags_no_esta_duplicado():
    for m in MODULOS_VIVOS:
        assert "isin(['true','1','t'])" not in _fuente(m).replace(' ', ''), (
            f'{m}.py reimplementa el criterio de flag en vez de usar es_flag_activo()'
        )


@pytest.mark.parametrize('valor,esperado', [
    (True, True), (False, False), (1.0, True), (0.0, False),
    ('true', True), ('1', True), ('1.0', True), ('SI', True),
    (None, False), ('', False), ('false', False),
])
def test_flag_activo_reconoce_los_dos_formatos(valor, esperado):
    """TOP1 escribe True/False y TOP2 escribe 1.0/0.0."""
    assert bool(es_flag_activo(pd.Series([valor])).iloc[0]) is esperado


# ── En sustancia principal entran todos; en cualquier sustancia solo los que consumen ──

def test_no_quedan_rellenos_con_cero_antes_de_contar_consumidores():
    """fillna(0) antes de un (v>0) es inocuo, pero sugiere un bug que no existe."""
    for m in MODULOS_VIVOS:
        src = _fuente(m)
        assert not re.search(r"fillna\(0\)[^\n]*\n[^\n]*>\s*0", src), (
            f'{m}.py rellena con cero antes de contar consumidores'
        )


def test_no_quedan_series_de_ceros_para_columnas_ausentes():
    """Una columna que falta no es una columna de ceros."""
    for m in MODULOS_VIVOS:
        assert 'Series([0]*' not in _fuente(m).replace(' ', ''), (
            f'{m}.py inventa una serie de ceros cuando falta una columna'
        )


# ── No se renombran las claves del runner ──────────────────────────────────

def test_las_claves_pdf_siguen_apuntando_a_los_word():
    with open(os.path.join(RAIZ, 'pipeline', 'runner.py'), encoding='utf-8') as fh:
        src = fh.read()
    assert "'pdf_caract':   'word_caract.py'" in src
    assert "'pdf_seg':      'word_seg.py'" in src


def test_los_modulos_pdf_siguen_borrados():
    """Contenían dos copias del clasificador y recibieron arreglos sin efecto."""
    for m in ['pdf_caract', 'pdf_seg']:
        ruta = os.path.join(RAIZ, 'pipeline', m + '.py')
        assert not os.path.exists(ruta), f'{m}.py volvió a aparecer'


# ── El país se deduce de los datos, no del nombre del archivo ──────────────

def test_pais_se_lee_de_la_columna_cuando_existe():
    """La tabla de Supabase la llama `pais` y el Base Wide `pais_TOP1`."""
    assert detectar_pais(pd.DataFrame({'pais': ['Ecuador'] * 3})) == 'Ecuador'
    assert detectar_pais(pd.DataFrame({'pais_TOP1': ['El Salvador'] * 3})) == 'El Salvador'


def test_pais_no_se_deduce_de_columnas_vacias():
    """El Wide genera columnas para todas las sustancias, llenas o no."""
    df = pd.DataFrame({'heroina_total': [None, None], 'crack_total': [3, 5]})
    assert detectar_pais(df) == 'El Salvador'


def test_pais_desconocido_devuelve_none():
    assert detectar_pais(pd.DataFrame({'algo': [1, 2]})) is None


def test_sin_pais_no_se_filtra_de_mas():
    """Sin país conocido, la categoría canónica se devuelve sin recortar."""
    assert clasificar_sustancia('heroina', None) == 'Heroína'
