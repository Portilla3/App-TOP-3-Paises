"""
pipeline.validacion_top — Criterios de validación compartidos para datos TOP.

Fuente de verdad única para los umbrales que definen un valor "imposible" en
el instrumento TOP. Usado tanto por el pipeline de reportes (wide_top.py,
caract_excel.py) como por el dashboard interactivo (pipeline/panel/*.py),
para que ambos apliquen exactamente el mismo criterio y no diverjan cuando
entre un dato sucio nuevo.

Decisión de arquitectura (2026-07-20): antes de este módulo, cada consumidor
reimplementaba su propio filtro (dias_consumo.py duplicaba el filtro 0-28;
edad.py y salud.py no filtraban nada). Este módulo centraliza esos criterios.

Criterios:
  - Días de consumo semanal:  0-7   (una semana tiene 7 días)
  - Días de consumo mensual:  0-28  (4 semanas)
  - Fecha de nacimiento:      la edad calculada (contra fecha_entrevista, o
                               contra hoy si no hay fecha_entrevista) debe
                               estar entre 10 y 100 años. Criterio dinámico
                               (no un año fijo), igual al que ya usaba
                               wide_top.py antes de este módulo.
  - Escalas de salud/calidad de vida (TOP): 0-20

No confundir con el rango de pandas (años 1677-2262), que es un límite
técnico de la librería, no un criterio clínico; se mantiene como resguardo
adicional dentro de edad_valida() pero no reemplaza el criterio clínico.
"""
import re
import unicodedata

import pandas as pd

# ── Umbrales centralizados ──────────────────────────────────────────────────
DIAS_SEMANA_MIN, DIAS_SEMANA_MAX = 0, 7
DIAS_MES_MIN, DIAS_MES_MAX = 0, 28

EDAD_MINIMA_ANIOS = 10
EDAD_MAXIMA_ANIOS = 100

ESCALA_SALUD_MIN, ESCALA_SALUD_MAX = 0, 20

_PANDAS_ANIO_MIN, _PANDAS_ANIO_MAX = 1677, 2262


def _norm_str(s):
    """Minúsculas, sin tildes y sin espacios de borde. Base de toda comparación
    de texto libre del sistema."""
    return (unicodedata.normalize('NFD', str(s).lower())
            .encode('ascii', 'ignore').decode().strip())


def dias_validos_semana(serie):
    """
    Recibe una Serie numérica (días de consumo en una semana, columnas *_s1..*_s4)
    y devuelve una Serie del mismo largo donde los valores fuera de 0-7 quedan
    en NaN. No modifica el resto.
    """
    num = pd.to_numeric(serie, errors='coerce')
    return num.where((num >= DIAS_SEMANA_MIN) & (num <= DIAS_SEMANA_MAX))


def dias_validos_mes(serie):
    """
    Recibe una Serie numérica (columnas *_total, escala 0-28) y devuelve una
    Serie donde los valores fuera de 0-28 quedan en NaN.
    """
    num = pd.to_numeric(serie, errors='coerce')
    return num.where((num >= DIAS_MES_MIN) & (num <= DIAS_MES_MAX))


def fecha_nacimiento_valida(serie_fecha_nacimiento, serie_fecha_referencia=None):
    """
    Recibe una Serie de fecha_nacimiento (y opcionalmente una Serie de
    fecha_entrevista para calcular la edad contra esa fecha en vez de hoy) y
    devuelve una Serie de fechas donde los valores imposibles quedan en NaT.

    Imposible = la edad calculada es menor a EDAD_MINIMA_ANIOS o mayor a
    EDAD_MAXIMA_ANIOS, o la fecha cae fuera del rango técnico que pandas
    puede representar (1677-2262).
    """
    fn = pd.to_datetime(serie_fecha_nacimiento, errors='coerce')

    if serie_fecha_referencia is not None:
        ref = pd.to_datetime(serie_fecha_referencia, errors='coerce')
        ref = ref.fillna(pd.Timestamp.now())
    else:
        ref = pd.Timestamp.now()

    edad_anios = (ref - fn).dt.days / 365.25

    invalida = (
        fn.isna()
        | (edad_anios < EDAD_MINIMA_ANIOS)
        | (edad_anios > EDAD_MAXIMA_ANIOS)
        | (fn.dt.year < _PANDAS_ANIO_MIN)
        | (fn.dt.year > _PANDAS_ANIO_MAX)
    )
    return fn.where(~invalida)


