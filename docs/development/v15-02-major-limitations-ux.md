# V15-02 — Lista vertical de Major limitations

**DEFERRED_TO_V15-02** — investigación del 3 de noviembre de 2026, a partir de la
observación del propietario durante la aceptación de V15-01. Base limpia:
`8ebe744a9d12f7c76f153ca2b6a509e08e36a5c5`, rama
`codex/v15-01-product-consolidation-foundation`.

No se implementa la corrección visual en V15-01: requiere modificar runtime
congelado y aprobar una identidad de presentación nueva. Este documento prepara
esa implementación sin cambiar contratos, informes anteriores ni sus manifiestos.
Los registros originales de V15-01 conservan su significado histórico.

## Causa comprobada y alcance

`drift/explorer_render.py::_Renderer.overview` (línea 610) genera el encabezado
`Major limitations` y llama a `_value(report["limitations"])`. `_value` delega en
`explorer_html.structured_value`, que ya emite **un `<ul class="evidence-values">`
y un `<li>` por afirmación**, dentro de `.compact-evidence`.

La causa horizontal es el CSS de `explorer_html.COMPACT_CSS` (líneas 69–71),
incluido mediante `SEMANTIC_CSS` en el `style.css` histórico:

```css
.compact-evidence .evidence-values{display:flex;flex-wrap:wrap;gap:.1rem 1.4rem;
padding-left:1.1rem;margin:.2rem 0;list-style:disc}
.compact-evidence .evidence-values>li{margin:0;max-width:100%;overflow-wrap:anywhere}
```

Flex permite varios elementos por fila. Las viñetas existentes proceden de
listas HTML reales; no son separadores insertados manualmente. También se aplica
a `Limitations for this finding` y a otras listas escalares históricas. El helper
compartido sirve a Architecture Explorer, captura, reportes nativos y Review
Explorer. Cambiar globalmente esa regla ampliaría el alcance de esta corrección.

## Dependencia que impide modificarlo ahora

- [Contrato V14-06](v14-06-contracts.md): sólo admite la sustitución histórica
  `1.4.0.dev1` → `1.4.0` en `__init__.py`; los otros 96 módulos conservan sus bytes.
- `tools/verify_legacy_candidate.py::_candidate_module_hashes` y
  `_check_candidate_source` derivan los **97 hashes** de la referencia inmutable
  `117318393ead604a023a24bad7d53eb429faa13f`. Una modificación CSS también cambia
  un módulo protegido. Los tests `test_v146_version_gate.py` ejercitan el rechazo.
- `drift/explorer.py::_renderer_identity` liga cinco módulos instalados:
  `drift/explorer.py`, `drift/explorer_render.py`, `drift/explorer_bundle.py`,
  `explorer_html.py` y `capture/display.py`. Alterar renderer o CSS compartido
  cambia `renderer_sha256`; la reproducción comprueba además HTML/CSS exactos.
- La revisión vigente es `1.4.0-historical-explorer.2`.
  `drift/explorer_bundle.py::_identity` sólo admite revisiones `.1` y `.2`.
  Adoptar una revisión nueva requiere una transición explícita del verificador
  portable y sus pruebas; incrementar sólo el literal no basta.

La investigación verificó el pin actual y demostró el rechazo de un hash de
renderer hipotéticamente modificado **sólo en memoria**. No se parchearon módulos,
instalaciones, baselines ni comprobaciones para obtener un resultado favorable.
Un override externo o editar `style.css` de un bundle existente tampoco es una
corrección válida: rompe sus hashes y la reproducción determinista.

## Implementación propuesta, pendiente de autorización V15-02

1. Aprobar un contrato acotado de transición de fuente/presentación, conservando
   las referencias anteriores y los oráculos analíticos nativos. Definir la nueva
   revisión de renderer y su aceptación portable sin reutilizar falsamente `.2`.
2. En `drift/explorer_render.py` usar una clase exclusiva para esta sección,
   sin modificar `_value`, `structured_value` ni el CSS compartido:

   ```python
   body += '<h2>Major limitations</h2><ul class="major-limitations">'
   body += "".join("<li>" + escape(item) + "</li>" for item in self.report["limitations"])
   body += "</ul>"
   ```

   Añadir al CSS histórico, con la tipografía heredada:

   ```css
   .major-limitations{display:block;list-style:disc outside;padding-left:1.4rem;
   margin:.65rem 0;min-width:0;max-width:100%;white-space:normal}
   .major-limitations>li{display:list-item;margin:.5rem 0;
   white-space:normal;overflow-wrap:anywhere;word-break:normal}
   ```

3. Actualizar la revisión y la política de versiones soportadas en
   `drift/explorer_bundle.py` bajo el contrato aprobado. Generar únicamente
   bundles nuevos; conservar los antiguos junto con su renderer compatible.
