"""
pipeline.panel.sustancia — Sustancia principal declarada al ingreso.

Aplica la TAXONOMÍA OFICIAL del TOP/UNODC:
  - Alcohol
  - Cannabis/Marihuana
  - Cocaína (clorhidrato)
  - Pasta base
  - Crack/Cristal (crack + metanfetaminas)
  - Tabaco/Nicotina
  - Sedantes
  - Heroína
  - Inhalables
  - Otras  (todo lo demás: Tusi, Ketamina, LSD, "Otra sustancia",
           múltiples sustancias declaradas, sin dato)

Diseño:
  - Barras verticales verdes con % del total de pacientes al ingreso
  - Todas las categorías con al menos 1 registro se muestran
  - "Otras" siempre al final (aunque supere alguna categoría principal)
  - Hover en "Otras" muestra el detalle interno

Función expuesta:
  render(df, pais, centro_id=None)
"""
import unicodedata
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion


COLOR_BARRA  = '#2E9B6C'   # verde consistente con continuidad
COLOR_OTRAS  = '#8FA9B9'   # gris azulado para "Otras"
TEXTO_OSCURO = '#1F3864'


# ═══════════════════════════════════════════════════════════════════════════════
# TAXONOMÍA OFICIAL TOP/UNODC
# ═══════════════════════════════════════════════════════════════════════════════

# Cada categoría es un conjunto de valores normalizados (mayúsculas, sin tildes)
# que se agrupan en ella. Ver _normalizar() abajo.
# ── Taxonomía alineada a wide_top.norm_sust_v3 (wide es fuente de verdad) ────
# Orden de evaluación importa: la primera regla que matchea gana.
# Cada entrada: (lista_de_substrings, nombre_categoria)
_REGLAS = [
    (['alcohol','alchol','cerveza','licor','aguard','beer','wine','ron'],  'Alcohol'),
    (['marihu','marhuana','cannabis','cannbis','marij','weed','crispy'],   'Cannabis/Marihuana'),
    (['tusi','tussi','tusy','tuci','2cb'],                                 'Tusi'),
    (['pasta base','pasta basica','papelillo','pbc','basuco','bazuco'],    'Pasta base'),
    (['metanfet','anfetam','cristal','crystal'],                           'Metanfetamina'),
    (['crack','piedra','paco'],                                            'Crack/Cristal'),
    (['cocain','cocai','perico','coke'],                                   'Cocaína'),
    (['tabaco','cigarr','nicot'],                                          'Tabaco/Nicotina'),
    (['inhalant','thiner','activo','pegamento','solvente'],                'Inhalables'),
    (['sedant','benzod','tranqui','clonaz','diazep','rivotril'],           'Sedantes'),
    (['opiod','heroina','morfin','fentanil','tramad'],                     'Opiáceos'),
    (['extasis','mdma','xtc'],                                             'Éxtasis'),
    (['ketam'],                                                            'Ketamina'),
]

# Orden visual fijo para el gráfico (de más a menos frecuente esperado)
ORDEN_CATEGORIAS = [r[1] for r in _REGLAS]

# Valores no informativos: se descartan (None) igual que en wide
_DESCARTAR = {
    'ninguno','ninguna','niega','no aplica','no consume','nada',
    'ludopatia','juego','apuesta','gaming','azar',
}

import re as _re

