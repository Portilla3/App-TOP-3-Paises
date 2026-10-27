-- Función de login de centro.
--
-- Vive en Supabase y se invoca por PostgREST desde app.py. Este archivo existe
-- porque hasta el 2026-10-18 las funciones de la base no estaban versionadas en
-- ningún lado: la única copia era la de producción. Un cambio hecho desde
-- cualquier sesión se perdía sin dejar rastro y sin forma de compararlo.
--
-- Si se modifica en Supabase, hay que actualizar este archivo en el mismo
-- commit. La prueba `tests/test_login_centro.py` verifica que la normalización
-- del código de centro siga acá.
--
-- Historial: `login_centro_insensible_a_mayusculas` (2026-10-18) y
-- `login_centro_texto_pegado` (2026-10-27). Ver DECISIONES.md, "El usuario del
-- login de centro es el código" y "El login tolera el texto pegado".

CREATE OR REPLACE FUNCTION public.validar_login_centro(p_correo text, p_password text)
 RETURNS TABLE(valido boolean, centro text, pais text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'extensions'
AS $function$
DECLARE
    v_centro  text;
    v_pais    text;
    v_entrada text;
    v_codigo  text;
    -- Espacios que deja un copiar y pegar: espacio, tabulación, saltos de
    -- línea, espacio duro y los invisibles que agregan WhatsApp y el correo.
    v_blancos text := E' \t\r\n' || chr(160) || chr(8203) || chr(8288) || chr(65279);
BEGIN
    -- El código de centro no distingue mayúsculas ni espacios de borde.
    v_entrada := upper(trim(coalesce(p_correo, '')));

    -- Si lo escrito no es un código, se busca uno que exista entre sus palabras:
    -- 'SJA🇸🇻  El Sa' entra como SJA y 'Usuario: CJR' como CJR. Solo se aceptan
    -- códigos de centros con clave activa, y la clave se sigue exigiendo.
    IF NOT EXISTS (SELECT 1 FROM centro_credenciales cc
                    WHERE upper(trim(cc.centro)) = v_entrada AND cc.activo) THEN
        SELECT upper(trim(cc.centro)) INTO v_codigo
          FROM regexp_matches(upper(coalesce(p_correo, '')), '[A-Z0-9_]+', 'g')
               WITH ORDINALITY AS palabra(texto, orden)
          JOIN centro_credenciales cc
            ON upper(trim(cc.centro)) = palabra.texto[1] AND cc.activo
         ORDER BY palabra.orden
         LIMIT 1;
        IF v_codigo IS NOT NULL THEN
            v_entrada := v_codigo;
        END IF;
    END IF;

    -- La clave distingue mayúsculas: bcrypt compara exacto y eso no se toca. Si
    -- falla tal cual, se prueba sin los espacios del borde, que es lo que suele
    -- arrastrar una clave copiada. Las claves que genera el sistema no tienen
    -- espacios.
    SELECT cc.centro, cc.pais
      INTO v_centro, v_pais
      FROM centro_credenciales cc
     WHERE upper(trim(cc.centro)) = v_entrada
       AND cc.activo        = TRUE
       AND (cc.password_hash = crypt(p_password, cc.password_hash)
            OR cc.password_hash = crypt(btrim(coalesce(p_password, ''), v_blancos), cc.password_hash))
     LIMIT 1;

    IF v_centro IS NOT NULL THEN
        BEGIN
            INSERT INTO centro_bitacora (centro, pais, accion, realizado_por)
            VALUES (v_centro, v_pais, 'login_exitoso', v_centro);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;

        RETURN QUERY SELECT TRUE, v_centro, v_pais;
    ELSE
        -- En el fallido se guarda lo que la persona escribió, no un centro.
        -- Esa columna es la que permitió medir por qué fallan los intentos.
        BEGIN
            INSERT INTO centro_bitacora (centro, pais, accion, realizado_por)
            VALUES (
                left(coalesce(p_correo, '(vacio)'), 50),
                '(desconocido)',
                'login_fallido',
                'anon'
            );
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END IF;
END;
$function$;