def edad_valida(serie_fecha_nacimiento, serie_fecha_referencia=None):
    """
    Igual que fecha_nacimiento_valida(), pero devuelve directamente la edad en
    años (float), con NaN donde la fecha de nacimiento es inválida. Pensado
    para pipeline/panel/edad.py, que necesita la edad, no la fecha.
    """
    fn_valida = fecha_nacimiento_valida(serie_fecha_nacimiento, serie_fecha_referencia)

    if serie_fecha_referencia is not None:
        ref = pd.to_datetime(serie_fecha_referencia, errors='coerce')
        ref = ref.fillna(pd.Timestamp.now())
    else:
        ref = pd.Timestamp.now()

    return (ref - fn_valida).dt.days / 365.25


def escala_salud_valida(serie):
    """
    Recibe una Serie numérica (salud_psicologica, salud_fisica, calidad_vida,
    escala 0-20 en el instrumento TOP) y devuelve una Serie donde los valores
    fuera de 0-20 quedan en NaN.
    """
    num = pd.to_numeric(serie, errors='coerce')
    return num.where((num >= ESCALA_SALUD_MIN) & (num <= ESCALA_SALUD_MAX))


# ── Sexo ────────────────────────────────────────────────────────────────────
# Convención regional única desde 2026-08-28: H = Hombre, M = Mujer, O = Otro.
#
# Antes de esta fecha convivían dos convenciones en la misma columna. Perú
# escribía M=Masculino y F=Femenino desde sus formularios, mientras Ecuador,
# El Salvador y México escribían H=Hombre y M=Mujer. Los módulos de reportes
# leían H/M y los del panel leían M/F, de modo que ningún país quedaba bien
# contado en ambos lados: el panel mostraba cero mujeres en Ecuador, El
# Salvador y México, y los informes de Perú reportaban 85% de mujeres.
#
# La base de Perú fue homologada a H/M/O y todos los formularios escriben esa
# convención. Esta función es la única fuente de verdad para leer el campo, y
# sigue aceptando 'F' y las variantes en texto por si entra un dato histórico.

_SEXO_HOMBRE = ('hombre', 'masculino', 'masc', 'male', 'varon', 'varón')
_SEXO_MUJER  = ('mujer', 'femenino', 'fem', 'female')
_SEXO_OTRO   = ('otro', 'otra', 'no binario', 'no binarie', 'nb', 'intersex')


def normalizar_sexo_valor(v):
    """
    Normaliza un valor del campo sexo a 'H', 'M', 'O' o None.

    None se reserva para el dato ausente, para que los módulos puedan
    excluirlo del N válido. Un texto libre que no corresponda a ninguna
    categoría conocida (por ejemplo 'ASEXUAL') se clasifica como 'O'.
    """
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass

    s = str(v).strip().lower()
    if not s:
        return None

    if s == 'h' or s.startswith(_SEXO_HOMBRE):
        return 'H'
    if s in ('m', 'f') or s.startswith(_SEXO_MUJER):
        return 'M'
    if s == 'o' or s.startswith(_SEXO_OTRO):
        return 'O'
    return 'O'


def normalizar_sexo(serie):
    """
    Versión vectorizada de normalizar_sexo_valor() para una Serie de pandas.
    Devuelve una Serie con valores 'H', 'M', 'O' o None.
    """
    return pd.Series(serie).apply(normalizar_sexo_valor)


