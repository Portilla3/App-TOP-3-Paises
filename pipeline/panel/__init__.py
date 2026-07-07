"""
pipeline.panel — Componentes del Panel de gestión de QALAT App2

Cada módulo expone una función `render(df, pais, centro_id=None)` que:
  - Recibe un DataFrame ya filtrado por país (ver data.cargar_datos_pais)
  - Si centro_id viene con valor, filtra al centro y muestra su vista
  - Si centro_id es None, muestra la vista agregada del país
  - Pinta directo sobre st.* del contexto de Streamlit

Convenciones:
  - Nombres de columnas en snake_case (formato Supabase crudo)
  - Los componentes NO consultan Supabase, solo pintan
  - La consulta y el caché viven exclusivamente en data.py
"""
