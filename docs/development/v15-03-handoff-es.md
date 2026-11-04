# Entrega técnica — Gate V15-03

**READY_FOR_OWNER_REVIEW**. Implementación acotada completa, suite general definitiva y verificación local aprobadas. Permanecen explícitos los controles de navegador, aceptación del propietario y seis jobs de CI del SHA que publique el propietario.

## Resultado y alcance

Se corrigieron dos problemas P2 reproducibles de PCAP Evidence Studio: una página distinta se anunciaba como página actual y los lotes de evidencia carecían de orientación y navegación adyacente. Ahora la navegación distingue documento exacto y familia; cada lote muestra página/total y rango de registros, con anterior/siguiente válidos. Explorar el siguiente lote pasa de volver al índice y localizarlo —al menos dos saltos— a un enlace directo. Los resultados analíticos, IDs, paquetes, asociaciones, fuentes y límites permanecen intactos.

Architecture Explorer, Historical Explorer e Import Studio alcanzan evidencia auténtica en los recorridos inspeccionados. Se conservaron sus renderizadores. El cambio evita ampliar innecesariamente la transición de fuente; no crea un panel integrado, enlaces absolutos entre informes ni nuevas capacidades OT/ICS.

## Identidades y dependencia anterior

| Elemento | Identidad exacta |
|---|---|
| Estado local inicial limpio | `codex/v15-02-compatibility-evolution`, `e01b5cf55b2918eb2b9908a250348a3477b38c3f` |
| Base fusionada PR #27 | `a3cf2f2e226b7a0fe985816cbaafb6ec6527b2f5` |
| Árbol base | `0e2c748edd6196a67a6cdee6f29b5aee639bb1a5` |
| Commit de producción verificado | `91f1d354f4d03ec202f6fd15b6ff6760d1d4f899` |
| Árbol de ese commit | `2556ba23761c3b9049725c70181335c880743d36` |
| Rama local | `codex/v15-03-evidence-centered-ux` |
| Cierre documental posterior | SHA/árbol/inventario y archivos finales: `output/v15-03/final-freeze.json` y `source-final.json` |
| Distribución anterior → candidata | `1.5.0.dev1` → `1.5.0.dev2` |
| Motor nativo / esquema YAML | `1.3.0` / `1`, sin cambio |
| Renderizador histórico | `1.5.0.dev1-historical-explorer.1`, sin cambio |
| Digest histórico de cinco fuentes | `442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b` |

La fuente local inicial y la fusión tienen el mismo árbol. PR #27 está fusionada; el [run base 41741064369](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/41741064369) terminó SUCCESS en las seis combinaciones Windows/Ubuntu/macOS × Python 3.12/3.14. Recibo: `output/v15-03/baseline-ci.json`. Ese resultado no se atribuye al candidato V15-03.

Windows 11 AMD64, Python 3.12.14. Intérprete definitivo: `C:\Users\PC\Desktop\OT-ArchGuard-CLEAN\.venv-v153-final\Scripts\python.exe`; módulos importados desde su `Lib\site-packages\otarchguard`. Sdist regular independiente: `.venv-v153-sdist`. Los recibos `authorized-final.json`, `authorized-sdist.json`, `environment-wheel.json` y `environment-sdist.json` registran ubicación y bytes realmente instalados; no se usó instalación editable.

## Problemas, causas y cambios

| Hallazgo | Reproducción original | Corrección / disposición |
|---|---|---|
| C-01, J2, P2 | `agent-c/supported/conversations-2.html` marcaba `conversations.html` con `aria-current=page`; reproducido en 36 documentos supported y 42 limited. | Comparar href con archivo real: `page` sólo en coincidencia exacta; `true` identifica familia. El pager señala el documento actual con párrafo no enlazado. |
| C-02, J2, P2 | `agent-c/supported/evidence-5.html` no tenía contador/rango ni anterior/siguiente. | Pager local etiquetado y continuo para todos los lotes, sin cambiar nombres ni anchors. |
| K-01, J2, evaluación estructural | Destino del skip link sin atributo explícito de foco programático; no se demostró fallo de navegador. | `main id=main tabindex=-1`; no añade parada a Tab. Verificación interactiva pendiente. |
| A-04, documentación, P3 | Tutorial instalaba estable 1.4.0 pero exigía CLI 1.3.0. | Distinguir distribución publicada y motor nativo. |
| B-01/B-02/A-03, P2 | Orientación de Architecture/Historical y branding de review. | Diferidos: navegación/evidencia funcionan; requieren cambio compartido o renderer histórico separado. |