# ── Flags booleanos ─────────────────────────────────────────────────────────
# Los formularios escriben las casillas "no aplica" (trabajo_na, educacion_na)
# como booleanos de JavaScript, pero llegan al Base Wide en formatos distintos
# según la etapa: en el TOP de ingreso como True/False y en el de seguimiento
# como 1.0/0.0. Un criterio que reconozca solo uno de los dos deja pasar
# registros que debía excluir, sin avisar.
_FLAG_ACTIVO = {'true', 't', 'si', 'sí', 'yes', 'y', 'x', '1', '1.0'}


def es_flag_activo(serie):
    """
    Recibe una Serie con un flag booleano tal como llega del Base Wide y
    devuelve una Serie de booleanos donde True significa que el flag está
    marcado. Reconoce True/False, 1.0/0.0, 1/0 y las variantes de texto.
    Los vacíos cuentan como no marcado.
    """
    return (pd.Series(serie).astype(str).str.strip().str.lower()
            .isin(_FLAG_ACTIVO))


# ── Sustancia principal ─────────────────────────────────────────────────────
# Cada país tiene su propia lista cerrada de sustancia principal en el
# formulario, y esa lista coincide con las columnas de días que ese país mide.
# La regla, decidida el 2026-09-02: una sustancia declarada que no está en la
# lista de su país va a 'Otra sustancia', que tiene su propia columna de días
# (otra_sust_total) y su propio campo de texto (otra_sust_nombre).
#
# Antes de esto el clasificador estaba copiado en diez módulos, con tres
# vocabularios distintos ('Marihuana' contra 'Cannabis/Marihuana', 'Crack'
# contra 'Crack/Cristal'), y el mapeo del panel esperaba nombres que el
# clasificador nunca devolvía. Eso dejaba fuera al 12 % de los pacientes.

OTRA_SUSTANCIA = 'Otra sustancia'

# Categoría canónica → columna de días en Supabase
SUSTANCIA_A_COLUMNA = {
    'Alcohol':          'alcohol_total',
    'Marihuana':        'marihuana_total',
    'Pasta Base':       'pastabase_total',
    'Cocaína':          'cocaina_total',
    'Crack':            'crack_total',
    'Metanfetamina':    'metanfetamina_total',
    'Heroína':          'heroina_total',
    'Sedantes':         'sedantes_total',
    OTRA_SUSTANCIA:     'otra_sust_total',
}

# Categorías que ofrece el formulario de cada país, en orden de presentación.
# Es la taxonomía madre: define qué barras aparecen en los gráficos de ese país.
CATEGORIAS_POR_PAIS = {
    'Perú':                 ['Alcohol', 'Marihuana', 'Pasta Base', 'Cocaína', 'Sedantes', OTRA_SUSTANCIA],
    'Ecuador':              ['Alcohol', 'Marihuana', 'Pasta Base', 'Cocaína', 'Sedantes', 'Heroína', OTRA_SUSTANCIA],
    'El Salvador':          ['Alcohol', 'Marihuana', 'Crack', 'Cocaína', 'Sedantes', OTRA_SUSTANCIA],
    'México':               ['Alcohol', 'Marihuana', 'Metanfetamina', 'Cocaína', 'Sedantes', OTRA_SUSTANCIA],
    'México CIJ':           ['Alcohol', 'Marihuana', 'Metanfetamina', 'Cocaína', 'Sedantes', OTRA_SUSTANCIA],
    'México Monte Fénix':   ['Alcohol', 'Marihuana', 'Metanfetamina', 'Cocaína', 'Sedantes', OTRA_SUSTANCIA],
    'México Mahanaim':      ['Alcohol', 'Marihuana', 'Metanfetamina', 'Cocaína', 'Sedantes', OTRA_SUSTANCIA],
}

# Etiqueta visible por país. México presenta cocaína y crack como una sola
# opción en su formulario, así que sus días van todos a cocaina_total.
ETIQUETAS_POR_PAIS = {
    'México':               {'Cocaína': 'Cocaína/crack', 'Metanfetamina': 'Metanfetamina (cristal)'},
    'México CIJ':           {'Cocaína': 'Cocaína/crack', 'Metanfetamina': 'Metanfetamina (cristal)'},
    'México Monte Fénix':   {'Cocaína': 'Cocaína/crack', 'Metanfetamina': 'Metanfetamina (cristal)'},
    'México Mahanaim':      {'Cocaína': 'Cocaína/crack', 'Metanfetamina': 'Metanfetamina (cristal)'},
    'Ecuador':              {'Pasta Base': 'Pasta Base/basuco'},
}

