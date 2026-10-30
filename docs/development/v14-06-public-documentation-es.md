# V14-06 — Presentación pública y documentación final

## Resultado y alcance

README reescrito para que un visitante entienda propósito, operación offline,
primera ejecución y límites antes de auditar contratos. Se mantienen las guías
técnicas, los registros históricos y las identidades de versión. No cambia
ningún módulo de producto, parser, renderer, contrato, dependencia ni test.

Antes: capacidades y detalles de ingeniería, dos diagramas, instalación desde
checkout y auditorías intercaladas. Después: **See it in action**, **Quick Start —
5 minutes**, **What it does / What it does not do**, **Documentation &
verification**; esta última separa operación y auditoría. El recorrido de siete
etapas distingue declaración, observación, identidad revisada, revisión analítica,
baseline explícito, comparación y evidencia visual.

Estado: **listo para inspección del propietario con captura de navegador pendiente**.
No se presenta v1.4.0 como estable publicado ni se crea un enlace de descarga futuro.

## Preflight y evidencia remota

- Raíz: `C:\Users\PC\Desktop\OT-ArchGuard-CLEAN`.
- Rama: `codex/v14-06-final-release-readiness`.
- HEAD inicial: `5c70ae09904687070ecce9374546aff8ae806588`; árbol inicial limpio.
- Distribución/CLI `1.4.0`; motor nativo y alias histórico `1.3.0`; esquema nativo `1`.
- Estable publicado según la documentación aceptada: v1.3.0. Integración en
  `main`, aceptación final, tag y publicación de v1.4 siguen siendo gates aparte.
- El propietario informa Draft PR #24 y seis jobs exitosos para ese HEAD.
  No se consultó GitHub: la directiva prohíbe operaciones remotas. El estado
  remoto actual y su último SHA no se presentan como comprobados de forma
  independiente. Los recibos anteriores de V14-05/V14-06 permanecen intactos.

## Archivos exactos

| Archivo | Cambio |
| --- | --- |
| `README.md` | Nueva portada, cuatro secciones, recorrido, Quick Start, capacidades/límites y navegación |
| `docs/installation.md` | Primer uso estable separado, equivalentes POSIX y selección de assets del nuevo source |
| `docs/images/README.md` | Estado veraz de la captura v1.4, fuente sintética y pasos de captura; procedencia antigua preservada |
| `docs/testing-strategy.md` | Distingue CI comunicada por el propietario de la verificación del nuevo commit |
| `docs/release-notes-1.4.0.md` | Corrige anchor al Quick Start y distingue checkpoint comunicado de la nueva CI pendiente |
| `docs/release-checklist.md` | Actualiza el gate del PR existente y el alcance de checks documentales |
| `docs/development/v14-06-public-documentation-es.md` | Este handoff |
| `tools/public-files.txt` | Entrada exacta de este nuevo documento |
| `MANIFEST.in` | Inclusión explícita de este nuevo documento en sdist |

Sin imágenes nuevas ni cambios a herramientas/tests públicos. Se conservan los
cuatro PNG existentes: uno se muestra en portada; los otros siguen enlazados
desde su procedencia. La discrepancia histórica de la leyenda de forwarding se
conserva en el contexto v1.3; no se anuncia como defecto nuevo de v1.4.

## Demostración y captura pendiente

La herramienta Computer Use detuvo el acceso a Edge porque no pudo determinar
con suficiente certeza la URL actual para aplicar la política. Se dejó de usar;
sin reintentos ni rutas alternativas para capturar. No había screenshot genuino
v1.4 en los assets existentes. El README muestra una exportación real v1.3
claramente identificada, sin enlace roto, imagen ficticia ni placeholder.

Se generó de nuevo el escenario real con instalación regular del wheel `1.4.0`
anterior, cuyos 97 módulos coinciden con el source inicial sin cambios analíticos:

```powershell
.\.venv-v146-wheel\Scripts\python.exe -m tools.historical_explorer_walkthrough --output output/v146-docs/historical-explorer
```

