-- sql/permisos_publicos.sql
--
-- El rol público de Supabase (anon, la llave escrita en los formularios) y el rol
-- authenticated quedan solo con lo que se usa. Ver DECISIONES.md, "El rol público
-- solo tiene lo que usa". Aplicado el 2026-11-01 como migración
-- `permisos_publicos_minimos`.
--
-- Lo que queda:
--   * anon puede agregar en top_registros (formularios TOP) y en
--     inscripciones_laboratorio (formulario de inscripción al laboratorio).
--   * irt_registros no se toca todavía: el formulario IRT de Panamá y la app IRT
--     la usan con una llave que no se pudo verificar. Está vacía.
-- Todo lo demás (leer, modificar, vaciar tablas, crear disparadores, ejecutar las
-- funciones de ingreso de centros y de claves) queda solo para la llave secreta
-- de la app, que es la que ya las usa.

-- Respaldo de los permisos que había, para poder volver atrás.
CREATE TABLE IF NOT EXISTS public.backup_permisos_publicos_20261101 AS
SELECT 'tabla'::text AS tipo, table_name::text AS objeto, grantee::text AS rol,
       privilege_type::text AS permiso
  FROM information_schema.role_table_grants
 WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')
UNION ALL
SELECT 'funcion', p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')', r.rolname, 'EXECUTE'
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
  CROSS JOIN (VALUES ('anon'), ('authenticated')) AS r(rolname)
 WHERE n.nspname = 'public' AND has_function_privilege(r.rolname, p.oid, 'EXECUTE');
ALTER TABLE public.backup_permisos_publicos_20261101 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.backup_permisos_publicos_20261101 FROM anon, authenticated;

-- Tablas: se quita todo al rol público, salvo irt_registros, y se devuelve solo lo que se usa.
DO $$
DECLARE t text;
BEGIN
    FOR t IN SELECT tablename FROM pg_tables
              WHERE schemaname = 'public' AND tablename <> 'irt_registros' LOOP
        EXECUTE format('REVOKE ALL ON public.%I FROM anon, authenticated', t);
    END LOOP;
END $$;
GRANT INSERT ON public.top_registros TO anon;
GRANT INSERT ON public.inscripciones_laboratorio TO anon;

-- Funciones: el ingreso de centros y la administración de claves, solo con la llave secreta.
REVOKE ALL ON FUNCTION public.validar_login_centro(text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.admin_listar_centros(text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.admin_crear_clave_centro(text, text, text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.admin_desactivar_clave_centro(text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.validar_login_centro(text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.admin_listar_centros(text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.admin_crear_clave_centro(text, text, text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.admin_desactivar_clave_centro(text, text, text) TO service_role;

-- Lo que se cree de aquí en adelante nace cerrado para el rol público. Así un
-- `CREATE TABLE ... AS` de respaldo ya no queda expuesto aunque se olvide el REVOKE.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated;

-- Para volver atrás, solo si algo se rompe: los permisos de antes están en
-- backup_permisos_publicos_20261101 (tipo, objeto, rol, permiso). Por ejemplo:
--   GRANT EXECUTE ON FUNCTION public.validar_login_centro(text, text) TO anon, authenticated;
