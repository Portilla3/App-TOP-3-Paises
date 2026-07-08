"""
pipeline.panel.sustancia — Sustancia principal declarada al ingreso.

Muestra el ranking de sustancias declaradas como principales por los pacientes
al momento del ingreso (etapa='ingreso'). El campo Supabase es 'sustancia_principal'
(text libre normalizado por los formularios de cada país).

Diseño:
  - Barras verticales, top 5-6 sustancias, resto agrupado en "Otras"
  - Color verde consistente con el bloque perfil
  - Porcentaje encima de cada barra
  - Nombre de la sustancia debajo

Función expuesta:
  render(df, pais, centro_id=None)

Notas de instrumento:
  Este componente es agnóstico al catálogo de sustancias por país. Se limita
  a leer 'sustancia_principal' tal como viene en Supabase y a agrupar.
  Cuando lleguemos a "columnas_instrumento" para el gráfico de "Días de
  consumo por sustancia" (sesión 4), ese sí necesita el catálogo por país.
"""
import unicodedata
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion


COLOR_BARRA  = '#2E9B6C'   # verde consistente con continuidad
TEXTO_OSCURO = '#1F3864'


TOP_N_SUSTANCIAS = 6


# Nombres canónicos para display. Se aplica sobre la versión normalizada
# (mayúsculas y sin tildes). Las que no estén en el mapa se muestran
# en Title Case como fallback.
NOMBRES_CANONICOS = {
    'ALCOHOL':     'Alcohol',
    'MARIHUANA':   'Marihuana',
    'MARIGUANA':   'Marihuana',
    'COCAINA':     'Cocaína',
    'PASTA BASE':  'Pasta base',
    'PASTA':       'Pasta base',
    'BASUCO':      'Pasta base',
    'PASTA BASE/BASUCO': 'Pasta base',
    'PASTA BASE / BASUCO': 'Pasta base',
    'CRACK':       'Crack',
    'PIEDRA':      'Crack',
    'HEROINA':     'Heroína',
    'SEDANTES':    'Sedantes',
    'BENZODIACEPINAS': 'Sedantes',
    'INHALABLES':  'Inhalables',
    'INHALANTES':  'Inhalables',
    'TUSI':        'Tusi',
    'TUSSI':       'Tusi',
    'DOS CG':      'Tusi',
    'ANFETAMINAS': 'Anfetaminas',
    'METANFETAMINAS': 'Metanfetaminas',
    'CRISTAL':     'Metanfetaminas',
    'ECSTASY':     'Éxtasis',
    'EXTASIS':     'Éxtasis',
    'LSD':         'LSD',
    'KETAMINA':    'Ketamina',
    'OTRA':        'Otra',
    'OTRO':        'Otra',
    'OTRAS':       'Otras',
    'OTROS':       'Otras',
    'NINGUNA':     'Ninguna',
    'NINGUNO':     'Ninguna',
}