def _clasificar_sustancia(valor_original):
    """
    Replica la lógica de wide_top.norm_sust_v3:
      - Quita paréntesis
      - Toma primera sustancia en entradas múltiples (split / , + y)
      - Quita tildes y pasa a minúsculas
      - Evalúa reglas en orden
    Retorna: (categoria_str, subclase_str)
      subclase in {'canonico','no_informativo','multiple','en_blanco','sin_reconocer'}
    """
    if valor_original is None or (isinstance(valor_original, float) and pd.isna(valor_original)):
        return ('Otras', 'en_blanco')

    raw = str(valor_original).strip()
    if raw == '':
        return ('Otras', 'en_blanco')

    # Preprocesamiento igual a wide
    raw = _re.split(r'[\r\n]', raw)[0].strip()
    raw = _re.sub(r'\(.*?\)', '', raw).strip()
    raw = _re.sub(r'^(las dos|ambas|los dos|ambos)[,\s]+', '', raw, flags=_re.IGNORECASE).strip()

    es_multiple = bool(_re.search(r'\s+y\s+|[/,+]', raw))
    primera = _re.split(r'\s+y\s+|[/,+]', raw, maxsplit=1)[0].strip()

    # Normalizar: minúsculas + sin tildes
    n = unicodedata.normalize('NFD', primera.lower()).encode('ascii', 'ignore').decode()

    # Descartar no informativos
    if any(x in n for x in _DESCARTAR):
        return ('Otras', 'no_informativo')

    # Evaluar reglas en orden
    for keywords, categoria in _REGLAS:
        if any(x in n for x in keywords):
            return (categoria, 'canonico')

    # No reconocido
    if es_multiple:
        return ('Otras', 'multiple')
    return ('Otras', 'sin_reconocer')


# Alias para mantener compatibilidad con el resto del archivo
def _clasificar(valor_original):
    return _clasificar_sustancia(valor_original)





# ═══════════════════════════════════════════════════════════════════════════════
# CÁLCULO
# ═══════════════════════════════════════════════════════════════════════════════

