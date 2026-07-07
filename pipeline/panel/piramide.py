"""
pipeline.panel.piramide — Pirámide sexo × grupo etario al ingreso.

Componente del bloque "Perfil de pacientes al ingreso". Muestra la distribución
demográfica de los pacientes que tienen etapa='ingreso' (solo primera evaluación).

Grupos etarios: 15-19, 20-29, 30-39, 40-49, 50+
Sexos considerados: 'Masculino'/'Femenino' (con normalización de variantes).

Diseño:
  - Barras horizontales
  - Mujeres a la izquierda (valores negativos en el eje), color púrpura
  - Hombres a la derecha (valores positivos), color naranja
  - Leyenda abajo con porcentajes totales por sexo

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion


COLOR_MUJER   = '#7B68EE'   # púrpura suave
COLOR_HOMBRE  = '#F26E4C'   # naranja
TEXTO_OSCURO  = '#1F3864'

GRUPOS_ETARIOS = ['15-19', '20-29', '30-39', '40-49', '50+']


def _clasificar_edad(edad):
    """Devuelve el grupo etario para una edad numérica."""
    if pd.isna(edad):
        return None
    e = int(edad)
    if e < 15:  return None    # menores de 15 no entran al análisis
    if e < 20:  return '15-19'
    if e < 30:  return '20-29'
    if e < 40:  return '30-39'
    if e < 50:  return '40-49'
    return '50+'


def _normalizar_sexo(v):
    """Normaliza variantes de sexo a 'M', 'F' o None."""
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    if not s:
        return None
    if s.startswith('m'):  # Masculino, Male, M, Hombre → M
        # Distinguir Masculino de Mujer
        if s.startswith('muj') or s.startswith('mujer') or s == 'm-mujer':
            return 'F'
        return 'M'
    if s.startswith('h'):  # Hombre → M
        return 'M'
    if s.startswith('f'):  # Femenino, F, Female → F
        return 'F'
    return None


def _calcular_piramide(df, hoy=None):
    """
    Filtra a etapa=ingreso y calcula conteo por (grupo_etario, sexo).

    Returns:
        dict con claves:
            grupos: lista de grupos etarios en orden
            mujeres: lista de conteos por grupo (M/F)
            hombres: lista de conteos por grupo
            total_m, total_h, pct_m, pct_h
    """
    if hoy is None:
        hoy = pd.Timestamp.now().normalize()

    vacio = {
        'grupos': GRUPOS_ETARIOS,
        'mujeres': [0] * len(GRUPOS_ETARIOS),
        'hombres': [0] * len(GRUPOS_ETARIOS),
        'total_m': 0, 'total_h': 0, 'pct_m': 0.0, 'pct_h': 0.0,
    }

    cols_req = {'etapa', 'sexo', 'fecha_nacimiento'}
    if df is None or df.empty or not cols_req.issubset(df.columns):
        return vacio

    tmp = df.copy()
    tmp['etapa'] = tmp['etapa'].fillna('').astype(str)
    tmp = tmp[tmp['etapa'] == 'ingreso']
    if tmp.empty:
        return vacio

    tmp['fecha_nacimiento'] = pd.to_datetime(tmp['fecha_nacimiento'], errors='coerce')
    tmp['edad']  = ((hoy - tmp['fecha_nacimiento']).dt.days / 365.25).round().astype('Int64')
    tmp['grupo'] = tmp['edad'].apply(_clasificar_edad)
    tmp['sexo_n'] = tmp['sexo'].apply(_normalizar_sexo)
    tmp = tmp[tmp['grupo'].notna() & tmp['sexo_n'].notna()]

    if tmp.empty:
        return vacio

    conteo = tmp.groupby(['grupo', 'sexo_n']).size().unstack(fill_value=0)
    conteo = conteo.reindex(GRUPOS_ETARIOS, fill_value=0)
    if 'M' not in conteo.columns:
        conteo['M'] = 0
    if 'F' not in conteo.columns:
        conteo['F'] = 0

    total_masculino = int(conteo['M'].sum())
    total_femenino  = int(conteo['F'].sum())
    total_grupo     = total_masculino + total_femenino

    return {
        'grupos':  GRUPOS_ETARIOS,
        'mujeres': conteo['F'].tolist(),
        'hombres': conteo['M'].tolist(),
        'total_m': total_femenino,      # % mujeres
        'total_h': total_masculino,     # % hombres
        'pct_m':   (total_femenino  / total_grupo * 100) if total_grupo > 0 else 0.0,
        'pct_h':   (total_masculino / total_grupo * 100) if total_grupo > 0 else 0.0,
    }


def render(df, pais, centro_id=None):
    """
    Pinta la pirámide de sexo × grupo etario al ingreso.

    Args:
        df: DataFrame del país
        pais: nombre del país (para contexto)
        centro_id: opcional; si viene con valor, filtra al centro antes de calcular
    """
    with st.container(border=True):
        st.markdown(
            titulo_seccion('👥', 'Pirámide sexo por grupo etario',
                           'perfil demográfico al ingreso'),
            unsafe_allow_html=True
        )

        # Filtrado opcional por centro
        if centro_id and 'centro' in df.columns:
            df_local = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()
        else:
            df_local = df

        p = _calcular_piramide(df_local)

        if sum(p['mujeres']) + sum(p['hombres']) == 0:
            st.info('ℹ Aún no hay datos suficientes de sexo y edad al ingreso.')
            return

        # Convertir mujeres a negativos para que queden a la izquierda
        mujeres_neg = [-v for v in p['mujeres']]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=p['grupos'],
            x=mujeres_neg,
            orientation='h',
            name=f'Mujeres ({p["pct_m"]:.0f}%)',
            marker=dict(color=COLOR_MUJER, line=dict(width=0)),
            hovertemplate='<b>%{y}</b><br>Mujeres: %{customdata}<extra></extra>',
            customdata=p['mujeres'],
            text=[str(v) if v > 0 else '' for v in p['mujeres']],
            textposition='outside',
            textfont=dict(color=TEXTO_OSCURO, size=11, family='Arial'),
        ))
        fig.add_trace(go.Bar(
            y=p['grupos'],
            x=p['hombres'],
            orientation='h',
            name=f'Hombres ({p["pct_h"]:.0f}%)',
            marker=dict(color=COLOR_HOMBRE, line=dict(width=0)),
            hovertemplate='<b>%{y}</b><br>Hombres: %{x}<extra></extra>',
            text=[str(v) if v > 0 else '' for v in p['hombres']],
            textposition='outside',
            textfont=dict(color=TEXTO_OSCURO, size=11, family='Arial'),
        ))

        max_abs = max(max(p['mujeres'] or [0]), max(p['hombres'] or [0]))
        rango = max_abs * 1.25 if max_abs > 0 else 1

        fig.update_layout(
            height=280,
            barmode='overlay',
            bargap=0.15,
            margin=dict(l=10, r=10, t=10, b=40),
            xaxis=dict(
                visible=False,
                range=[-rango, rango],
                fixedrange=True,
            ),
            yaxis=dict(
                tickfont=dict(size=12, color=TEXTO_OSCURO, family='Arial'),
                automargin=True,
                fixedrange=True,
                categoryorder='array',
                categoryarray=GRUPOS_ETARIOS,   # desde 15-19 abajo hasta 50+ arriba
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(
                orientation='h',
                yanchor='top', y=-0.05,
                xanchor='center', x=0.5,
                font=dict(size=11, color=TEXTO_OSCURO),
            ),
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