Sólo cambian dos módulos de producción; los otros 95 conservan exactamente sus bytes. SHA-256 autorizados:

- `src/otarchguard/__init__.py`: `537061f2c8798181dbcef27787531b620d459455c9786557521df4d808123228`.
- `src/otarchguard/capture/explorer.py`: `3370880ed45688b8d2c084b135d465316cd3ef580922671524a817e3a5a24c3b`.

Otros archivos revisables: `pyproject.toml`, `.github/workflows/ci.yml`, `MANIFEST.in`, `tools/public-files.txt`, `tools/verify_v15_03_transition.py`, `tests/test_v15_03_navigation.py`, `tests/test_v15_03_transition.py`, adaptaciones acotadas de `test_capture_ux_integrity.py`, `test_release_candidate.py`, `test_v141_identity.py`, `examples/capture-studio/README.md` y ocho documentos `docs/development/v15-03-*.md`. `git diff --name-only a3cf2f2 HEAD` identifica el conjunto definitivo.

## Transición, evidencia histórica y seguridad

`tools/verify_v15_03_transition.py` es una política nueva y revisable. Fija commit/árbol anterior, dos digests autorizados y los 95 módulos sin cambio; rechaza altas, bajas, recursos desconocidos y alteraciones de oráculos protegidos. Valida metadatos, ubicación y bytes físicos instalados antes de importar producción. Ejecución autoritativa aislada con `python -I`; helpers/comparador se compilan desde bytes Git autenticados y se usan cachés nuevas.

El verificador V15-02 y sus pruebas permanecen byte a byte. Se ejecutan contra su fuente archivada e instalación dev1, no contra dev2. `transition-final/transition.json`: PASS; verificador V15-02 anidado: PASS; 30 pruebas históricas: PASS. Todas las salidas nativas comparadas resultan `EXACT_BYTES`, sin diferencias efectivamente aceptadas. Consumidores frozen supported/limited y corpus industrial conservan sus recibos separados.

Cambiar `__init__.py` cambia el productor analítico ligado a fuente. Verificación portable del bundle dev1: PASS; replay con dev2: rechazo `EVIDENCE_REVISION`; recuperación con instalación dev1 original: PASS. Inventario histórico intacto y `approval_transferred=false`. No se reescribieron revisiones, baselines, aprobaciones, revocaciones ni referencias v1.4. Una identidad de productor diferente no demuestra cambio físico de tráfico.

La navegación conserva escaping, máscara de rutas, revelado de bidi, CSP, ausencia de ejecución/recursos externos y presupuestos. Las pruebas comprueban identidad de flow/registro, no sólo existencia del destino; cubren enlaces hacia otro archivo existente, anchors ausentes/duplicados, siguiente incorrecto, evidencia omitida, JSON alterado, fuente no autorizada y falsificación rehasheada. El auditor alteró un booleano real de reachability y recalculó todos los hashes: el comparador inmutable lo rechazó por diferencia inexplicada en `trace.json`.

## Campañas y conteos

