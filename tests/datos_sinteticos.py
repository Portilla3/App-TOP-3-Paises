# -*- coding: utf-8 -*-
"""
Base TOP sintética, con el esquema de `top_registros` en Supabase.

La usa la prueba de humo de los reportes (`test_reportes.py`). Los pacientes
son inventados: códigos, fechas y respuestas salen de un generador con semilla
fija, así que la base es siempre la misma y no contiene datos de nadie.

Cada país llena solo las sustancias que ofrece su formulario
(`CATEGORIAS_POR_PAIS`), como en la base real.
"""
import ast
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

from pipeline.validacion_top import CATEGORIAS_POR_PAIS, OTRA_SUSTANCIA

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PREFIJO_COLUMNA = {
    'Alcohol': 'alcohol', 'Marihuana': 'marihuana', 'Pasta Base': 'pastabase',
    'Cocaína': 'cocaina', 'Crack': 'crack', 'Metanfetamina': 'metanfetamina',
    'Heroína': 'heroina', 'Sedantes': 'sedantes', OTRA_SUSTANCIA: 'otra_sust',
}
TODAS = list(PREFIJO_COLUMNA.values())
LETRAS = 'ABCDEFGHIJLMNOPRSTUV'


def rename_map():
    """El RENAME_MAP de app.py, leído sin ejecutar la app."""
    with open(os.path.join(RAIZ, 'app.py'), encoding='utf-8') as fh:
        arbol = ast.parse(fh.read())
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and any(
                getattr(t, 'id', None) == 'RENAME_MAP' for t in nodo.targets):
            return ast.literal_eval(nodo.value)
    raise LookupError('app.py no define RENAME_MAP')


def _semanas(rng, maximo):
    s = [int(x) for x in rng.integers(0, maximo + 1, size=4)]
    return s, sum(s)


def _fila(rng, pais, centro, codigo, nacimiento, sexo, fecha, etapa, ident, principal,
          solo_alcohol=False):
    f = {
        'id': ident, 'created_at': f'{fecha.isoformat()}T12:00:00+00:00',
        'pais': pais, 'centro': centro, 'codigo_paciente': codigo,
        'fecha_nacimiento': nacimiento.isoformat(), 'nombre_entrevistador': 'Prueba',
        'fecha_entrevista': fecha.isoformat(), 'sexo': sexo, 'etapa': etapa,
        'sustancia_principal': principal,
    }
    del_pais = {PREFIJO_COLUMNA[c] for c in CATEGORIAS_POR_PAIS[pais]}
    for pref in TODAS:
        if pref not in del_pais:
            continue
        # La sustancia principal se consume más; las demás casi nunca.
        maximo = 7 if PREFIJO_COLUMNA.get(principal) == pref else (0 if solo_alcohol else 1)
        s, total = _semanas(rng, maximo)
        f[f'{pref}_s4'], f[f'{pref}_s3'], f[f'{pref}_s2'], f[f'{pref}_s1'] = s
        f[f'{pref}_total'] = total
        f[f'{pref}_prom'] = round(float(rng.uniform(1, 8)), 1) if total else None
    if principal == OTRA_SUSTANCIA:
        f['otra_sust_nombre'], f['otra_sust_unidad'] = 'Tusi', 'Gramos/día'
    for c in ('hurto', 'robo', 'venta_droga', 'rina_pelea'):
        f[c] = 'S' if rng.random() < 0.2 else 'N'
    s, total = _semanas(rng, 1)
    f['vif_s4'], f['vif_s3'], f['vif_s2'], f['vif_s1'], f['vif_total'] = *s, total
    for c in ('salud_psicologica', 'salud_fisica', 'calidad_vida'):
        f[c] = int(rng.integers(0, 21))
    for pref in ('dias_trabajo', 'dias_educacion'):
        s, total = _semanas(rng, 5)
        f[f'{pref}_s4'], f[f'{pref}_s3'], f[f'{pref}_s2'], f[f'{pref}_s1'] = s
        f[f'{pref}_total'] = total
    f['trabajo_na'], f['educacion_na'] = False, False
    f['vivienda_estable'] = 'S' if rng.random() < 0.8 else 'N'
    f['vivienda_basica'] = 'S' if rng.random() < 0.9 else 'N'
    return f


def base_sintetica(pais, n_pacientes=40, centros=('C01', 'C02'),
                   con_seguimiento=True, hoy=date(2026, 10, 27), semilla=0,
                   etapa_ingreso='ingreso', solo_alcohol=False):
    """
    DataFrame con el esquema de Supabase. Cada paciente tiene su TOP de ingreso;
    con `con_seguimiento`, la mitad tiene además un TOP en tratamiento a los
    90 días y algunos un egreso. La sustancia principal se reparte entre las
    categorías del país, con algunos "Tusi" (Otra sustancia) y algunos vacíos.

    `etapa_ingreso='en_tratamiento'` arma un centro sin ningún TOP de ingreso, y
    `solo_alcohol=True` uno donde nadie consume otra cosa: las dos condiciones
    del incidente del 2026-09-09.
    """
    rng = np.random.default_rng(semilla)
    categorias = CATEGORIAS_POR_PAIS[pais]
    filas, ident = [], 1
    for i in range(n_pacientes):
        nacimiento = date(1960 + int(rng.integers(0, 45)), int(rng.integers(1, 13)),
                          int(rng.integers(1, 29)))
        codigo = (''.join(rng.choice(list(LETRAS), 4))
                  + nacimiento.strftime('%d%m%Y'))
        sexo = ['H', 'H', 'M', 'O'][i % 4]
        centro = centros[i % len(centros)]
        if solo_alcohol:
            principal = 'Alcohol'
        elif i % 9 == 8:
            principal = None
        else:
            principal = categorias[i % len(categorias)]
        texto_principal = 'Tusi' if principal == OTRA_SUSTANCIA else principal

        ingreso = hoy - timedelta(days=int(rng.integers(100, 300)))
        filas.append(_fila(rng, pais, centro, codigo, nacimiento, sexo, ingreso,
                           etapa_ingreso, ident, principal, solo_alcohol))
        filas[-1]['sustancia_principal'] = texto_principal
        ident += 1
        if con_seguimiento and i % 2 == 0:
            filas.append(_fila(rng, pais, centro, codigo, nacimiento, sexo,
                               ingreso + timedelta(days=90), 'en_tratamiento',
                               ident, principal, solo_alcohol))
            filas[-1]['sustancia_principal'] = texto_principal
            ident += 1
        if con_seguimiento and i % 6 == 0:
            filas.append(_fila(rng, pais, centro, codigo, nacimiento, sexo,
                               ingreso + timedelta(days=95), 'egreso', ident, principal,
                               solo_alcohol))
            filas[-1]['sustancia_principal'] = texto_principal
            ident += 1
    return pd.DataFrame(filas)


def excel_bruto(df, ruta):
    """Lo que hace app.py antes de procesar_wide(): renombrar y guardar."""
    mapa = rename_map()
    df.rename(columns={k: v for k, v in mapa.items() if k in df.columns}).to_excel(ruta, index=False)
    return ruta
