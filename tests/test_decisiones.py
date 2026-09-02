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
    categorias_pais, clasificar_sustancia, columna_de_sustancia,
    construir_episodios, detectar_pais, es_etapa_ingreso, es_flag_activo,
    lineas_base, normalizar_sexo_valor,
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


@pytest.mark.parametrize('texto', [
    'ninguna', 'niega', 'ludopatia', '', '0', None,
    'N', 'no', 'nan', '-', 'x', 's/d', 'minguna',
])
def test_lo_que_no_es_sustancia_no_va_a_otra_sino_a_nulo(texto):
    """Ausencia de dato es None, y queda fuera del denominador. No es 'Otra'."""
    assert clasificar_sustancia(texto, 'Perú') is None


@pytest.mark.parametrize('texto', ['Nicotina', 'Sedantes', 'Naranja rara'])
def test_el_filtro_de_vacios_no_se_come_sustancias_reales(texto):
    """'n' y 'no' se comparan exactos: como subcadena estarían en todo."""
    assert clasificar_sustancia(texto, 'Perú') is not None


@pytest.mark.parametrize('texto,pais,esperado', [
    ('Tusi',                          'Perú',        OTRA_SUSTANCIA),
    ('Tabaco',                        'Perú',        OTRA_SUSTANCIA),
    ('Ketamina',                      'Perú',        OTRA_SUSTANCIA),
    ('Inhalantes',                    'Perú',        OTRA_SUSTANCIA),
    ('Crack',                          'Perú',       OTRA_SUSTANCIA),
    ('Metanfetamina',                 'El Salvador', OTRA_SUSTANCIA),
    ('Otra',                          'Perú',        OTRA_SUSTANCIA),
    ('Otras',                         'El Salvador', OTRA_SUSTANCIA),
    ('marihuana',                     'El Salvador', 'Marihuana'),
    ('Sedantes',                      'Ecuador',     'Sedantes'),
    ('LAS DOS, ALCOHOL Y LA COCAINA', 'Perú',        'Alcohol'),
])
def test_valores_reales_que_hay_hoy_en_la_base(texto, pais, esperado):
    """Los 94 registros con sustancia fuera de la lista de su país, al 2026-09-02."""
    assert clasificar_sustancia(texto, pais) == esperado


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


# ── La línea base es el TOP con etapa de ingreso, y solo ese ────────────────

@pytest.fixture
def registros():
    """Los cinco casos que definen la regla, con un reingreso y dos sin ingreso."""
    return pd.DataFrame([
        ('A', 'C1', '2026-01-10', 'ingreso'),
        ('A', 'C1', '2026-04-10', 'seguimiento'),
        ('A', 'C1', '2026-08-10', 'ingreso'),
        ('A', 'C1', '2026-09-01', 'en_tratamiento'),
        ('B', 'C1', '2026-05-14', 'en_tratamiento'),
        ('C', 'C1', '2026-03-01', 'ingreso'),
        ('C', 'C2', '2026-07-01', 'ingreso'),
        ('D', 'C1', '2026-02-01', 'en_tratamiento'),
        ('D', 'C1', '2026-06-01', 'ingreso'),
    ], columns=['codigo_paciente', 'centro', 'fecha_entrevista', 'etapa'])


def test_un_top_de_ingreso_abre_un_episodio(registros):
    ep = construir_episodios(registros)['_episodio']
    assert ep.iloc[0] == 'A|C1|2026-01-10'


def test_los_top_siguientes_pertenecen_al_mismo_episodio(registros):
    ep = construir_episodios(registros)['_episodio']
    assert ep.iloc[1] == ep.iloc[0]


def test_un_reingreso_abre_un_episodio_nuevo(registros):
    ep = construir_episodios(registros)['_episodio']
    assert ep.iloc[2] == 'A|C1|2026-08-10' != ep.iloc[0]


def test_sin_top_de_ingreso_no_hay_episodio(registros):
    """Son 182 pacientes al 2026-09-02. Quedan fuera de la caracterización."""
    ep = construir_episodios(registros)['_episodio']
    assert pd.isna(ep.iloc[4])


def test_lo_anterior_al_ingreso_queda_fuera(registros):
    """Un TOP de en_tratamiento previo no describe cómo llegó la persona."""
    ep = construir_episodios(registros)['_episodio']
    assert pd.isna(ep.iloc[7])


def test_el_mismo_paciente_en_dos_centros_son_dos_episodios(registros):
    ep = construir_episodios(registros)['_episodio']
    assert ep.iloc[5] != ep.iloc[6]


def test_lineas_base_devuelve_una_fila_por_episodio(registros):
    lb = lineas_base(registros)
    assert len(lb) == 5
    assert (lb['etapa'] == 'ingreso').all()


def test_lineas_base_sin_columnas_no_revienta():
    assert lineas_base(pd.DataFrame({'algo': [1, 2]})).empty


