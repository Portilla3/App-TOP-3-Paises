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


def test_un_centro_sin_top_de_ingreso_no_revienta_el_pipeline():
    """Tres centros no tienen ningún TOP de ingreso. Sin la guarda, pd.DataFrame([])
    sale sin columnas y procesar_wide falla con KeyError en la clave del episodio."""
    with open(os.path.join(RAIZ, 'pipeline', 'wide_top.py'), encoding='utf-8') as fh:
        src = fh.read()
    assert 'if not top1_rows:' in src
    assert 'df_top1 = pd.DataFrame(columns=list(df_wide.columns))' in src


# ── Duplicados: vale la última carga ───────────────────────────────────────

def _dup(**extra):
    base = dict(pais='El Salvador', centro='CMM', codigo_paciente='AAAA01011990',
                fecha_entrevista='2026-04-07', etapa='ingreso')
    base.update(extra)
    return base


def test_de_dos_copias_se_conserva_la_cargada_despues():
    """Los duplicados reales son TOP vueltos a cargar para corregirlos."""
    from pipeline.validacion_top import quedarse_con_ultima_version
    df = pd.DataFrame([
        _dup(id=10, created_at='2026-07-10 10:00:00+00', alcohol_total=5),
        _dup(id=25, created_at='2026-07-24 15:00:00+00', alcohol_total=20),
    ])
    r = quedarse_con_ultima_version(df, ['codigo_paciente', 'centro', 'fecha_entrevista', 'etapa'])
    assert len(r) == 1 and r.iloc[0]['alcohol_total'] == 20


def test_manda_la_fecha_de_carga_aunque_el_id_diga_otra_cosa():
    from pipeline.validacion_top import quedarse_con_ultima_version
    df = pd.DataFrame([
        _dup(id=99, created_at='2026-06-01 10:00:00+00', alcohol_total=5),
        _dup(id=12, created_at='2026-08-01 10:00:00+00', alcohol_total=20),
    ])
    r = quedarse_con_ultima_version(df, ['codigo_paciente', 'etapa'])
    assert r.iloc[0]['alcohol_total'] == 20


def test_sin_fecha_de_carga_desempata_el_id():
    from pipeline.validacion_top import quedarse_con_ultima_version
    df = pd.DataFrame([_dup(id=30, alcohol_total=20), _dup(id=10, alcohol_total=5)])
    r = quedarse_con_ultima_version(df, ['codigo_paciente', 'etapa'])
    assert r.iloc[0]['alcohol_total'] == 20


def test_sin_fecha_de_carga_ni_id_se_conserva_la_primera():
    """Sin información de cuándo se cargó, no hay base para elegir otra."""
    from pipeline.validacion_top import quedarse_con_ultima_version
    df = pd.DataFrame([_dup(alcohol_total=5), _dup(alcohol_total=20)])
    r = quedarse_con_ultima_version(df, ['codigo_paciente', 'etapa'])
    assert r.iloc[0]['alcohol_total'] == 5


def test_el_orden_de_las_filas_no_cambia():
    from pipeline.validacion_top import quedarse_con_ultima_version
    df = pd.DataFrame([
        _dup(id=1, codigo_paciente='Z', created_at='2026-01-01'),
        _dup(id=2, codigo_paciente='A', created_at='2026-01-02'),
        _dup(id=3, codigo_paciente='M', created_at='2026-01-03'),
    ])
    r = quedarse_con_ultima_version(df, ['codigo_paciente'])
    assert list(r['codigo_paciente']) == ['Z', 'A', 'M']


def test_lineas_base_usa_la_ultima_carga_del_ingreso():
    df = pd.DataFrame([
        _dup(id=10, created_at='2026-07-10', sexo='H'),
        _dup(id=25, created_at='2026-07-24', sexo='M'),
    ])
    lb = lineas_base(df)
    assert len(lb) == 1 and lb.iloc[0]['sexo'] == 'M'