# Sinónimos y erratas del histórico, de cuando el campo era texto libre.
# El orden importa: 'pasta base' antes que 'base', 'crack' antes que 'cocaina'.
_SINONIMOS = [
    (['pasta base', 'pasta basica', 'pastabase', 'papelillo', 'pbc', 'basuco', 'bazuco'], 'Pasta Base'),
    (['metanfet', 'anfetam', 'cristal', 'crystal'],                                       'Metanfetamina'),
    (['crack', 'piedra', 'paco'],                                                         'Crack'),
    (['heroina', 'heroína', 'heroin'],                                                    'Heroína'),
    (['alcohol', 'alchol', 'cerveza', 'licor', 'aguard', 'beer', 'wine', 'ron'],           'Alcohol'),
    (['marihu', 'marhuana', 'cannabis', 'cannbis', 'marij', 'weed', 'crispy'],             'Marihuana'),
    (['cocain', 'cocai', 'perico', 'coke'],                                               'Cocaína'),
    (['sedant', 'benzod', 'tranqui', 'clonaz', 'diazep', 'rivotril'],                      'Sedantes'),
]

# Respuestas que no nombran una sustancia: se descartan, no van a 'Otra'.
# 'minguna' es la errata habitual de 'ninguna' en los registros del pilotaje.
_SIN_SUSTANCIA = ['ninguno', 'ninguna', 'minguna', 'niega', 'no aplica',
                  'no consume', 'nada', 'ludopatia', 'juego', 'apuesta',
                  'gaming', 'azar']

# Respuestas de una o dos letras que significan "no", y marcadores de vacío.
# Van por coincidencia exacta: como subcadena, 'n' o 'no' aparecerían dentro de
# casi cualquier nombre de sustancia.
_VACIO_EXACTO = {'n', 's', 'no', 'na', 'nan', 'ninguna.', '-', '--', '0', 'x', 'sd'}


def _limpiar_declaracion(texto):
    """Deja la primera sustancia declarada, sin paréntesis ni conectores."""
    raw = str(texto).strip()
    if raw in ('0', ''):
        return None
    raw = re.split(r'[\r\n]', raw)[0].strip()
    raw = re.sub(r'\(.*?\)', '', raw).strip()
    raw = re.sub(r'^(las dos|ambas|los dos|ambos)[,\s]+', '', raw, flags=re.IGNORECASE).strip()
    return re.split(r'\s+y\s+|[/,+]', raw, maxsplit=1)[0].strip()


def clasificar_sustancia(texto, pais=None):
    """
    Devuelve la categoría canónica de una sustancia principal declarada.

    Si `pais` viene dado, cualquier sustancia que no esté en la lista de ese
    país cae en 'Otra sustancia'. Sin `pais`, devuelve la categoría canónica
    sin filtrar, para usos que no dependen del formulario.

    Devuelve None cuando no hay declaración o cuando lo declarado no es una
    sustancia (ninguna, ludopatía). Esos casos son ausencia de dato y quedan
    fuera del denominador.
    """
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return None
    primera = _limpiar_declaracion(texto)
    if not primera:
        return None
    n = _norm_str(primera)
    if n in _VACIO_EXACTO or any(x in n for x in _SIN_SUSTANCIA):
        return None

    cat = next((c for claves, c in _SINONIMOS if any(k in n for k in claves)), OTRA_SUSTANCIA)

    if pais is not None:
        permitidas = CATEGORIAS_POR_PAIS.get(pais)
        if permitidas is not None and cat not in permitidas:
            return OTRA_SUSTANCIA
    return cat