4. No alterar `drift/contract.py::LIMITATIONS`, drift JSON, IDs, navegación,
   hallazgos, evidencias o aprobaciones. El inventario de productor analítico en
   `evidence/revisions.py` no incluye estos renderers: un cambio sólo de renderer
   no implica por sí mismo cambiar analysis IDs. Si una transición adicional de
   distribución modifica `__init__.py`, revisar separadamente esa frontera de
   productor; no rehashar revisiones antiguas ni transferir aprobaciones.

Es un plan, no código aplicado ni una revisión de renderer ya aceptada.

## Contenido y pruebas de aceptación pendientes

La referencia ficticia contiene estas siete afirmaciones, en este orden exacto:

1. Differences describe selected finite evidence and declared models, not deployment changes.
2. Unobserved traffic is not proven absent, blocked or evidence of an offline device.
3. Raw addresses and matching labels do not establish physical device or sensor identity.
4. Packet counts are raw counts, not rates or normalized activity trends.
5. Capture authenticity, clock synchronization and reviewer authority are unattested.
6. Protocol headers do not prove command execution, application success or authorization.
7. No incident, attribution, industrial safety or risk severity is determined.

Añadir tests independientes en `test_historical_explorer_render.py` y
`test_historical_explorer_layout.py`: exactamente un UL de la sección y siete LI;
texto y orden idénticos al oráculo literal y al JSON canónico; sin pérdidas ni
duplicados; layout block/list-item, marcadores e indentación; wrapping de texto
largo; sin flex/grid/inline horizontal, pseudo-viñetas, JavaScript ni recursos
externos. No afirmar ausencia de overflow real sólo por inspeccionar reglas CSS.
Comprobar que sólo cambian el fragmento de esta sección y su CSS; conservar
hrefs/anchors, demás páginas, evidencia, JSON analítico y estado de aprobación.
Agregar pruebas de la nueva revisión de renderer, identidad y verificación
portable/reproducción, manteniendo el rechazo de identidades desconocidas.

## Evidencia de esta investigación

Se generó un **bundle nuevo con el diseño actual**, a partir de fuentes ficticias
retenidas, sin modificar el workspace, reporte JSON ni bundle previo:

`output/v15-01/major-limitations-2026-11-03/site/index.html`

Publicación `PUBLISHED_SOURCE_REPRODUCED`, verificación portable y reproducción
analítica correctas; 39 páginas HTML, cero enlaces rotos. El probe HTML confirma
un UL, siete LI y texto/orden exactos. No es un reporte corregido ni un preview de
Option A. El estado ficticio revocado se conserva; no se registró ninguna revisión
o aprobación nueva. Recibos y comandos locales:
`output/v15-01/major-limitations-2026-11-03/{investigation,verification}.json`.

Comprobaciones ejecutadas en Windows/CPython 3.12.14 con el wheel regular de
V15-01 y operaciones Python de red denegadas:

| Comprobación | Resultado |
|---|---|
| Tests existentes de render, layout, bundles, semántica compartida y freeze | 196 PASS / 0 FAIL / 0 ERROR / 1 SKIP, de 197 casos; junction no permitida en el sandbox |
| Ruff lint / formato / mypy estricto | PASS en las tres comprobaciones |
| Verificador inmutable completo | PASS; 124 artefactos, 110 analíticos, 13 apéndices HTML JSON y 54 archivos de tests históricos comprobados |
| Runtime y fuentes anteriores | Los 97 módulos coinciden con el pin; workspace, reporte y bundle previo conservan sus hashes |

No se añaden tests de una corrección diferida ni se presenta un test verde de
contenido como prueba de apilamiento vertical. No se repite la suite completa.
Los cambios de esta entrega se limitan a este seguimiento y su inclusión en
`MANIFEST.in` y `tools/public-files.txt`.

Para repetir el escenario ficticio desde un checkout con el paquete regular
instalado, crear el padre `output` y elegir un destino nuevo:

```powershell
New-Item -ItemType Directory -Force output | Out-Null
python -m tools.historical_explorer_walkthrough --output output/v15-02-limitations-review
```

Ese comando permite reproducir el fixture; no se atribuye una ejecución adicional
a esta investigación. El bundle de referencia entregado arriba se generó mediante
`generate_explorer` y se comprobó con `verify_explorer(..., workspace=...)`.

Tras implementar bajo V15-02, el propietario deberá revisar el **nuevo bundle
corregido** a zoom 100% y 200%, ventana estrecha, wrapping largo, teclado/foco,
viñetas e indentación, siete afirmaciones intactas y funcionamiento offline.
Esas comprobaciones humanas siguen pendientes; las pruebas estáticas no las
sustituyen. No se realizó push, PR, merge, tag ni publicación.
