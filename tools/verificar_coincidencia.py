# -*- coding: utf-8 -*-
"""
Comprueba que el panel y los reportes den los mismos números.

Los reportes leen el Base Wide que arma `procesar_wide()`; el panel lee los
registros crudos de Supabase. Este script corre los dos caminos sobre el mismo
archivo y compara indicador por indicador. Si algo no coincide, lo nombra.

Uso:
    python tools/verificar_coincidencia.py respaldo_top_registros_AAAA-MM-DD.xlsx
"""
import os
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.validacion_top import (  # noqa: E402
    categorias_pais, clasificar_sustancia, columna_de_sustancia, detectar_pais,
    dias_validos_mes, edad_valida, etiqueta_sustancia, lineas_base,
    normalizar_sexo_valor,
)
from pipeline.wide_top import procesar_wide  # noqa: E402

TOLERANCIA = 0.05


def _col(df, base):
    """La columna del Wide equivalente a una del crudo."""
    for c in df.columns:
        if c == f'{base}_TOP1':
            return c
    return None


def _indicadores_panel(crudo):
    lb = lineas_base(crudo)
    if lb.empty:
        return None
    pais = detectar_pais(lb)
    cat = lb['sustancia_principal'].apply(lambda v: clasificar_sustancia(v, pais))
    nv = int(cat.notna().sum())
    ind = {'N': len(lb), 'N válido sustancia': nv}
    for c in categorias_pais(pais):
        ind[f'% {etiqueta_sustancia(c, pais)}'] = round((cat == c).sum() / nv * 100, 1) if nv else 0.0
    sexo = lb['sexo'].apply(normalizar_sexo_valor)
    ind['% mujeres'] = round((sexo == 'M').sum() / max(sexo.notna().sum(), 1) * 100, 1)
    for c in categorias_pais(pais):
        col = columna_de_sustancia(c, lb.columns)
        sub = dias_validos_mes(lb.loc[cat == c, col]).dropna() if col else pd.Series(dtype=float)
        ind[f'días {etiqueta_sustancia(c, pais)}'] = round(float(sub.mean()), 1) if len(sub) else None
    return pais, ind


def _indicadores_reportes(ruta):
    wide = procesar_wide(ruta)['wide']
    if wide.empty:
        return None
    pais = detectar_pais(wide)
    csp = _col(wide, 'sustancia_principal')
    cat = wide[csp].apply(lambda v: clasificar_sustancia(v, pais))
    nv = int(cat.notna().sum())
    ind = {'N': len(wide), 'N válido sustancia': nv}
    for c in categorias_pais(pais):
        ind[f'% {etiqueta_sustancia(c, pais)}'] = round((cat == c).sum() / nv * 100, 1) if nv else 0.0
    sexo = wide[_col(wide, 'sexo')].apply(normalizar_sexo_valor)
    ind['% mujeres'] = round((sexo == 'M').sum() / max(sexo.notna().sum(), 1) * 100, 1)
    for c in categorias_pais(pais):
        col = columna_de_sustancia(c, wide.columns)
        sub = dias_validos_mes(wide.loc[cat == c, col]).dropna() if col else pd.Series(dtype=float)
        ind[f'días {etiqueta_sustancia(c, pais)}'] = round(float(sub.mean()), 1) if len(sub) else None
    return pais, ind


def _iguales(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < TOLERANCIA


def verificar(ruta):
    crudo = pd.read_excel(ruta)
    problemas = []

    for pais in sorted(crudo['pais'].dropna().unique()):
        sub = crudo[crudo['pais'] == pais]
        if len(sub) < 5:
            continue
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        sub.to_excel(tmp.name, index=False)
        tmp.close()

        rp = _indicadores_panel(sub)
        rr = _indicadores_reportes(tmp.name)
        os.unlink(tmp.name)
        if rp is None or rr is None:
            print(f'\n{pais}: sin datos suficientes')
            continue

        _, ip = rp
        _, ir = rr
        print(f'\n{"═" * 58}\n{pais}\n{"═" * 58}')
        print(f'{"indicador":<28}{"panel":>10}{"reportes":>11}   ')
        print('-' * 58)
        for k in ip:
            a, b = ip[k], ir.get(k)
            ok = _iguales(a, b)
            if not ok:
                problemas.append(f'{pais} · {k}: panel {a} contra reportes {b}')
            fa = '—' if a is None else (f'{a:.1f}' if isinstance(a, float) else str(a))
            fb = '—' if b is None else (f'{b:.1f}' if isinstance(b, float) else str(b))
            print(f'{k:<28}{fa:>10}{fb:>11}   {"" if ok else "DIFIERE"}')

    # ── Nivel centro ────────────────────────────────────────────────────────
    # El Wide se procesa una sola vez y se filtra por `centro_TOP1`, en vez de
    # llamar a procesar_wide() por cada centro: son noventa y un centros y el
    # pipeline completo por cada uno tarda minutos. La diferencia entre ambas
    # formas solo aparecería en los cuatro pacientes que figuran en dos centros.
    print(f'\n{"═" * 58}\nPOR CENTRO\n{"═" * 58}')
    tmp_todo = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    crudo.to_excel(tmp_todo.name, index=False)
    tmp_todo.close()
    wide_todo = procesar_wide(tmp_todo.name)['wide']
    os.unlink(tmp_todo.name)

    revisados = 0
    for (pais, cen), sub in crudo.groupby(['pais', 'centro']):
        revisados += 1
        lb = lineas_base(sub)
        w = wide_todo[wide_todo['centro_TOP1'].astype(str).str.strip() == str(cen).strip()]
        if len(lb) != len(w):
            problemas.append(f'{pais} · {cen}: N panel {len(lb)} contra reportes {len(w)}')
            continue
        if not len(lb):
            continue
        p = detectar_pais(lb) or pais
        ca = lb['sustancia_principal'].apply(lambda v: clasificar_sustancia(v, p))
        cb = w['sustancia_principal_TOP1'].apply(lambda v: clasificar_sustancia(v, p))
        na, nb = max(int(ca.notna().sum()), 1), max(int(cb.notna().sum()), 1)
        for c in categorias_pais(p):
            a, b = (ca == c).sum() / na * 100, (cb == c).sum() / nb * 100
            if abs(a - b) >= TOLERANCIA:
                problemas.append(f'{pais} · {cen} · {c}: {a:.1f} contra {b:.1f}')
    print(f'{revisados} centros revisados.')

    print(f'\n{"═" * 58}')
    if problemas:
        print(f'{len(problemas)} indicadores no coinciden:\n')
        for p in problemas:
            print('  ·', p)
        return 1
    print('Todos los indicadores coinciden entre el panel y los reportes.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(verificar(sys.argv[1]))