def test_el_wide_deduplica_con_la_funcion_compartida():
    with open(os.path.join(RAIZ, 'pipeline', 'wide_top.py'), encoding='utf-8') as fh:
        src = fh.read()
    assert 'quedarse_con_ultima_version(df, _clave_dedup)' in src
    assert "drop_duplicates(subset=_clave_dedup, keep='first')" not in src


# ── Hay dos indicadores de seguimiento y un solo TOP2 (2026-09-10) ──────────

@pytest.fixture
def seguimientos():
    """Un TOP2 con etiqueta de ingreso, uno sin etiqueta de seguimiento, un
    duplicado del mismo día y pacientes de 30, 70 y 120 días sin TOP2."""
    return pd.DataFrame([
        ('A', 'C1', '2026-05-01', 'ingreso'),
        ('A', 'C1', '2026-08-01', 'en_tratamiento'),
        ('B', 'C1', '2026-05-01', 'ingreso'),
        ('B', 'C1', '2026-06-15', 'ingreso'),
        ('C', 'C1', '2026-05-01', 'ingreso'),
        ('C', 'C1', '2026-05-01', 'en_tratamiento'),
        ('D', 'C2', '2026-06-29', 'ingreso'),
        ('E', 'C2', '2026-08-18', 'en_tratamiento'),
        ('F', 'C2', '2026-09-27', 'ingreso'),
    ], columns=['codigo_paciente', 'centro', 'fecha_entrevista', 'etapa'])


HOY = '2026-10-27'


def test_el_top2_se_identifica_por_fecha_y_no_por_etiqueta(seguimientos):
    from pipeline.panel.seguimiento_core import top2_por_paciente
    per = top2_por_paciente(seguimientos, hoy=HOY).set_index('codigo')
    assert per.loc['A', 'tiene_top2'] and per.loc['B', 'tiene_top2']
    assert not per.loc['C', 'tiene_top2'], 'dos TOP el mismo día son uno solo'


def test_los_modulos_de_seguimiento_no_buscan_el_top2_por_su_cuenta():
    """Semáforo, tiempo entre TOP y continuidad llaman al core."""
    culpables = []
    for nombre, fuente in [('semaforo_seguimiento', 'top2_por_paciente'),
                           ('tiempo_top', 'top2_por_paciente'),
                           ('config', 'calcular_seguimiento')]:
        with open(os.path.join(RAIZ, 'pipeline', 'panel', nombre + '.py'), encoding='utf-8') as fh:
            src = fh.read()
        if 'ETAPAS_TOP2' in src or 'ETAPAS_SEGUNDA' in src or fuente not in src:
            culpables.append(nombre)
    assert not culpables, 'reimplementan el TOP2: ' + ', '.join(culpables)


def test_los_dos_indicadores_solo_difieren_en_el_denominador(seguimientos):
    pytest.importorskip('streamlit')
    from pipeline.panel.config import continuidad_por_centro
    from pipeline.panel.seguimiento_core import calcular_seguimiento
    aplic = continuidad_por_centro(seguimientos, hoy=HOY)
    cob = calcular_seguimiento(seguimientos, hoy=HOY)
    assert aplic['n_pacientes'].sum() == 6          # todos los pacientes
    assert aplic['n_con_top2'].sum() == 2            # A y B
    assert cob['n_elegibles'] == 4 and cob['n_con_top2'] == 2   # 90+ días: A, B, C, D


def test_el_semaforo_cuadra_con_la_tarjeta_con_seguimiento(seguimientos):
    pytest.importorskip('streamlit')
    from pipeline.panel.semaforo_seguimiento import _calcular_semaforo
    from pipeline.panel.seguimiento_core import calcular_seguimiento
    s = _calcular_semaforo(seguimientos, hoy=HOY)
    cob = calcular_seguimiento(seguimientos, hoy=HOY)
    assert (s['completado'], s['al_dia'], s['rezago'], s['urgente']) == (2, 1, 1, 2)
    assert s['sin_ingreso'] == 1   # E solo tiene un TOP en tratamiento
    assert s['urgente'] == cob['n_elegibles'] - cob['n_con_top2']


