# -*- coding: utf-8 -*-
"""
Compara los dos caminos de cálculo del sistema sobre los mismos datos.

Los reportes (Word, Excel, PPT) leen el Base Wide que arma `procesar_wide()`.
El panel de la app lee los registros crudos de Supabase y no pasa por el Wide.
Son dos rutas distintas desde la misma fuente, y este script mide en qué se
apartan.

Uso:
    python tools/comparar_panel_wide.py respaldo_top_registros_AAAA-MM-DD.xlsx

El archivo se obtiene en la app, pestaña Respaldos, botón "Generar archivo
Excel". Trae los registros crudos sin filtrar.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.validacion_top import (  # noqa: E402
    categorias_pais, clasificar_sustancia, normalizar_sexo_valor,
)
from pipeline.wide_top import procesar_wide  # noqa: E402


def _criterio_panel(df):
    """Lo que hace el panel: filtrar por la etiqueta de etapa, texto exacto."""
    return df[df['etapa'].astype(str).str.strip() == 'ingreso']


def _criterio_wide(df):
    """Lo que hace procesar_wide(): el registro más antiguo de cada paciente
    pasa a ser su TOP1, sin mirar cómo el centro etiquetó la etapa."""
    return (df.sort_values(['codigo_paciente', 'fecha_entrevista'])
              .groupby('codigo_paciente', as_index=False).first())


def comparar(ruta):
    crudo = pd.read_excel(ruta)
    wide = procesar_wide(ruta)['wide']

    print(f'registros crudos: {len(crudo)}   filas del Base Wide: {len(wide)}\n')

    # ── 1. Pacientes que cada camino cuenta ──────────────────────────────────
    print('PACIENTES POR PAÍS')
    print(f"{'país':<20}{'panel':>8}{'wide':>8}{'dif':>8}")
    print('-' * 44)
    tp = tw = 0
    for pais in sorted(crudo['pais'].dropna().unique()):
        sub = crudo[crudo['pais'] == pais]
        a, b = len(_criterio_panel(sub)), len(_criterio_wide(sub))
        tp, tw = tp + a, tw + b
        print(f'{pais:<20}{a:>8}{b:>8}{b - a:>+8}')
    print('-' * 44)
    print(f"{'TOTAL':<20}{tp:>8}{tw:>8}{tw - tp:>+8}\n")

    # ── 2. De dónde sale la diferencia ───────────────────────────────────────
    etapas = crudo.groupby(['pais', 'centro', 'codigo_paciente'])['etapa'] \
                  .apply(lambda s: set(s.astype(str).str.strip()))
    sin_ingreso = etapas[~etapas.apply(lambda s: 'ingreso' in s)]
    print(f'PACIENTES SIN NINGÚN REGISTRO CON etapa=ingreso: {len(sin_ingreso)}')
    print('El Wide los cuenta, el panel no. Sus etapas son:\n')
    print(sin_ingreso.apply(lambda s: ' + '.join(sorted(s))).value_counts().to_string())
    print()

    # ── 3. Qué tanto mueve los porcentajes publicados ────────────────────────
    print('SUSTANCIA PRINCIPAL · porcentaje según cada criterio')
    for pais in sorted(crudo['pais'].dropna().unique()):
        sub = crudo[crudo['pais'] == pais]
        a, b = _criterio_panel(sub), _criterio_wide(sub)
        if len(a) < 10:
            continue
        ca = a['sustancia_principal'].apply(lambda v: clasificar_sustancia(v, pais))
        cb = b['sustancia_principal'].apply(lambda v: clasificar_sustancia(v, pais))
        na, nb = max(ca.notna().sum(), 1), max(cb.notna().sum(), 1)
        print(f'\n  {pais}  (panel N={len(a)}, wide N={len(b)})')
        for cat in categorias_pais(pais):
            pa, pb = (ca == cat).sum() / na * 100, (cb == cat).sum() / nb * 100
            marca = '  <--' if abs(pb - pa) >= 2 else ''
            print(f'    {cat:<18}{pa:>7.1f}%{pb:>8.1f}%{pb - pa:>+8.1f}{marca}')

    # ── 4. Sexo, que ya produjo el peor error del sistema ────────────────────
    print('\n\nSEXO · distribución según cada criterio')
    for pais in sorted(crudo['pais'].dropna().unique()):
        sub = crudo[crudo['pais'] == pais]
        a, b = _criterio_panel(sub), _criterio_wide(sub)
        if len(a) < 10:
            continue
        sa = a['sexo'].apply(normalizar_sexo_valor)
        sb = b['sexo'].apply(normalizar_sexo_valor)
        fa = (sa == 'M').sum() / max(sa.notna().sum(), 1) * 100
        fb = (sb == 'M').sum() / max(sb.notna().sum(), 1) * 100
        print(f'  {pais:<20} mujeres: panel {fa:>5.1f}%   wide {fb:>5.1f}%   {fb - fa:>+5.1f}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    comparar(sys.argv[1])
