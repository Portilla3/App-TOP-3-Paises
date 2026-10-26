-- Errores graves de registro en la Plataforma, por grupo y por mes de carga.
-- Definición en DECISIONES.md, "Qué es un error grave de registro" (2026-10-26).
-- Se ejecuta en el SQL Editor de Supabase. Solo lee.
--
-- Universo: TOP cargados por los formularios de la Plataforma.
--   * Fuera: las dos migraciones desde JotForm (Perú 19/05/2026 16:22 UTC,
--     El Salvador 05/06/2026 17:07 UTC). Sus errores son de JotForm.
--   * Si un TOP se cargó dos veces, cuenta la última carga.
-- Errores graves:
--   r1  la fecha dentro del código (DDMMAAAA) no coincide con la fecha de nacimiento
--   r2  TOP que no es de ingreso, sin ingreso con su código en ese centro, pero con
--       un ingreso anterior de otro código del mismo centro que parece la misma
--       persona (mismo sexo y misma fecha de nacimiento o parte del código igual).
--       Es una estimación: revisar los casos antes de corregir.
--   r3  fecha de entrevista posterior al día de carga, anterior a 2020 o
--       anterior al nacimiento
-- No son error: las semanas en blanco ni que el primer TOP sea "en tratamiento".

with base as (
  select t.*, upper(trim(codigo_paciente)) cod,
    case when pais = 'México' then 'México IMSS-B'
         when pais in ('México Mahanaim', 'México Monte Fénix') then 'México autónomos'
         else pais end grupo,
    date_trunc('minute', created_at) in ('2026-05-19 16:22:00+00', '2026-06-05 17:07:00+00') migrado,
    row_number() over (partition by upper(trim(codigo_paciente)), centro, fecha_entrevista, etapa
                       order by created_at desc, id desc) rn
  from top_registros t
), u as (select * from base where rn = 1 and not migrado),
ing as (
  select centro, cod, min(fecha_entrevista) f_ing, min(fecha_nacimiento) fn, min(sexo) sexo
  from base where etapa = 'ingreso' group by 1, 2
), f as (
  select u.*,
    to_char(date_trunc('month', created_at at time zone 'America/Lima'), 'YYYY-MM') mes,
    (cod ~ '^[A-ZÁÉÍÓÚÑ]{4}[0-9]{8}$' and fecha_nacimiento is not null and
     substr(cod,9,4)||'-'||substr(cod,7,2)||'-'||substr(cod,5,2) <> to_char(fecha_nacimiento,'YYYY-MM-DD')) r1,
    (etapa <> 'ingreso'
     and not exists (select 1 from ing i where i.centro = u.centro and i.cod = u.cod)
     and exists (select 1 from ing i
                 where i.centro = u.centro and i.cod <> u.cod and i.f_ing <= u.fecha_entrevista and (
                      (i.fn = u.fecha_nacimiento and i.sexo = u.sexo
                       and (left(i.cod,2) = left(u.cod,2) or substr(i.cod,3,2) = substr(u.cod,3,2)))
                   or (left(i.cod,4) = left(u.cod,4) and i.sexo = u.sexo
                       and (substr(i.cod,9,4) = substr(u.cod,9,4) or substr(i.cod,5,4) = substr(u.cod,5,4)))
                   or (right(i.cod,8) = right(u.cod,8) and i.sexo = u.sexo
                       and (left(i.cod,2) = left(u.cod,2) or substr(i.cod,3,2) = substr(u.cod,3,2)))))) r2,
    (fecha_entrevista > (created_at at time zone 'America/Lima')::date
     or fecha_entrevista < '2020-01-01'
     or (fecha_nacimiento is not null and fecha_entrevista <= fecha_nacimiento)) r3
  from u
)
select coalesce(grupo, 'TOTAL') grupo, coalesce(mes, 'todo') mes,
  count(*) top_analizados,
  count(*) filter (where r1) codigo_vs_nacimiento,
  count(*) filter (where r2) seguimiento_otro_codigo,
  count(*) filter (where r3) fecha_imposible,
  count(*) filter (where r1 or r2 or r3) con_algun_error,
  round(100.0 * count(*) filter (where r1 or r2 or r3) / count(*), 1) pct_con_error
from f
group by cube(grupo, mes)
order by grupo nulls last, mes nulls last;