def test_el_tiempo_entre_top_usa_el_mismo_top2(seguimientos):
    pytest.importorskip('streamlit')
    from pipeline.panel.tiempo_top import _calcular_tiempo
    res, sin_top2 = _calcular_tiempo(seguimientos, hoy=HOY)
    assert res.set_index('centro').loc['C1', 'promedio_dias'] == round((92 + 45) / 2)
    assert [c['centro'] for c in sin_top2] == ['C2']


def test_nadie_rotula_porcentaje_de_seguimiento_a_secas():
    import glob
    culpables = []
    rutas = glob.glob(os.path.join(RAIZ, 'pipeline', '**', '*.py'), recursive=True)
    rutas.append(os.path.join(RAIZ, 'app.py'))
    for ruta in rutas:
        with open(ruta, encoding='utf-8') as fh:
            for linea in fh:
                if linea.lstrip().startswith('#'):
                    continue
                if re.search(r"['\"][^'\"]*(% de seguimiento|% Continuidad|Cobertura seguimiento|Cobertura TOP2)", linea):
                    culpables.append(os.path.basename(ruta))
    assert not culpables, 'rótulo prohibido en: ' + ', '.join(sorted(set(culpables)))


# ── Las tarjetas cuentan con el mismo criterio que los gráficos ────────────

def test_la_tarjeta_pacientes_ingresados_cuenta_episodios(registros):
    pytest.importorskip('streamlit')
    from pipeline.panel.metricas import _calcular_metricas
    from pipeline.panel.kpis_centro import _calcular_kpis
    assert _calcular_metricas(registros)['pacientes_ingresados'] == len(lineas_base(registros))
    c1 = registros[registros['centro'] == 'C1']
    assert _calcular_kpis(c1, hoy=HOY)['pacientes_ingresados'] == len(lineas_base(c1))


def test_el_desglose_de_la_tarjeta_suma_el_total(registros):
    pytest.importorskip('streamlit')
    from pipeline.panel.metricas import _calcular_metricas
    df = pd.concat([registros, pd.DataFrame([('G', 'C1', '2026-04-01', 'seguimiento1'),
                                             ('H', 'C1', '2026-04-01', 'egreso')],
                                            columns=registros.columns)])
    m = _calcular_metricas(df)
    assert sum(n for n, _ in m['desglose_etapas']) == m['total_registros'] == len(df)
    assert (1, 'otra etiqueta') in m['desglose_etapas']


def test_las_tarjetas_del_centro_no_filtran_la_etapa_a_mano():
    for nombre in ('metricas', 'kpis_centro'):
        with open(os.path.join(RAIZ, 'pipeline', 'panel', nombre + '.py'), encoding='utf-8') as fh:
            src = fh.read()
        assert "== 'ingreso'" not in src, nombre + ' filtra la etapa a mano'
        assert 'lineas_base' in src, nombre + ' no usa lineas_base()'


def test_el_hover_de_otra_sustancia_muestra_el_desglose():
    pytest.importorskip('streamlit')
    from pipeline.panel.sustancia import _calcular_sustancias
    df = pd.DataFrame([
        ('A', 'C1', '2026-05-01', 'ingreso', 'Perú', 'Tusi'),
        ('B', 'C1', '2026-05-01', 'ingreso', 'Perú', 'Alcohol'),
    ], columns=['codigo_paciente', 'centro', 'fecha_entrevista', 'etapa', 'pais', 'sustancia_principal'])
    r = _calcular_sustancias(df)
    assert r['otras_desglose'].get('sin_reconocer') == 1
    assert r['otras_desglose']['_sin_reconocer_detalle'] == {'tusi': 1}