def categorias_pais(pais):
    """Categorías que se dibujan para ese país, siempre todas y en orden fijo."""
    return list(CATEGORIAS_POR_PAIS.get(pais, list(SUSTANCIA_A_COLUMNA.keys())))


def etiqueta_sustancia(categoria, pais=None):
    """Nombre visible de la categoría en los gráficos de ese país."""
    return ETIQUETAS_POR_PAIS.get(pais, {}).get(categoria, categoria)


# Palabras que delatan el país por las sustancias que mide su formulario.
# Se evalúan en orden: Ecuador antes que Perú, porque Ecuador tiene pasta base
# además de heroína.
_HUELLA_PAIS = [
    ('heroina',       'Ecuador'),
    ('crack',         'El Salvador'),
    ('metanfetamina', 'México'),
    ('pastabase',     'Perú'),
    ('pasta base',    'Perú'),
]


def detectar_pais(df):
    """
    Devuelve el país de un conjunto de registros.

    Primero busca una columna de país, que existe tanto en la tabla de Supabase
    (`pais`) como en el Base Wide (`pais_TOP1`). Solo si no la encuentra recurre
    a deducirlo por las columnas de días que traen datos, porque el Wide genera
    columnas para todas las sustancias del sistema estén llenas o no, y la sola
    presencia de `heroina_total` no dice nada.

    Devuelve None si no logra determinarlo, y en ese caso quien llame debe
    permitir todas las categorías en vez de filtrar de más.
    """
    for col in df.columns:
        if _norm_str(col).split('_')[0] in ('pais', 'country'):
            vals = df[col].dropna().astype(str).str.strip()
            if not vals.empty:
                return vals.mode().iloc[0]

    presentes = set()
    for col in df.columns:
        n = _norm_str(col)
        for huella, _ in _HUELLA_PAIS:
            if huella in n and df[col].notna().any():
                presentes.add(huella)
    return next((p for huella, p in _HUELLA_PAIS if huella in presentes), None)


# ── Episodios de tratamiento ────────────────────────────────────────────────
# La unidad de análisis es el episodio, no la persona: quien ingresa dos veces
# al mismo centro, o a dos centros distintos, cuenta dos veces. Decidido el
# 2026-09-02, con el criterio del NDTMS británico de donde viene el instrumento.
#
# Un TOP con etapa de ingreso abre un episodio. Los TOP siguientes del mismo
# paciente en el mismo centro pertenecen a ese episodio hasta que aparezca otro
# ingreso. Los TOP anteriores a cualquier ingreso no pertenecen a ninguno: son
# de pacientes que ya estaban en tratamiento cuando el centro adoptó el TOP, y
# no describen cómo llegó esa persona.

ETAPA_INGRESO = 'ingreso'


def es_etapa_ingreso(valor):
    """Reconoce la etapa de ingreso tolerando mayúsculas, tildes y espacios."""
    return _norm_str(valor) == ETAPA_INGRESO


def construir_episodios(df, col_codigo='codigo_paciente', col_centro='centro',
                        col_fecha='fecha_entrevista', col_etapa='etapa'):
    """
    Agrega la columna `_episodio` al DataFrame.

    El identificador de un episodio es `código|centro|fecha del TOP de ingreso`.
    Los registros que no pertenecen a ningún episodio quedan en None y deben
    excluirse de la caracterización y del análisis de cambio.

    No modifica el DataFrame recibido.
    """
    d = df.copy()
    d['_fecha_ord'] = pd.to_datetime(d[col_fecha], errors='coerce')
    d = d.sort_values([col_codigo, col_centro, '_fecha_ord'], na_position='last')

    episodios = []
    actual = None
    clave_previa = None
    for _, fila in d.iterrows():
        clave = (fila[col_codigo], fila[col_centro])
        if clave != clave_previa:
            actual = None
            clave_previa = clave
        if es_etapa_ingreso(fila[col_etapa]):
            fecha = fila['_fecha_ord']
            marca = fecha.strftime('%Y-%m-%d') if pd.notna(fecha) else 'sin-fecha'
            actual = f'{fila[col_codigo]}|{fila[col_centro]}|{marca}'
        episodios.append(actual)

    d['_episodio'] = episodios
    return d.drop(columns='_fecha_ord').reindex(df.index)