| Campaña | Estado al corte / recibo |
|---|---|
| Suite focalizada definitiva | PASS, 83; `focused-final.log` / `.xml` |
| Pruebas nuevas únicas | 40 casos en los dos módulos V15-03; incluidas en las 83 |
| Auditor F independiente | PASS, las mismas 40; no sumar nuevamente |
| Sdist extraído con runtime instalado | PASS, 258; `sdist.log` / `.xml`; se solapan con la suite |
| V15-02 preservado, entorno dev1 | PASS, 30 en 26.25 s; `transition-final/historical-tests.xml` |
| Suite general candidata definitiva | PASS, 4.453; cero FAIL/ERROR/SKIP; `full-final.log` / `.xml` |
| Ruff / formato / mypy estricto | PASS; mypy: 274 archivos; `static-exits.json` |
| Dependencias wheel y sdist | PASS; `dependencies-final.log`, `dependencies-sdist.log` |
| Walkthroughs finales y sdist | PASS, exit 0; recibos en `review/`, `sdist-capture/`, `sdist-historical/` |
| Transición final aislada | PASS; `transition-final.log`, `transition-final/commands.json` y `transition.json` |
| Teclado / viewport / zoom / impresión / propietario | NOT_TESTED |
| CI remoto del candidato exacto | NOT_TESTED, sin publicación autorizada |

La suite actual excluye expresamente `tests/test_v15_transition.py`: sus 30 casos específicos de dev1 se conservan y ejecutan separadamente en ese entorno. No se oculta un skip ni se afirma que el verificador viejo acepta dev2. No sumar las ejecuciones focalizadas, F y sdist como pruebas únicas adicionales; el total único es 4.453 casos actuales más 30 históricos = 4.483. Focalizadas, F y sdist están completamente incluidas en la campaña actual. Los 40 nuevos casos son únicos, no adicionales a esas 4.453.

Los intentos fallidos quedan retenidos: ensurepip inicial restringido por sandbox; reinstalación de `.venv-v153-wheel` bloqueada al mover el launcher y entorno dejado sin runtime; primera transición afectada por ese entorno; primer candidato con elemento HTML no permitido. Esas ejecuciones están superadas por entornos nuevos y recibos definitivos, sin convertir sus resultados en PASS.

## Paquetes, fuente y congelación

La instalación definitiva wheel y la instalación regular desde sdist autorizan los mismos 97 módulos, distribución y motor. `archive-implementation.json` audita los archivos construidos del commit de producción: wheel 363.322 bytes, SHA-256 `793a32b4c76030d6c4d5e8125095e33f1a9973a0344da129d6f8dd4db22fc9b3`; sdist 2.371.897 bytes, SHA-256 `39a26252057988fce393ced0afb3ffcf1840fe75a27965f4b9519bdf1f52c75c`. Son identidades del candidato de implementación; los archivos definitivos se reconstruyen por separado en `output/v15-03/final-artifacts/`, con auditoría y hashes en `archive-final.json` y `final-freeze.json`. Ambos entornos regulares se reinstalan desde esos archivos finales y repiten autorización aislada, identidad y pip check; sus bytes de producción/pruebas son los ya verificados.

`archive-audit.json` pertenece a un intento anterior superado y no identifica el runtime definitivo. La congelación final registra HEAD/árbol, inventario público, módulos, fuentes de tests, archivos, instalaciones y checks; una edición exclusivamente documental no autoriza atribuirle otra producción. Los informes y capturas ficticios quedan ignorados bajo `output/v15-03/`; no se publican ni se incluyen accidentalmente como evidencia operacional.

## Rendimiento medido

Mismo driver, entradas/dependencias registradas, Windows/Python 3.12.14; una preparación y cinco renders completos por caso, sin análisis/mapping. Valores iniciales bajo concurrencia de trabajo no controlada:

| Caso | Mediana antes → después | Variación tiempo | Bytes antes → después | Páginas |
|---|---:|---:|---:|---:|
| Supported | 0.26666 → 0.36362 s | +36.4% | 402.392 → 405.651 (+0.81%) | 47 → 47 |
| Limited | 0.33913 → 0.36271 s | +7.0% | 452.987 → 456.758 (+0.83%) | 53 → 53 |
| Dense 130 | 2.44128 → 2.64844 s | +8.5% | 3.653.901 → 3.667.134 (+0.36%) | 175 → 175 |