@pytest.mark.parametrize('valor,esperado', [
    ('ingreso', True), ('Ingreso', True), ('  INGRESO  ', True),
    ('en_tratamiento', False), ('seguimiento', False), ('', False),
])
def test_la_etapa_de_ingreso_tolera_mayusculas_y_espacios(valor, esperado):
    assert es_etapa_ingreso(valor) is esperado


def test_el_panel_no_filtra_la_etapa_a_mano():
    """Los módulos de caracterización usan lineas_base(), no su propio filtro."""
    import glob
    culpables = []
    for ruta in glob.glob(os.path.join(RAIZ, 'pipeline', 'panel', '*.py')):
        nombre = os.path.basename(ruta)[:-3]
        if nombre not in ('edad', 'piramide', 'salud', 'transgresion',
                          'dias_consumo', 'sustancia'):
            continue
        with open(ruta, encoding='utf-8') as fh:
            src = fh.read()
        if "str.strip() == 'ingreso'" in src:
            culpables.append(nombre)
    assert not culpables, 'filtran la etapa a mano: ' + ', '.join(culpables)


# ── Todos los gráficos muestran todas las categorías del país ──────────────

REPORTES = ['caract_excel', 'seg_excel', 'word_caract', 'word_seg',
            'pptx_caract', 'pptx_seg']


def test_ningun_reporte_se_salta_las_categorias_vacias():
    """Antes hacían `if n > 0: agregar`, y la sustancia desaparecía del gráfico."""
    patrones = ['if len(sub): dias', 'if len(sub)>=1: dias',
                'if n_c > 0: consumo', 'if n_c>0: consumo']
    culpables = []
    for m in REPORTES:
        src = _fuente(m)
        if any(p in src for p in patrones):
            culpables.append(m)
    assert not culpables, 'se saltan categorías vacías: ' + ', '.join(culpables)


def test_la_columna_de_dias_se_encuentra_en_los_dos_formatos():
    """Supabase las llama `alcohol_total`; el Base Wide, `alcohol_total_TOP1`."""
    cortas = ['alcohol_total', 'pastabase_total', 'otra_sust_total']
    largas = ['alcohol_total_TOP1', 'pastabase_total_TOP1', 'otra_sust_total_TOP1']
    for cols in (cortas, largas):
        assert columna_de_sustancia('Alcohol', cols) is not None
        assert columna_de_sustancia('Pasta Base', cols) is not None
        assert columna_de_sustancia(OTRA_SUSTANCIA, cols) is not None


def test_una_sustancia_que_el_pais_no_mide_no_tiene_columna():
    """Crack en Perú o heroína en México: la categoría existe, la columna no."""
    cols = ['alcohol_total', 'marihuana_total', 'cocaina_total']
    assert columna_de_sustancia('Heroína', cols) is None
    assert columna_de_sustancia('Crack', cols) is None


def test_la_deduplicacion_del_wide_conserva_el_top_de_ingreso():
    """Un paciente con sus tres registros sin fecha perdía su ingreso, y su
    episodio desaparecía de los reportes pero no del panel."""
    with open(os.path.join(RAIZ, 'pipeline', 'wide_top.py'), encoding='utf-8') as fh:
        src = fh.read()
    assert 'drop_duplicates(subset=[COL_CODIGO, COL_FECHA]' not in src
    assert '_clave_dedup' in src


# ── El sexo tiene tres categorías, y "Otro" es una respuesta ───────────────

def test_ningun_modulo_excluye_otro_del_n_valido():
    """`isin(['H','M'])` dejaba fuera del informe a quien declaró otro sexo,
    mientras el panel sí lo contaba. Son 2 personas al 2026-09-02."""
    culpables = []
    for m in REPORTES:
        src = _fuente(m)
        for linea in src.splitlines():
            if "isin(['H','M'])" in linea.replace(' ', '') and not linea.strip().startswith('#'):
                culpables.append(m)
                break
    assert not culpables, 'excluyen Otro del N válido: ' + ', '.join(culpables)


def test_los_rangos_de_edad_no_se_calculan_a_mano():
    """El panel usaba int(edad) y los reportes pd.cut con bins distintos."""
    culpables = [m for m in REPORTES if 'bins=[0,17,30' in _fuente(m).replace(' ', '')]
    assert not culpables, 'calculan rangos de edad a mano: ' + ', '.join(culpables)


@pytest.mark.parametrize('edad,esperado', [
    (17, 'Menos de 18'), (17.5, 'Menos de 18'), (17.99, 'Menos de 18'),
    (18, '18 a 30'), (30.9, '18 a 30'), (31, '31 a 40'),
    (60, '51 a 60'), (61, '61 o más'), (None, None),
])
def test_el_rango_etario_cuenta_anios_cumplidos(edad, esperado):
    """Quien tiene 17 años y medio no está en el rango de 18 a 30."""
    from pipeline.validacion_top import rango_etario
    assert rango_etario(edad) == esperado