def lineas_base(df, col_codigo='codigo_paciente', col_centro='centro',
                col_fecha='fecha_entrevista', col_etapa='etapa'):
    """
    Devuelve una fila por episodio: el TOP de ingreso que lo abre.

    Es la población de la caracterización. Reemplaza al filtro
    `etapa == 'ingreso'`, que contaba dos veces los ingresos duplicados y no
    distinguía episodios del mismo paciente en centros distintos.
    """
    faltan = {col_codigo, col_centro, col_etapa} - set(df.columns)
    if faltan:
        return df.iloc[0:0]
    d = construir_episodios(df, col_codigo, col_centro, col_fecha, col_etapa)
    d = d[d['_episodio'].notna() & d[col_etapa].apply(es_etapa_ingreso)]
    return d.drop_duplicates(subset='_episodio', keep='first')


# Palabras que identifican la columna de días de cada categoría, sirvan los
# nombres cortos de Supabase (`alcohol_total`) o los largos del Base Wide
# (`Alcohol Total (0-28)_TOP1`).
_PALABRA_DE_SUSTANCIA = {
    'Alcohol':       'alcohol',
    'Marihuana':     'marihuana',
    'Pasta Base':    'pasta',
    'Cocaína':       'cocaina',
    'Crack':         'crack',
    'Metanfetamina': 'metanfetamina',
    'Heroína':       'heroina',
    'Sedantes':      'sedantes',
    OTRA_SUSTANCIA:  'otra_sust',
}


def columna_de_sustancia(categoria, columnas, sufijo='_TOP1'):
    """
    Encuentra la columna de días totales de una categoría entre las columnas
    dadas. Devuelve None si esa sustancia no se mide en ese formulario, que es
    lo que ocurre con crack en Perú o heroína en México.
    """
    palabra = _PALABRA_DE_SUSTANCIA.get(categoria)
    if palabra is None:
        return None
    candidatas = [c for c in columnas if palabra in _norm_str(c)]
    if not candidatas:
        return None
    totales = [c for c in candidatas if 'total' in _norm_str(c)]
    if not totales:
        return None
    conservan_sufijo = [c for c in totales if _norm_str(c).endswith(_norm_str(sufijo))]
    return (conservan_sufijo or totales)[0]


# ── Rangos etarios ──────────────────────────────────────────────────────────
# El panel clasificaba con `int(edad) < 18` y los cuatro módulos de reporte con
# `pd.cut(bins=[0,17,30,...])`. Como la edad es un float, alguien de 17 años y
# medio caía en "Menos de 18" en el panel y en "18 a 30" en los informes, y el
# mismo país mostraba un conteo distinto en cada salida.

RANGOS_ETARIOS = ['Menos de 18', '18 a 30', '31 a 40', '41 a 50', '51 a 60', '61 o más']

_CORTES_ETARIOS = [(18, 'Menos de 18'), (31, '18 a 30'), (41, '31 a 40'),
                   (51, '41 a 50'), (61, '51 a 60')]


def rango_etario(edad, sufijo=''):
    """
    Devuelve el rango etario de una edad, o None si no es válida.

    Los años se cuentan cumplidos: quien tiene 17 años y medio está en "Menos de
    18", no en "18 a 30". `sufijo` permite ' años' para las tablas que lo usan.
    """
    if edad is None or pd.isna(edad):
        return None
    try:
        anios = int(float(edad))
    except (TypeError, ValueError):
        return None
    etiqueta = next((r for tope, r in _CORTES_ETARIOS if anios < tope), '61 o más')
    return etiqueta + sufijo


def rangos_etarios(serie, sufijo=''):
    """Versión vectorizada de rango_etario() para una Serie."""
    return pd.Series(serie).apply(lambda v: rango_etario(v, sufijo))