`agent-e/{before,after}/benchmark.json` conserva ensayos individuales, mínimo/máximo/desviación, hashes y recuentos. Datos canónicos y páginas se conservan; generación repetida determinista. La repetición sin campañas pesadas, en orden candidato→dev1, obtuvo medianas antes/después 0,247294/0,233129 s, 0,275811/0,268877 s y 2,222209/2,144854 s (cinco ensayos por caso). No reprodujo la ralentización inicial. Los intervalos se solapan; no se afirma aceleración ni ausencia universal de regresión. Véase performance.md para min/max/desviación y agent-e/repeat-{before,after}/benchmark.json. Antivirus, caché y planificación no están controlados. No se midió memoria ni rendimiento global del producto.

## Auditoría independiente y artefactos visuales

A: cuatro journeys y auditoría; B: Architecture/import; C: PCAP; D: historia/compatibilidad; E: instalación/rendimiento; F: revisión escéptica. Sin ediciones concurrentes de producción. F detectó P1 inicial porque `<span>` no era permitido por el auditor HTML: se sustituyó localmente por párrafo permitido, sin ampliar la allowlist. También exigió reforzar guards de pager y corregir rutas documentales/CI. Todos resueltos; no queda P0/P1 independiente abierto. `agent-f/findings.md` conserva evidencia y disposiciones.

Auditoría final independiente: **486 páginas, 14.408 enlaces, cero archivos/fragmentos faltantes ni IDs duplicados**, siete sitios; `review-link-audit.json`. Las auditorías de descubrimiento se solapan y no se suman a estos totales. La conectividad estática se acompaña de pruebas de flow/record correcto, pero no acredita interacción de navegador.

