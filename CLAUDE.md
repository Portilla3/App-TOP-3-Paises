# QALAT · Instrucciones para Claude

QALAT es el sistema de monitoreo de resultados de tratamiento de drogas de
UNODC, con los instrumentos TOP e IRT, en Perú, Ecuador, El Salvador y México,
este último con cuatro instituciones. Rodrigo Portilla es el consultor a cargo y
el único desarrollador.

**Este archivo es la fuente única de las reglas de trabajo.** Lo lee solo
Claude Code al abrir el repositorio, y los chats del proyecto "App 2.0 QALAT"
lo leen desde
`https://raw.githubusercontent.com/Portilla3/App-TOP-3-Paises/main/CLAUDE.md`.
Si una regla cambia, se cambia aquí y en ningún otro lugar. Ver
`QALAT_ARRANQUE_CHAT.md` para el texto corto que va en el proyecto de Claude y
el porqué de cada regla.

---

## La memoria del proyecto está en el repositorio

Fuente de verdad: `https://github.com/Portilla3/App-TOP-3-Paises`, rama `main`,
repositorio público.

| Documento | Qué contiene |
|---|---|
| `DECISIONES.md` | Reglas de cálculo con su fundamento. No se rediscuten. |
| `QALAT_REGLAS_DE_CALCULO.md` | Las mismas reglas, ordenadas por tema |
| `CHANGELOG.md` | Qué cambió en el código y por qué |
| `PENDIENTES.md` | Lo que falta y lo que se decidió no hacer |
| `INCIDENTES.md` | Lo que se rompió en producción, con causa y arreglo |

**Antes de afirmar cualquier cosa sobre reglas de cálculo, incidentes o
pendientes, lee el documento que corresponda.** En un chat sin acceso al
repositorio, usa la copia del knowledge del proyecto y dilo explícitamente.
Si el knowledge y el repositorio se contradicen, manda el repositorio.

## Dónde se escribe cada cosa

- Cambio de código: su línea en `CHANGELOG.md`, en el mismo commit. Si queda
  para después, no se hace.
- Problema que llegó a producción: su entrada en `INCIDENTES.md`, el mismo día.
- Decisión que cierra una discusión: `DECISIONES.md` con su fundamento, y su
  prueba en `tests/`. Una decisión sin prueba se incumple sin que nadie se
  entere.
- Lo que falta o se descartó: `PENDIENTES.md`.

## La carpeta local del proyecto se revisa al empezar y se deja al día

En el computador de Rodrigo, la carpeta
`OneDrive\Documentos\EMCDDA final\C A L I D A D\Acreditación\ONUDD\QALAT\QALAT 2025\App TOP 3.0`
(dentro de su carpeta de usuario) tiene:

- `Operativo`: los documentos que se usan con los países y los centros. No están
  en GitHub; si un cambio los deja viejos, se avisa qué parte y se pregunta antes
  de editarlos.
- `_respaldo_repositorio`: copia de estos documentos del repositorio. Al cerrar
  un cambio se refresca entera y se anota el commit en su `LEEME.txt`.
- `Plataforma_QALAT_caracterizacion.docx`: el informe que describe la
  plataforma. Si un cambio lo deja viejo, se avisa qué sección.
- `_historico` no se edita ni se consulta para trabajar. Solo recibe lo que
  queda superado, anotado en su `LEEME.txt`.

Es regla de Rodrigo desde el 27 de octubre de 2026, para no confundirse.

## Dos accesos distintos, que no hay que confundir

- **Formulario TOP:** el centro elige su código de una lista y carga pacientes.
  No usa clave. La lista vive en el HTML de cada país; en Perú, `index.html`.
  Un centro nuevo que va a cargar TOP se agrega ahí.
  **Los links de los formularios no cambian.** No se cambia el nombre ni la
  ubicación de ningún formulario (`index.html`, `index_ecuador.html`,
  `index_elsalvador.html`, `index_mexico.html`, `index_mexicocij.html`,
  `index_montefenix.html`, `index_mahanaim.html`), no se renombra el
  repositorio y no se toca la configuración de GitHub Pages. Los centros usan
  esos links y no pueden cambiarlos. Se edita el contenido de cada archivo en
  su lugar. Ver DECISIONES.md, "El formulario de Perú se llama `index.html` y
  no se renombra".
- **Plataforma (Streamlit):** el centro entra con código y clave para ver su
  panel y descargar reportes. Las claves viven en `centro_credenciales`. Solo
  tiene sentido para centros que ya tienen datos.

El 18 de octubre se confundieron: a cinco centros nuevos de Perú se les creó
clave de plataforma en vez de agregarlos al formulario, y quedaron sin poder
cargar nada.

## Reglas de trabajo

La numeración no se cambia: otros documentos citan estas reglas por número.

1. Antes de tocar código, correr `python -m pytest tests/ -v -p no:cacheprovider`.
   Si algo ya falla, decirlo antes de seguir.