def _normalizar(s):
    """Convierte a mayúsculas y quita tildes para comparación."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ''
    txt = str(s).strip().upper()
    # Quitar tildes
    txt = ''.join(
        c for c in unicodedata.normalize('NFD', txt)
        if unicodedata.category(c) != 'Mn'
    )
    return txt


def _display(clave_normalizada):
    """Devuelve el nombre canónico para mostrar. Fallback: Title Case."""
    if clave_normalizada in NOMBRES_CANONICOS:
        return NOMBRES_CANONICOS[clave_normalizada]
    return clave_normalizada.title()


def _calcular_sustancias(df):
    """
    Filtra a etapa=ingreso, normaliza el texto (mayúsculas + sin tildes)
    y agrupa por sustancia_principal.

    Separa: (a) el ranking con sustancias específicas + bucket 'Otras (menos
    frecuentes)' si hay más de TOP_N, y (b) el conteo de pacientes que
    declararon 'Otra sustancia' sin especificar (no entra al ranking porque
    no informa qué droga es el problema).

    Returns:
        dict con claves:
            ranking: pd.DataFrame con columnas sustancia, n, pct
            n_otra_sin_especificar: int (pacientes con 'Otra')
            pct_otra_sin_especificar: float
            total_valid: int
    """
    vacio = {
        'ranking': pd.DataFrame(columns=['sustancia', 'n', 'pct']),
        'n_otra_sin_especificar': 0,
        'pct_otra_sin_especificar': 0.0,
        'n_en_blanco': 0,
        'pct_en_blanco': 0.0,
        'total_valid': 0,
    }

    cols_req = {'etapa', 'sustancia_principal'}
    if df is None or df.empty or not cols_req.issubset(df.columns):
        return vacio

    tmp = df.copy()
    tmp['etapa'] = tmp['etapa'].fillna('').astype(str)
    tmp = tmp[tmp['etapa'] == 'ingreso']
    if tmp.empty:
        return vacio

    total_ingreso = len(tmp)   # total de pacientes con TOP1 (denominador honesto)

    tmp['sust_norm'] = tmp['sustancia_principal'].apply(_normalizar)

    # Contar los en blanco antes de filtrarlos
    n_blanco = int((tmp['sust_norm'] == '').sum())
    tmp = tmp[tmp['sust_norm'] != '']

    if tmp.empty:
        return {
            **vacio,
            'n_en_blanco': n_blanco,
            'pct_en_blanco': (n_blanco / total_ingreso * 100) if total_ingreso else 0.0,
        }

    # Separar "Otra sustancia" genérica antes de contar
    NO_INFORMATIVOS = {
        'OTRA', 'OTRO', 'OTRAS', 'OTROS',
        'OTRA SUSTANCIA', 'OTRAS SUSTANCIAS',
        'NO SABE', 'NS', 'NR', 'NO RESPONDE', 'NINGUNA', 'NINGUNO',
    }
    mask_no_inf = tmp['sust_norm'].isin(NO_INFORMATIVOS)
    n_no_inf = int(mask_no_inf.sum())

    ranking_src = tmp[~mask_no_inf]
    if ranking_src.empty:
        return {
            **vacio,
            'n_otra_sin_especificar': n_no_inf,
            'pct_otra_sin_especificar': (n_no_inf / total_ingreso * 100) if total_ingreso else 0.0,
            'n_en_blanco': n_blanco,
            'pct_en_blanco': (n_blanco / total_ingreso * 100) if total_ingreso else 0.0,
        }

    total_valid = len(ranking_src)
    conteo = ranking_src.groupby('sust_norm').size().reset_index(name='n')
    conteo = conteo.sort_values('n', ascending=False).reset_index(drop=True)

    if len(conteo) > TOP_N_SUSTANCIAS:
        top   = conteo.iloc[:TOP_N_SUSTANCIAS].copy()
        resto = conteo.iloc[TOP_N_SUSTANCIAS:]
        if len(resto) > 0:
            fila_resto = pd.DataFrame([{
                'sust_norm': '__RESTO__',
                'n': int(resto['n'].sum())
            }])
            top = pd.concat([top, fila_resto], ignore_index=True)
        conteo = top

    def _label(k):
        if k == '__RESTO__':
            return 'Otras (menos frecuentes)'
        return _display(k)

    conteo['sustancia'] = conteo['sust_norm'].apply(_label)
    conteo['pct']       = conteo['n'] / total_valid * 100

    return {
        'ranking': conteo[['sustancia', 'n', 'pct']],
        'n_otra_sin_especificar': n_no_inf,
        'pct_otra_sin_especificar': (n_no_inf / total_ingreso * 100) if total_ingreso else 0.0,
        'n_en_blanco': n_blanco,
        'pct_en_blanco': (n_blanco / total_ingreso * 100) if total_ingreso else 0.0,
        'total_valid': total_valid,
    }


def render(df, pais, centro_id=None):
    """
    Pinta las barras de sustancia principal declarada al ingreso.
    Excluye del ranking los registros con 'Otra sustancia' sin especificar
    y los muestra como nota debajo del gráfico.
    """
    with st.container(border=True):
        # Filtrado opcional por centro
        if centro_id and 'centro' in df.columns:
            df_local = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()
        else:
            df_local = df

        res = _calcular_sustancias(df_local)
        conteo     = res['ranking']
        n_no_inf   = res['n_otra_sin_especificar']
        pct_no_inf = res['pct_otra_sin_especificar']
        n_blanco   = res['n_en_blanco']
        pct_blanco = res['pct_en_blanco']

        # Título con subtítulo dinámico según haya "Otra sustancia" o no
        subtitulo = '% de pacientes al ingreso · sustancias específicas'
        st.markdown(
            titulo_seccion('💊', 'Sustancia principal declarada', subtitulo),
            unsafe_allow_html=True
        )

        if conteo.empty:
            if n_no_inf > 0 or n_blanco > 0:
                st.info(
                    f'ℹ No hay sustancias específicas para rankear. '
                    f'{n_no_inf} declararon "Otra sustancia", {n_blanco} sin dato.'
                )
            else:
                st.info('ℹ Aún no hay datos de sustancia principal para el ingreso.')
            return

        textos = [f'{p:.0f}%' for p in conteo['pct']]
        hovers = [
            f'<b>{s}</b><br>{n} pacientes<br>{p:.1f}%'.replace('.', ',')
            for s, n, p in zip(conteo['sustancia'], conteo['n'], conteo['pct'])
        ]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=conteo['sustancia'],
            y=conteo['pct'],
            marker=dict(color=COLOR_BARRA, line=dict(width=0)),
            text=textos,
            textposition='outside',
            textfont=dict(color=TEXTO_OSCURO, size=12, family='Arial'),
            hovertext=hovers,
            hoverinfo='text',
            showlegend=False,
            cliponaxis=False,
        ))

        max_pct = float(conteo['pct'].max()) if not conteo.empty else 100.0

        fig.update_layout(
            height=170,
            margin=dict(l=8, r=8, t=10, b=8),
            xaxis=dict(
                tickfont=dict(size=11, color=TEXTO_OSCURO, family='Arial'),
                fixedrange=True,
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

        # Notas debajo del gráfico
        notas = []
        if n_no_inf > 0:
            notas.append(
                f'⚠ {n_no_inf} ({pct_no_inf:.1f}%) declararon "Otra sustancia" sin especificar'
                .replace('.', ',')
            )
        if n_blanco > 0:
            notas.append(
                f'⚠ {n_blanco} ({pct_blanco:.1f}%) sin dato de sustancia principal'
                .replace('.', ',')
            )
        if notas:
            st.markdown(
                f'<div style="font-size:.72rem;color:#B45309;padding:.15rem .1rem 0 .1rem;'
                f'line-height:1.4;">' + ' &nbsp;·&nbsp; '.join(notas) + '</div>',
                unsafe_allow_html=True
            )