Raíz local para los siguientes artefactos: `C:\Users\PC\Desktop\OT-ArchGuard-CLEAN\`.

| Caso | Índice relativo a esa raíz |
|---|---|
| Architecture | `output\v15-03\review\architecture\index.html` |
| PCAP comparado | `output\v15-03\review\capture\comparison\index.html` |
| Historical normal | `output\v15-03\review\historical\normal\index.html` |
| Historical revocado | `output\v15-03\review\historical\revoked\index.html` |
| Historical denso | `output\v15-03\review\historical\dense\index.html` |
| PCAP denso | `output\v15-03\agent-e\after\dense-0\index.html` |
| PCAP limitado | `output\v15-03\agent-e\after\limited-0\index.html` |

El navegador disponible rechazó `file:` por su política de acceso. No se añadió servidor ni se usó otro mecanismo para eludirla. No existen screenshots ni resultados positivos de foco real, zoom, viewport o impresión. El propietario debe abrir los HTML directamente en su navegador habitual, manteniendo las carpetas completas.

## Aceptación manual del propietario

Registrar navegador/versión/fecha y **PASS / FAIL / NOT_TESTED / NOT_APPLICABLE** por cada recorrido y propiedad. Estado inicial de todos: NOT_TESTED.

**J1 — Architecture, seis pasos:** (1) abrir overview y confirmar modelo/hash/model-only; (2) Assets → `it`; (3) abrir interfaz y distinguir propietario/placement; (4) abrir Exact trace `it → svc_jump`; (5) seguir regla/witness y comprobar TCP/3389, modelo y limitaciones; (6) volver a Analytical results y Architecture overview. No confundir declaración y despliegue.

**J2 — PCAP, ocho pasos:** (1) abrir overview y Coverage and limits; (2) Observed addresses → `192.0.2.10`; (3) abrir su TCP/502 a `192.0.2.20`; (4) seguir finding y Evidence details; (5) comprobar flow ID, packet references y clasificación; (6) inspeccionar asociación revisada sin asumir autorización; (7) en caso denso recorrer siguiente/anterior lote y confirmar Page N/M/rango exacto; (8) volver a comunicación y overview. Revisar ARP/IPv6 y abstención en caso limitado.

**J3 — Historical, ocho pasos:** (1) abrir normal overview; (2) Scope and comparability → Pair 1; (3) abrir dominio/finding; (4) seguir source revision/evidencia retenida; (5) regresar al mismo finding; (6) Evidence and approval → comparar estado registrado y estado de generación; (7) abrir revoked y confirmar REVOKED actual con aprobación original conservada; (8) Verify this report → distinguir integridad portable/replay y volver al overview. Repetir navegación densa y revisar las siete limitaciones verticales.

**J4 — Import/review:** recorrer las evidencias de `output/v15-03/agent-a/import-explorer/index.html`: Assets → eng → candidato contradictorio → source observation → decisión/partición del propietario → declaración nativa. Son decisiones ficticias; no aplicarlas a un proyecto real.

**Accesibilidad, ocho comprobaciones:** (1) Tab → skip → Enter → Tab y Shift+Tab; (2) foco visible en enlaces/pagers sin trampas; (3) Enter/Space en details y SHA completo; (4) teclado en región de tabla y scroll horizontal local; (5) viewport aproximado 375px; (6) 320px; (7) zoom 200%; (8) print-preview de tabla y finding denso. Confirmar texto normal sin overflow global, IPv6/IDs largos completos, estados no dependientes del color, ningún contenido crítico oculto y leyenda histórica legible.

## Cierre local, CI y publicación por el propietario

Rama local cerrada mediante commits; `final-freeze.json` registra estado limpio, SHA/árbol e inventarios definitivos. El único cambio posterior a producción 91f1d35 fue el orden de argumentos CI en 19b552fe5892b45c768d8cbd897568e7d289a230 (árbol 1d1e3204df831593b5ad5c273ca87e6121abe68e), seguido del cierre solo documental. La prueba original de CI permanece intacta; auditor F04 confirmó argumentos idénticos. Antes de publicar, comprobar `final-freeze.json`, `git status --short --branch`, `git rev-parse HEAD` y `git rev-parse 'HEAD^{tree}'`. Suite final, auditoría y aceptación local constan en sus recibos; los controles externos siguen pendientes. No se ejecutó push, PR, merge, tag ni publicación de assets.

Procedimiento ordinario, sólo para ejecución posterior por el propietario:

```powershell
Set-Location 'C:\Users\PC\Desktop\OT-ArchGuard-CLEAN'
git status --short --branch
git log --oneline -3
git diff --stat origin/main...HEAD
git rev-parse HEAD
git fetch --no-tags origin main
git log --oneline HEAD..origin/main
# Si main avanzó: reconciliar y repetir las verificaciones antes de publicar.
git push -u origin codex/v15-03-evidence-centered-ux
```

Después abrir [comparación para preparar PR](https://github.com/z4y-d3n/OT-ArchGuard/compare/main...codex/v15-03-evidence-centered-ux?expand=1), base `main`, título `V15-03: Evidence-centered PCAP navigation and source transition`. Adjuntar resumen, verificación, límites de navegador/rendimiento y enlace a este documento; no adjuntar capturas operacionales ni todo `output/`. Exigir seis jobs reales SUCCESS para el SHA exacto enviado y revisar resultados wheel/sdist, transición y oráculos. Un commit posterior necesita sus propios checks. No fusionar ni crear tag estable como parte de este gate.

Recomendación V15-04: cerrar aceptación visual real y ampliar medición solo si aparece una regresión reproducible; después abordar orientación/branding de Architecture e Historical con transición de fuente/renderizador propia. Mantener alcance offline, trazabilidad de evidencia y separación entre aprobación local, integridad y reproducción analítica.

La primera suite completa (full.xml) tuvo 4.452 PASS y un FAIL: el guard textual de CI esperaba el prefijo de comando anterior. Se reordenó --ignore después de --basetemp, sin cambiar argumentos ni prueba; 17 casos CI/foundation pasaron y la repetición completa posterior aprobó los 4.453. Ese intento no se borra ni se contabiliza como cobertura única adicional. F04 está documentado en agent-f/ci-order-review.md.

F también sustituyó un enlace de hallazgo por otro flujo existente: archivos, anclas y JSON seguían válidos, pero el oráculo contextual original rechazó la identidad equivocada. Recibo: `agent-f/wrong-existing-record.json`; experimento aislado sin aumentar el conteo de casos pytest. E recalculó estadísticas y hashes de los 72 sitios reales de rendimiento. Estas auditorías complementan el PASS de la suite sin sustituir la aceptación visual pendiente.
