-- sql/permisos_top_registros.sql
--
-- La base de pacientes no se lee ni se modifica con la llave pública.
-- Ver DECISIONES.md. Aplicado el 2026-10-31 como migración
-- `cerrar_lectura_publica_top`.
--
-- Antes: el rol anon, que es la llave pública escrita en los formularios, podía
-- leer y modificar todos los registros de top_registros, de todos los países.
-- Después: anon solo agrega registros, que es lo único que hacen los formularios
-- de captura. La app lee y escribe con la llave secreta, desde el servidor.

-- Respaldo de las políticas y permisos que había, para poder volver atrás.
CREATE TABLE IF NOT EXISTS public.backup_permisos_top_20261031 AS
SELECT 'politica'::text AS tipo, polname::text AS nombre, polcmd::text AS accion,
       pg_get_expr(polqual, polrelid) AS usando,
       pg_get_expr(polwithcheck, polrelid) AS chequeo,
       polroles::regrole[]::text AS roles
  FROM pg_policy
 WHERE polrelid = 'public.top_registros'::regclass
UNION ALL
SELECT 'permiso', grantee::text, privilege_type::text, NULL, NULL, NULL
  FROM information_schema.role_table_grants
 WHERE table_schema = 'public' AND table_name = 'top_registros'
   AND grantee IN ('anon', 'authenticated');
ALTER TABLE public.backup_permisos_top_20261031 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.backup_permisos_top_20261031 FROM anon, authenticated;

-- Se quitan las dos políticas que abrían la lectura y la modificación.
DROP POLICY IF EXISTS select_publico_v2 ON public.top_registros;
DROP POLICY IF EXISTS permitir_update_correccion ON public.top_registros;

-- El rol público queda solo con el permiso de agregar.
REVOKE ALL ON public.top_registros FROM anon, authenticated;
GRANT INSERT ON public.top_registros TO anon;

-- Para volver atrás, solo si algo se rompe:
--   GRANT SELECT, UPDATE ON public.top_registros TO anon;
--   CREATE POLICY select_publico_v2 ON public.top_registros
--     FOR SELECT TO anon USING (true);
--   CREATE POLICY permitir_update_correccion ON public.top_registros
--     FOR UPDATE TO anon USING (true) WITH CHECK (true);