Fixture exacta: `tools.historical_explorer_walkthrough.scenario`, con
`tools.drift_walkthrough.prepare` y sus productores ficticios de paquetes/modelos.
No se importaron capturas de terceros ni datos operativos. Los reviews de fixture
son explícitamente ficticios y no autorizan evidencia real.

Resultado: `status: passed`; normal, incomplete, decoder, unchanged y dense;
repetición byte a byte idéntica, workspace intacto por generación y replay
analítico exitoso. El escenario normal contiene 14 findings: 12 diferencias,
un soporte sin cambios y una abstención. El harness revoca después el baseline
ficticio: la verificación posterior conserva reproducción y devuelve `REVOKED`.
La aprobación registrada al generar no se confunde con la autoridad actual.

Acción exacta del propietario: abrir
`C:\Users\PC\Desktop\OT-ArchGuard-CLEAN\output\v146-docs\historical-explorer\normal\index.html`,
revisar `communications.html`, `coverage.html` y `verification.html`, y capturar
una vista legible con evidencia y advertencias. Registrar navegador/versión,
HTML exacto/hash, viewport, zoom, dimensiones y cualquier recorte o resize.
Seguir la [procedencia y pauta de captura](../images/README.md#v14-historical-explorer-browser-capture--owner-action).
No hay archivo de screenshot nuevo, método de captura exitoso, recorte ni resize
que atribuir a este pase. El HTML no ha recibido una nueva aceptación visual.

## Quick Start verificado

El bloque PowerShell del README se extrae y ejecuta literalmente en una carpeta
nueva, con instalación regular del wheel, extracción del sdist y siete comandos:
crear venv, instalar wheel, `pip check`, `--version`, `tar -xf`, `explore` e
`Invoke-Item`. Todos devuelven 0; `--version` imprime exactamente `1.4.0`.
El report generado es un Architecture Explorer, no un check de todos los intents.

Preflight de comandos: `output/v146-docs/quick-start-precommit.json` y logs 1–7;
salida real:
`C:\Users\PC\Desktop\OT-ArchGuard-CLEAN\output\v146-docs\quick-start-precommit\report\index.html`.
Import regular desde `.venv/Lib/site-packages/otarchguard`; 97 módulos coincidentes.
El primer intento falló antes de instalar por permisos del TEMP del sandbox al
ejecutar ensurepip. Se preservó el fallo, se fijaron TEMP/TMP a un directorio local
y se repitió en una carpeta nueva, sin cambiar los comandos ni el producto.

Para la comprobación desconectada se suministraron `PIP_NO_INDEX=1`,
`PIP_FIND_LINKS` al wheelhouse ya preparado y el hook `OTARCHGUARD_OFFLINE_CHECK=1`
con `PYTHONPATH=tools/offline`, sin agregar `src` a imports. Python local: 3.14.5.
La instalación ordinaria puede descargar dependencias; no se promete que lo haga
offline sin wheelhouse. El hook es una barrera de Python, no una prueba de air gap.
`Invoke-Item` termina correctamente; esto no prueba aceptación visual del browser.
Cinco minutos es una etiqueta aproximada, sin medición garantizada.

El conjunto final se reconstruye tras el commit en
`output/v146-docs/release-assets/`, y el mismo bloque se repite contra esos assets
en `output/v146-docs/quick-start-final/`. Los recibos finales están en
`quick-start-final.json` y `delivery.json`, bajo `output/v146-docs/`.
Los equivalentes Linux/macOS se revisan por sintaxis/contrato; no se afirma una
ejecución nativa local ni una nueva comprobación del estable v1.3.

## Verificación documental y de paquetes

La auditoría local recorre 53 Markdown y 310 referencias locales de los documentos
modificados y sus destinos directos: existencia, anchors, navegación e imágenes,
sin links rotos. El recibo completo queda
en `output/v146-docs/markdown-links.json`; las referencias remotas no se visitan.
El HTML del Quick Start se analiza para verificar links/anchors locales y excluir
scripts o recursos remotos. Los bundles históricos pasan su verificador nativo.
Siete documentos pasan parseo CommonMark con tablas y jerarquía de headings;
15 bloques PowerShell pasan el parser del shell. No se presenta este parseo
como inspección visual de GitHub o del navegador. Recibo: `markup.json`.

Los gates de inventario y archivos se conservan: una entrada explícita adicional,
sin exenciones de docs. Se ejecutan 103 tests enfocados de source/archive integrity,
identidad del candidato, metadata y ensamblaje, con red Python denegada:
103 PASS, cero FAIL/ERROR/SKIP, 38,10 segundos en Windows/Python 3.14.5.
Recibos: `output/v146-docs/focused-tests.xml` y `focused-tests.log`.
Se construyen wheel/sdist y se auditan miembros, bytes, README de metadata,
licencias, entry points y payload de módulos mediante las herramientas existentes.
El resultado final exacto, recuentos, SHA/tree y hashes de assets se guarda fuera
del source en `output/v146-docs/delivery.json` y sus recibos enlazados por ruta.

Tras commit se exige `tools.verify_source_checkout` contra HEAD y
`tools.prepare_release` con `--verify`. El sdist incorpora este documento,
imágenes y ejemplos. Las cuatro entregas anteriores en `output/v146/` no se
sobrescriben: README/metadata, tree, sdist, manifiesto y checksums pueden cambiar
aunque los 97 módulos runtime sean idénticos. No se reutilizan hashes anteriores.

No se repite la matriz analítica completa ni se ejecuta Ruff/mypy: no hay Python
público modificado. No se atribuye al nuevo commit CI heredada ni una suite completa.
Una revisión independiente de solo lectura encontró dos P2 documentales:
expectativa de `--version` con prefijo inexistente y selección de assets antiguos.
Ambos se corrigieron; no informó otro hallazgo semántico en el alcance revisado.

## Precisión y límites preservados

- Sin anuncio de estable v1.4 publicado ni capacidad industrial ilimitada.
- Sin inferir incidente, ejecución/éxito de comandos, sesión, autorización o
  enforcement real desde observaciones o caminos declarados.
- Sin interpretar falta de captura o comparación unsupported como negativo probado.
- Review local no autenticado, propuesta y aprobación distintas, baseline acotado
  y ninguna herencia automática de aprobación entre revisiones.
- Hashes y verificación portable prueban integridad acotada, no autenticidad forense.
- Límites completos, cobertura parcial de corpus y registros históricos accesibles.

## Identidad Git y aceptación del propietario

El commit inicial, la rama y el árbol limpio se registran arriba. El SHA final no
se inserta en un documento que lo definiría circularmente: se registra después
del commit en `output/v146-docs/delivery.json`, junto con estado final del árbol,
inventario exacto, fuentes verificadas y resultados. El mensaje del checkpoint es
`docs: redesign public onboarding and evidence presentation for v1.4`.
Cero push, fetch, modificaciones de PR, merge, tag, publicación o llamadas remotas.

Checklist de inspección:

1. Primera pantalla de README y visual v1.3 correctamente etiquetado; capturar
   el HTML v1.4 indicado si se desea completar el nuevo asset.
2. Quick Start y su salida local final
   `C:\Users\PC\Desktop\OT-ArchGuard-CLEAN\output\v146-docs\quick-start-final\report\index.html`.
3. Tabla de capacidades, límites y recorrido con reviews explícitos.
4. Navegación de usuario/auditor y wording estable/candidato.
5. `output/v146-docs/delivery.json`, assets nuevos y checksums ligados al SHA final.

Recomendación: inspección local del propietario; tras aceptación, push autorizado
a V14-06 y seis jobs de CI para el SHA exacto. Después, integración ordenada de la
pila de PRs y aceptación del nuevo `main`, reconstrucción final y publicación
autorizada aparte. No se ha publicado v1.4.0. Detener aquí para inspección.