def _calcular_sustancias(df):
    """
    Aplica la taxonomía oficial y devuelve el ranking + desglose de "Otras".

    Returns:
        dict con:
          ranking: pd.DataFrame [categoria, n, pct]  (siempre incluye Otras al final)
          otras_desglose: dict {subclase → n}  para tooltip
          total: int (denominador = pacientes con etapa=ingreso)
    """
    vacio = {
        'ranking': pd.DataFrame(columns=['categoria', 'n', 'pct']),
        'otras_desglose': {},
        'total': 0,
    }

    cols_req = {'etapa', 'sustancia_principal'}
    if df is None or df.empty or not cols_req.issubset(df.columns):
        return vacio

    tmp = df.copy()
    tmp['etapa'] = tmp['etapa'].fillna('').astype(str)
    tmp = tmp[tmp['etapa'] == 'ingreso']
    if tmp.empty:
        return vacio

    total = len(tmp)

    # Clasificar cada fila
    clasificaciones = tmp['sustancia_principal'].apply(_clasificar)
    tmp['categoria']  = clasificaciones.apply(lambda t: t[0])
    tmp['subclase']   = clasificaciones.apply(lambda t: t[1])

    # Conteos por categoría
    conteos = tmp.groupby('categoria').size().to_dict()

    # Desglose interno de "Otras" (para hover)
    otras = tmp[tmp['categoria'] == 'Otras']
    otras_desglose = otras.groupby('subclase').size().to_dict()

    # Además: detalle textual de las sustancias sin reconocer específicas
    # (Tusi, Ketamina, LSD...) para que el hover sea más informativo
    sin_reconocer_detalle = {}
    if 'sin_reconocer' in otras_desglose:
        sr = otras[otras['subclase'] == 'sin_reconocer']
        sr_norm = sr['sustancia_principal'].apply(_normalizar)
        for v in sr_norm.value_counts().items():
            sin_reconocer_detalle[v[0]] = int(v[1])

    otras_desglose['_sin_reconocer_detalle'] = sin_reconocer_detalle

    # Ranking: categorías principales ordenadas por conteo desc, luego "Otras" al final
    principales = []
    for cat in ORDEN_CATEGORIAS:
        n = int(conteos.get(cat, 0))
        if n > 0:
            principales.append({'categoria': cat, 'n': n})
    principales.sort(key=lambda d: -d['n'])

    filas = list(principales)
    n_otras = int(conteos.get('Otras', 0))
    if n_otras > 0:
        filas.append({'categoria': 'Otras', 'n': n_otras})

    if not filas:
        return vacio

    ranking = pd.DataFrame(filas)
    ranking['pct'] = ranking['n'] / total * 100

    return {
        'ranking': ranking,
        'otras_desglose': otras_desglose,
        'total': total,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def _formatear_hover_otras(desglose):
    """Construye el texto de hover para la barra 'Otras' con su desglose."""
    partes = []
    etiquetas = {
        'sin_reconocer':    'Otras drogas específicas',
        'no_informativo':   'Declaró "Otra sustancia"',
        'multiple':         'Múltiples sustancias',
        'en_blanco':        'Sin dato',
    }
    for k, label in etiquetas.items():
        n = desglose.get(k, 0)
        if n > 0:
            partes.append(f'  · {label}: {n}')

    detalle = desglose.get('_sin_reconocer_detalle', {})
    if detalle:
        partes.append('  ')
        partes.append('  Detalle:')
        for nombre, n in sorted(detalle.items(), key=lambda x: -x[1])[:8]:
            partes.append(f'    - {nombre.title()}: {n}')

    return '<br>'.join(partes) if partes else ''


def render(df, pais, centro_id=None):
    with st.container(border=True):
        if centro_id and 'centro' in df.columns:
            df_local = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()
        else:
            df_local = df

        res = _calcular_sustancias(df_local)
        ranking       = res['ranking']
        otras_desglose = res['otras_desglose']
        total         = res['total']

        st.markdown(
            titulo_seccion('💊', 'Sustancia principal declarada',
                           f'% del total de pacientes al ingreso · N = {total}'),
            unsafe_allow_html=True
        )

        if ranking.empty:
            st.info('ℹ Aún no hay datos de sustancia principal para el ingreso.')
            return

        # Colores: Otras siempre en gris, las demás en verde
        colores = [COLOR_OTRAS if c == 'Otras' else COLOR_BARRA for c in ranking['categoria']]

        # Hovers
        hovers = []
        for _, row in ranking.iterrows():
            base = f"<b>{row['categoria']}</b><br>{int(row['n'])} pacientes<br>{row['pct']:.1f}%".replace('.', ',')
            if row['categoria'] == 'Otras':
                detalle = _formatear_hover_otras(otras_desglose)
                if detalle:
                    base = base + '<br>' + detalle
            hovers.append(base)

        textos = [f'{p:.0f}%' for p in ranking['pct']]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ranking['categoria'],
            y=ranking['pct'],
            marker=dict(color=colores, line=dict(width=0)),
            text=textos,
            textposition='outside',
            textfont=dict(color=TEXTO_OSCURO, size=12, family='Arial'),
            hovertext=hovers,
            hoverinfo='text',
            showlegend=False,
            cliponaxis=False,
        ))

        max_pct = float(ranking['pct'].max())

        fig.update_layout(
            height=175,
            margin=dict(l=8, r=8, t=10, b=8),
            xaxis=dict(
                tickfont=dict(size=10, color=TEXTO_OSCURO, family='Arial'),
                fixedrange=True,
                tickangle=0,
            ),
            yaxis=dict(
                visible=False,
                range=[0, max_pct * 1.25],
                fixedrange=True,
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # Pequeña nota debajo con el desglose de "Otras" si hay algo relevante
        if otras_desglose.get('no_informativo', 0) + otras_desglose.get('en_blanco', 0) + otras_desglose.get('multiple', 0) > 0:
            partes = []
            n_sr  = otras_desglose.get('sin_reconocer', 0)
            n_ni  = otras_desglose.get('no_informativo', 0)
            n_mul = otras_desglose.get('multiple', 0)
            n_bl  = otras_desglose.get('en_blanco', 0)
            if n_sr > 0:  partes.append(f'{n_sr} otras drogas específicas')
            if n_ni > 0:  partes.append(f'{n_ni} "Otra sustancia"')
            if n_mul > 0: partes.append(f'{n_mul} múltiples')
            if n_bl > 0:  partes.append(f'{n_bl} sin dato')
            if partes:
                st.markdown(
                    f'<div style="font-size:.7rem;color:#888;padding:.1rem .1rem 0 .1rem;'
                    f'line-height:1.35;">Otras incluye: ' + ' · '.join(partes) + '</div>',
                    unsafe_allow_html=True
                )