2. Después de tocar código, correrlas de nuevo. Si se rompió una regla, se
   arregla o se explica por qué la regla cambió.
3. No implementar sin autorización explícita. Confirmar el alcance antes de
   tocar más de un archivo.
4. Verificar contra datos antes de afirmar. La descripción de un problema puede
   estar equivocada, incluida la de Rodrigo.
5. Con el conector de Supabase activo, Claude puede leer por su cuenta.
   **Cualquier modificación requiere permiso explícito de Rodrigo antes de
   ejecutarse.** Sin el conector, entregar el SQL exacto para que Rodrigo lo
   ejecute, indicando si es SQL Editor o Table Editor.
6. Todo UPDATE va con respaldo previo, con un conteo que use la misma condición
   del WHERE, y envuelto en CTE con `RETURNING`. El SQL Editor responde
   "Success. No rows returned" a un UPDATE normal y esa ambigüedad ya provocó
   una doble ejecución.
7. Los respaldos se crean con `ENABLE ROW LEVEL SECURITY` y `REVOKE ALL FROM
   anon, authenticated`. `CREATE TABLE AS` deja la tabla expuesta por PostgREST.
8. El export del SQL Editor de Supabase trunca en 100 filas. Para bajar la tabla
   completa, la app tiene un botón en la pestaña Respaldos.
9. *(Solo chats en la nube.)* El dominio `streamlit.app` no responde desde el
   contenedor de Claude. Los chequeos en vivo los hace Rodrigo desde su
   navegador.
10. Verificar que una app arranca no es verificar que funciona. Los reportes se
    prueban generándolos. Después de subir un cambio de código, reiniciar la app
    TOP desde share.streamlit.io (menú ⋮, Reboot) y comprobar que el cambio se
    ve: el "Updated app!" trae los archivos pero no recarga los módulos de
    `pipeline/`. Ver INCIDENTES.md, 2026-10-30. Antes de reiniciar, las pruebas
    automáticas de GitHub (pestaña Actions) tienen que estar en verde para ese
    commit. Ver DECISIONES.md, "Las versiones se fijan exactas". Subir y
    reiniciar van seguidos, sin dejar pasar tiempo entre uno y otro.
11. *(Solo chats en la nube.)* En el contenedor de Claude, `git push` con el
    token dentro de la URL falla con "unexpected disconnect while reading
    sideband packet". No es el token: el proxy del contenedor hace que el `POST`
    final salga sin credencial y GitHub responde 401. Se resuelve mandando la
    credencial como cabecera explícita:

    ```
    AUTH=$(printf 'x-access-token:%s' "$TOKEN" | base64 -w0)
    git -c http.extraHeader="Authorization: Basic $AUTH" \
        push https://github.com/Portilla3/App-TOP-3-Paises.git HEAD:main
    ```

## Trabajo con Git en el computador de Rodrigo (Claude Code local)

Streamlit Cloud publica lo que llega a `main`. Un error en `main` lo ven los
centros.

- **Nunca commit ni push directo a `main`.** Cada cambio va en su propia rama:
  `fix/...` para arreglos, `feat/...` para funciones nuevas, `docs/...` para
  documentos.
- **Al empezar la sesión:** `git status` y `git fetch`. Si `main` local está
  atrasado respecto de `origin/main`, avisar y hacer `git pull` en `main` antes
  de crear la rama. Rodrigo también trabaja desde chats en la nube, que suben
  directo a GitHub.
- **Flujo de un cambio:** rama, pruebas locales (regla 1 y 2), commit, push de
  la rama, esperar GitHub Actions en verde. Push de una rama que no es `main` no
  publica nada: se puede hacer sin pedir permiso aparte.
- **Juntar con `main` (merge y push de `main`) requiere autorización explícita
  de Rodrigo en esa conversación.** Va seguido del Reboot de la regla 10. No se
  hace si Rodrigo no puede mirar la app después del reinicio.
- **Mensajes de commit:** PowerShell 5.1 corta los mensajes con comillas.
  Escribir el mensaje en un archivo temporal fuera del repo y usar
  `git commit -F <archivo>`.
- **Secretos:** nunca subir claves, tokens ni `secrets.toml`. Los secretos
  viven en Streamlit Cloud. El repositorio es público.
- **Entorno:** Python 3.14 con las versiones exactas de `requirements.txt`, las
  mismas de producción. No actualizar paquetes por cuenta propia.

## Cómo responder

Español neutro, sin modismos argentinos, sin rayas largas. Como asesor y no como
asistente: cuestionar los supuestos, etiquetar cada afirmación con `[Seguro]`,
`[Probable]` o `[Suposición]`, y no ceder sin evidencia nueva. Explicar sin
jerga: Rodrigo es salubrista, no programador. Antes de pedir permiso para un
comando, decir en una línea qué hace y si modifica algo.
