"""
pipeline.panel.data — Carga de datos desde Supabase para el Panel de gestión.

Función principal:
  cargar_datos_pais(pais) -> pd.DataFrame

Diseño:
  - Cacheada con st.cache_data(ttl=300): 5 minutos entre golpes reales a Supabase
  - Devuelve DataFrame con columnas snake_case originales de Supabase
  - NO aplica RENAME_MAP: los componentes de Panel usan nombres nativos
  - Levanta excepción si falla; el llamador debe hacer try/except

Uso típico en app.py:
    from pipeline.panel.data import cargar_datos_pais
    try:
        df = cargar_datos_pais(pais_fijo)
    except Exception as e:
        st.error(f'No se pudieron cargar los datos: {e}')
        st.button('Reintentar', on_click=lambda: st.cache_data.clear())
        st.stop()
"""
import streamlit as st
import pandas as pd
import urllib.request
import urllib.parse
import json
from pipeline.sb_paginado import fetch_todo


def _sb_headers():
    """Headers para consultas REST a Supabase. Reutiliza secrets globales."""
    return {
        'apikey':        st.secrets['SUPABASE_KEY'],
        'Authorization': f"Bearer {st.secrets['SUPABASE_KEY']}",
        'Content-Type':  'application/json',
    }


def _sb_url(tabla='top_registros'):
    return f"{st.secrets['SUPABASE_URL']}/rest/v1/{tabla}"


@st.cache_data(ttl=300, show_spinner='Cargando datos del país...')
def cargar_datos_pais(pais):
    """
    Consulta top_registros filtrando por país y devuelve DataFrame.

    Args:
        pais: nombre del país tal como está en la columna 'pais' de Supabase
              (ej: 'Perú', 'Ecuador', 'México', 'México CIJ', 'El Salvador')

    Returns:
        pd.DataFrame con columnas snake_case de Supabase.
        Vacío si no hay registros para ese país.

    Raises:
        urllib.error.URLError si Supabase no responde
        KeyError si faltan credenciales en Streamlit Secrets
        Exception genérica en otros errores de red o parsing
    """
    url = _sb_url() + '?select=*&order=fecha_entrevista.asc,id.asc'
    url += f"&pais=eq.{urllib.parse.quote(pais)}"

    registros = fetch_todo(url, _sb_headers())

    if not registros:
        return pd.DataFrame()

    return pd.DataFrame(registros)


def invalidar_cache_pais():
    """Fuerza limpieza del cache. Se llama desde botón 'Actualizar datos'."""
    cargar_datos_pais.clear()
