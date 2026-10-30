# V14-06 — Entrega local del candidato OT-ArchGuard v1.4.0

Fecha: 29 de octubre de 2026, America/Santiago. Preparación local: la versión
pública estable continúa siendo v1.3.0. Esta entrega no publica un release.

## A. Resultado ejecutivo

**RELEASE_CANDIDATE_READY_WITH_OWNER_GATES_PENDING**. La preparación técnica local
queda completada con límites documentados. Se congeló la distribución `1.4.0`
manteniendo el motor nativo y el alias histórico `__version__` en `1.3.0`.
Cada suite completa recoge 4.371 casos únicos: 4.370 PASS y un SKIP ambiental.
No se suman sus ejecuciones ni el subconjunto de Python 3.12. No quedan P0 demostrados sin
resolver ni P1 sin disposición concreta.

Se corrigieron defectos de verificación de releases: cabeceras de metadata
ambiguas/incorrectas, entrypoints adicionales y perfiles WHEEL alterados podían
aceptarse aun recalculando RECORD. El revisor independiente detectó además el
Metadata-Version coordinado inválido; ahora se exige el perfil revisado 2.4.
Se corrigió durante desarrollo el destino mutable de los hooks del nuevo
ensamblador. El verificador histórico permite sólo un cambio exacto del literal
de distribución derivado del pin aprobado; no repinea referencias ni relaja
inventarios. No fue necesario modificar parsers, lifecycle, motor o renderers.

La limitación significativa V146-B01 permanece intencional: las revisiones de
desarrollo vinculan fuente exacta y no se trasladan automáticamente al productor
estable. Se documentó conservar entorno/workspace anteriores, generar nuevos
análisis y efectuar nuevo review, sin editar hashes ni transferir aprobación.
La revisión independiente acepta esa disposición. Siguen pendientes las decisiones
del propietario, la CI del SHA final, integración de la pila y aceptación/publicación
desde el `main` integrado exacto.

## B. Identidad de las fuentes

| Identidad | Valor |
|---|---|
| Padre local y publicado | `ac893bc3174f0a7ace67454d19ad6e61116425af` |
| Árbol del padre | `80b1c4edded2c358548cf5c953200da1adddd8ff` |
| Inventario público inicial | 483 archivos; `e3403e07116beb6e200f6c09c659c7f4330dc4ae3823a713c1252e02c191a464` |
| Rama local | `codex/v14-06-final-release-readiness` |
| Primer freeze funcional/performance | `ab1ff34a7b7653ea3887f9db340b56666032e49f` |
| Congelación corregido y suites completas | `40ffbeab422dcf13f57d4fb9bc6e61a95d08642e` |
| Árbol de ese freeze | `1a7046eb5bc663d0fb1d398e8b72efada539524a` |
| Inventario público de aceptación | 503 archivos; `207b57038829d1c988dd4656974ffc8915ed022769998c8ab003b608fa34c4ad` |
| Inventario de 97 módulos padre | `e8900197961db578c83aca3576cf4883077b40dce243b4bc9af02553d8759cf2` |
| Inventario de 97 módulos candidato | `07b1db335733137cacb9b083960d308c67ae6716c8fe3202e6d7cfc5aec45d2a` |
| SHA local/árbol/inventario finales de entrega | `output/v146/delivery.json`, generado después del commit documental; `git rev-parse HEAD` y `git rev-parse 'HEAD^{tree}'` |
| Estado final del árbol | Limpio, comprobado en el recibo externo de entrega |

El único módulo de producción modificado es `src/otarchguard/__init__.py`: cambia
un literal de distribución. Los otros 96 módulos y todos los renderers conservan
bytes. No cambia ningún archivo de contrato implementado ni fixture congelado.
Se modifican dos aserciones de identidad de distribución, con justificación
explícita, y se agregan 98 casos únicos V14-06. No se debilita una aserción
analítica para obtener verde. Version, auditor de paquetes y verificador histórico
son revisados por el integrador y el revisor independiente.

El commit documental posterior incorpora esta evidencia y las correcciones del
runbook. Sus artifacts se reconstruyen y auditan nuevamente. No se atribuye la
ejecución completa al SHA documental: el código, tests y payload probado son
idénticos al freeze indicado y se verifican sus hashes. El recibo externo evita
incluir el hash de un archivo dentro de ese mismo archivo o de su propio sdist.

## C. Trabajo efectivamente realizado por agentes

| Agente | Alcance y hallazgos | Cambios | Verificación propia | Límite pendiente |
|---|---|---|---|---|
| A, native_assurance | Dominio cerrado, deny, intents independientes, witness, reservas de trabajo; sin P0/P1 nativo demostrado | Cinco casos y auditoría nativa | 229 PASS; Ruff/format/mypy | Campaña propia usó padre instalado; aceptación candidata en I |
| B, pipeline_assurance | Hints, TCP fragmentado, interpretación/review/replay, procedencia; V146-B01 | Cuatro casos compuestos y auditoría | 612 PASS/1 SKIP; 59 PASS de corpus, con solapamiento | Sin migración automática; productor anterior conservado |
| C, security_assurance | Datos hostiles, rutas, publicación, HTML e integridad; preflight ZIP antes de XML | 15 casos de tres adaptadores y auditoría | 430 PASS/1 SKIP; lint/format/mypy | Auditoría interna finita, sin pentest profesional |
| D, documentation_onboarding | Guías obsoletas, límites y upgrade, instalación/recovery | 12 documentos públicos/README y auditoría | 171 links; 12 bloques PowerShell; smoke del padre | Smoke final de ocho comandos del candidato completado por integrador |
| E, packaging_performance | Metadata/entrypoints/WHEEL, argv de build, licencias/deps y medición | Auditor estricto, 41 casos, avisos y dos informes | 41 PASS; lint/mypy; OSV 16 versiones; cuatro cargas emparejadas | Advisories temporales y mediciones acotadas |
| Integrador | Versión, pins, inventarios, ensamblado, campañas y entrega | Gate de versión, ensamblador/17 casos, runbook/handoff | Tres suites completas, 3.12, legacy, workflows, recovery y auditorías finales | Gates del propietario |
| Revisor independiente adicional | Desafío read-only del diff, evidencia y paquetes | Cero implementación; F01–F03 y validación de B01 | Revisión de fuentes/bytes/manifests y disposición final | CI/main/publicación siguen separados |

Cinco especialistas y un revisor adicional fueron utilizados. Se trabajó por
oleadas según los slots disponibles, con propiedad exclusiva de tests/informes.
El integrador controló versiones, CI, listas compartidas y todo diff de producción.

## D. Aceptación de capacidades

| Capacidad | Comportamiento admitido | Evidencia | Frontera de interpretación | Estado |
|---|---|---|---|---|
| Nativo | Validación, reachability, intents, exposición, trace y compare | Oracles/casos A, suites y 110 artifacts legacy; ejemplos CLI | Declaraciones de iniciación, no enforcement ni sesión real | PASS |
| Import Studio | Inventarios, gráficos y documentos acotados, review/provenance/reconciliación | Suite; project/document/quality walkthroughs; ZIP preallocation | Extracción estructural revisada, sin ejecutar Office | PASS |
| Architecture Explorer | Navegación offline de arquitectura/evidencia | Walkthrough instalado fuera del checkout; fuentes y links | Modelo declarado, no topología física autenticada | PASS |
| Capture Studio | PCAP/PCAPNG admitidos, observaciones y asociaciones/reconciliación | Suite; capture walkthrough; consumidores congelados | Hints/SYN/ausencia no prueban éxito, autorización o bloqueo | PASS WITH DOCUMENTED LIMITATION |
| Siete protocolos | Header/metadata subsets y abstención conservadora | Corpus, casos B/V14-05, suite e integración histórica | Sin TCP reassembly; NULL/SLL y formas no admitidas; tres gaps externos | PASS WITH DOCUMENTED LIMITATION |
| Histórico y revisiones | Storage inmutable, dependencias, revisiones y semántica exacta | evidence/evidence_history walkthroughs; suite/replay adversarial | Colección física distinta de análisis; no fuente/autenticidad inferida | PASS WITH DOCUMENTED LIMITATION |
| Baselines/review | Membresía/scope exactos, aprobación local, revocación/supersesión | Walkthrough histórico y casos de integridad | Nombres humanos no autenticados; no herencia de aprobación | PASS WITH DOCUMENTED LIMITATION |
| Drift | Comparabilidad/coverage explícita, dominios observados y nativos | Suite; drift walkthrough; replay | Cambio analítico/decoder no equivale a cambio físico | PASS WITH DOCUMENTED LIMITATION |
| Historical Explorer | Bundle offline, normal/dense/incomplete/decoder/unchanged y revocación | Walkthroughs wheel y sdist; verificación portable y de fuentes | Integridad portable distinta de autoridad/reproducción actual | PASS |
| Recuperación | Uninstall, wheel público 1.3 verificado, validación y reinstalación 1.4 | recovery-demo.json, Python 3.12 real | Workspace conservado; no se intentó downgrade histórico | PASS |

Los ocho módulos de walkthrough pasan con wheel instalado: project, document,
quality, capture, evidence, evidence_history, drift e historical_explorer.
Se ejecutan además Architecture Explorer, ejemplos nativos y ocho comandos de
onboarding de la guía final. El sdist instalado ejecuta ejemplos nativos y el
Historial Explorer desde su extracción auditada. Las suites del sdist usan los tests
del checkout con imports del site-packages independiente, conforme a la CI.

## E. Contratos congelados

| Referencia | Identidad original/candidata | Preservación y transición admitida | Prueba |
|---|---|---|---|
| Native v1.2 | `f52c792b683cb499dc7de765b65b5cc897a96854` permanece fijo | Schema 1 y contract.py exactos; sólo excepciones históricas previas expresas | 110 artifacts; schema SHA `a9fc6c96fbe0b91596516d4818a53edd5c9504611a142bcd152a7880460ebcf9`; contract SHA `7f423951e67f8583a4d71dc4ffa5812eb866e6b4244b1f605f9c613662d515ef` |
| Presentación V14-04 | `117318393ead604a023a24bad7d53eb429faa13f` permanece fijo | Paquete aprobado instalado aparte; renderers/13 HTML exactos | Capturas, appendices JSON y hashes independientes |
| Producción padre→candidato | 97 módulos, 96 exactos | Sólo `DISTRIBUTION_VERSION = "1.4.0.dev1"`→`"1.4.0"` | Fuente completa+inventario instalado; adversarios de módulos extra/omitidos/cambios |
| Motor/API | `1.3.0`→`1.3.0` | Resultados canónicos nativos idénticos | Legacy, oracles, fixtures y outputs emparejados |
| Enrichment/lifecycle/drift/Explorer | Versiones existentes sin cambios | No nueva semántica, schema ni límites | Inventario [contratos](v14-06-contracts.md); suites y replay |

Init padre SHA `970f736133968e77bee8b8675d01c70465c8fe441c368e6750d0cdf76e311525`;
candidato `dfea43564e1416d2996e5007a29da17f2d97603f5883c48c9c3aec9f70a8289c`.
No se reemplazó una referencia inmutable por HEAD.

## F. Seguridad y hallazgos

| ID | Gravedad | Resultado y disposición | Evidencia / residual |
|---|---|---|---|
| V146-R01 | P0 de preparación | Gate anterior rechazaba versión estable legítima; transición exacta implementada | 16 casos nuevos+guardas previas+legacy instalado; sin excepción genérica |
| V146-E01 | P1 | Rechazo de cabeceras ambiguas, entrypoints y WHEEL manipulados | 41 regresiones de archivos reales; RECORD recalculado no autoriza metadata falsa |
| V146-F01 | P1 | Revisor detectó Metadata-Version inválido concordante en tres records; fijado a perfil 2.4 | Dos adversarios coordinados dentro de los 41; suites completas del nuevo freeze |
| V146-E02 | P1 | Destino de build afectado por mutación de argv; corregido antes de aceptación | Rehearsal real de cuatro assets auditados y reabiertos |
| V146-B01 | P1 documental | Incompatibilidad exact-source intencional, guías corregidas y deferral revisado independientemente | Conservación del productor viejo/nuevos análisis-review; no migración implícita |
| A/SEC/B assurance | P2 | Extremos de puertos, intents, hints/framing y ZIP previo a XML cubiertos | Casos finitos independientes, sin runtime rewrite |
| D01–D03/F02–F03 | P1/P2 documental | Alcance/acceptance/upgrade, arquitectura de suite sdist, checksums y comandos PowerShell corregidos | Links, sintaxis y comandos instalados; historial documental preservado |

La matriz detallada de superficies, reproducción y límites está en
[seguridad](v14-06-security-audit.md) y el [registro](v14-06-readiness.md).
No se detectaron firmas de secretos en el scan acotado del padre; no se promete
un detector exhaustivo. Fuentes/imports pueden contener datos sensibles y no son
anonimizados. Los formatos adversariales se procesaron con fixtures finitos.
El modelo mantiene escritor único, límites de proceso y supuestos de filesystem;
no brinda aislamiento de un administrador concurrente ni durabilidad universal.

## G. Paquetes y artifacts

Los siguientes hashes corresponden **exactamente al freeze funcional probado
40ffbeab422dcf13f57d4fb9bc6e61a95d08642e**, conservado en `output/v146/acceptance-assets/`:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `otarchguard-1.4.0-py3-none-any.whl` | 363,482 | `bed0326d4425879bd0bc3724d46c77b1c3573fc12eebcaacf93a7d14e28704f7` |
| `otarchguard-1.4.0.tar.gz` | 2,173,312 | `561ce34fdd8d4a9e664dfbeb171053f8925d53ccc78daa233015dd80f43f1f6b` |
| `release-manifest.json` | 131,138 | `1924394a669712cb0834db0de6781da57b9aa516678565a2a9ae7008ce95e47e` |
| `SHA256SUMS.txt` | 280 | `fad51a3f5dae7e80936d17d6cdfd16d6ef56154e8f8c925b7089874fdab1747a` |

Ambos paquetes se construyen desde source limpio, se auditan por miembro y se
instalan independientemente sin import editable. Wheel/sdist/Python 3.12 tienen
los mismos 97 módulos instalados. La auditoría revisa source bytes, inventarios,
PKG-INFO/METADATA, perfil WHEEL, scripts, dependencias, licencias y RECORD.
`pip check` pasa en los tres entornos.

Se verifican además dos entornos de usuario nuevos, sin dependencias de desarrollo:
pip resuelve la clausura runtime desde wheelhouse para wheel y sdist, con backend
local para el segundo. Pasan identidad de los 97 módulos, pip check y validación
nativa. Los recibos son `output/v146/user-wheel-environment.json` y
`output/v146/user-sdist-environment.json`; no se usa `--no-deps` en esas instalaciones.

La **entrega documental final** reconstruye cuatro artifacts nuevos bajo
`output/v146/release-assets/`. Sus tamaños, SHA-256, commit y árbol definitivos
están en `output/v146/delivery.json` y su `release-manifest.json`; el recibo se
genera después de commitear este documento. Esto evita un hash circular del sdist
que contiene el propio handoff. Se reauditan fuente/archivos y se reinstala su
payload, demostrando igualdad con el freeze probado. No reutilice los hashes de
la tabla anterior para esa entrega final o para un futuro main integrado.

Manifest y SHA256SUMS no se hashéan a sí mismos. Se verifica la lista completa de
tres checksums y los cuatro archivos regulares; se rechazan digests inventados,
afirmaciones de aceptación añadidas y metadata de manifest no canónica. No se afirma
reproducibilidad byte a byte de archivos ZIP/gzip; sí igualdad de fuentes,
inventarios y payload instalado. Los assets no han sido publicados ni firmados.

## H. Separación de versiones

| Identidad | Valor observado |
|---|---|
| Package, importlib.metadata, DISTRIBUTION_VERSION y CLI --version | `1.4.0` |
| NATIVE_ENGINE_VERSION y alias histórico __version__ | `1.3.0` |
| Native schema/report/trace | `1` |
| Observaciones / workspace histórico | `2` / `2` |
| Enrichment / decoder | `1` / `2` |
| Drift / Historical Explorer | `1` / `1` |

El gate deriva la transición de bytes aprobados, compara la fuente completa con
la instalación regular y mantiene separado el paquete aprobado dev1. Se rechazan
otros cambios de versión/engine, módulos, HTML, resultados, tests históricos,
manifests y referencias. Las revisiones históricas permanecen exact-source.

## I. CI, tests y recibos

Fuente y entorno de la campaña: `40ffbeab422dcf13f57d4fb9bc6e61a95d08642e`, Windows 11 AMD64. La campaña source
importa `src/otarchguard`; wheel y sdist importan su site-packages separado. Todas
usan el hook offline Python y destinos de temporales independientes. Las tres
ejecuciones completas contienen el mismo conjunto de 4371 casos únicos.

| Campaña | Únicos | PASS | FAIL | ERROR | SKIP | Segundos | Recibo |
|---|---:|---:|---:|---:|---:|---:|---|
| Fuente, Python 3.14.5 | 4371 | 4370 | 0 | 0 | 1 | 1104.526 | `output/v146/full-source.xml` |
| Wheel instalado, Python 3.14.5 | 4371 | 4370 | 0 | 0 | 1 | 1104.548 | `output/v146/full-wheel.xml` |
| Sdist instalado independiente, Python 3.14.5 | 4371 | 4370 | 0 | 0 | 1 | 1104.492 | `output/v146/full-sdist.xml` |
| Subconjunto extenso, Python 3.12.14 | 943 | 942 | 0 | 0 | 1 | 278.953 | `output/v146/full-py312.xml` |

El único SKIP corresponde a `test_actual_windows_junction_is_rejected`: el SO no
otorgó creación de junction. No es un PASS del producto ni se eliminó la prueba.
Python 3.12 usa 24 archivos críticos: nuevos adversarios, oracles, capture, siete
protocolos, lifecycle/review, drift/Explorer e integridad de fuente/paquete. El
subconjunto extenso se justifica por código analítico idéntico y la futura matriz
completa de CI; no se afirma una suite completa adicional en3.12. No se ejecutó
Python 3.13, Linux o macOS localmente; metadata >=3.12 no es compatibilidad universal.

Ruff lint PASS; format PASS; strict mypy PASS (263 archivos de código). Dependencias
consistentes y payloads wheel/sdist/3.12 exactos. Legacy PASS:110 artifacts y13 HTML.
Consumidores congelados supported/limited PASS, corpus sintético verificado,
14 entradas de manifiesto de corpus y 171 links documentales del control inicial.
El control documental final verifica 186 links en 27 documentos y 18 bloques
PowerShell sin errores de sintaxis. Se ejecutan ambos procedimientos estrictos
de checksums, incluido un directorio con espacios y Unicode. Los comandos futuros
de push/tag/publicación sólo se analizan, no se ejecutan. Walkthroughs
y onboarding offline pasan con paquete instalado, incluido replay/forged rejection
y verificación de bundles. No se hizo un nuevo review humano de zoom/teclado/print.

Las cuatro ejecuciones iniciales recién iniciadas se interrumpieron al encontrar
F01; se preservan como `interrupted-initial-*`, sin sumarlas ni llamarlas PASS.
La campaña completa de la tabla se inició después de corregir y refreezar.
Errores de invocación del integrador se corrigieron sin modificar expectativas
del producto ni suprimir fallos de tests.

CI del **padre**: run40880668115, evento push, intento1, `ac893bc3174f0a7ace67454d19ad6e61116425af`,
seis jobs success Windows/Ubuntu/macOS×Python 3.12/3.14. Se verificaron conclusiones,
head remoto y artifacts; cero steps skipped en el recibo no equivale a un recuento
independiente de skips de tests del padre. No se afirma una CI ejecutada para
V14-06 ni para un futuro main. Vea [parent-ci](v14-06-parent-ci.json).

| Recibo local | SHA-256 |
|---|---|
| `full-source.xml` | `205087f194fd0fdb39ca349d746281389fa4f0f25336d1c9c470e6b473045c8d` |
| `full-wheel.xml` | `36cfdac350911eca6b8e23a4cc5f9401f607b8dacbc524a294d249b6f534905e` |
| `full-sdist.xml` | `241c28aa2a7d2cc91231d95fa5e893239d4449b4a1395247ca6a01fb83ffb924` |
| `full-py312.xml` | `db5ff0cd039ace23555e6fcba1ec63ffbf07ee392181dfd205e7cc394ff16f76` |
| `legacy/comparison.json` | `b564796c4177ea2d57517bf1f2216147175a036da01e1a2697144c25fdb9cb6e` |
| `performance-parent.json` | `2e7a893cde68466a9f72579a02becf77728c493cdf9ab3c0f1db0654ce7b5271` |
| `performance-candidate.json` | `390f37afd051bc8ca661b2a288b58b677a51604498508908a38e84b30cca0204` |

Los logs/XML completos quedan en output/v146, ignorados por Git. El handoff
preserva resultados y hashes compactos; no transforma ejecuciones solapadas en
nuevos tests únicos.

## J. Rendimiento y dependencias

La [comparación emparejada](v14-06-performance.md) fija padre ac893bc y primer
freeze ab1ff34, mismo host/CPython 3.14.5/14deps, cinco ensayos, warmup excluido y
allocations separados. Startup mediana0,726442→0,729308s; check0,011564→0,011779s;
PCAP0,004901→0,005171s; enrichment0,005088→0,005170s. Se conservan rangos y pequeñas
subidas. Tres outputs analíticos, contadores nativos y picos Python son exactos.
No se infiere speedup ni regresión causal universal; se divulga sesgo secuencial
y posible breve actividad del revisor. Los cambios posteriores sólo afectan
herramientas/documentación: el mismo payload97 módulos se verifica nuevamente.

No se repite toda la matriz de benchmarks para un cambio de literal/documentos;
se conservan estudios V14-05 y prueba de identidad del motor/parsers/renderers.
OSV oficial devolvió cero matches para16 versiones exactas consultadas (14 runtime,
pip y setuptools), con fecha/request/response retenidos. Es consulta temporal y
acotada, no prueba de ausencia de vulnerabilidades. Se revisaron17 archivos de
licencias/avisos no vacíos y la clausura de14 dependencias. No se actualizan deps ni
se agregan runtime dependencies. Detalle: [packaging](v14-06-packaging-audit.md).

## K. Documentación

Se corrigen README, CHANGELOG, instalación, release checklist, testing strategy,
foundation/history/Historical Explorer, límites, guía PCAP y README de ejemplos;
se agregan [notas 1.4](../release-notes-1.4.0.md), contratos, cinco auditorías y este
handoff/runbook. Se preservan registros históricos, capturas ficticias y aceptación
previa V14-04. Las guías distinguen estable 1.3, candidato 1.4 y futura publicación.
Comandos reales de onboarding y ejemplos se ejecutan contra instalación1.4.

## L. Limitaciones conservadas

Sin positivos externos aceptados completos para Modbus/DCP/IEC104; NULL/SLL no
soportados; sin reensamblado TCP ni decodificación industrial completa, valores
de proceso o éxito de comandos; sin planta real, pentest profesional o certificación.
Review humano local no autenticado, escritor único y fuente original de terceros
parcialmente desconocida. No autenticidad forense general ni anonimización.
Un hash prueba bytes, no autoría, cobertura, control físico o autoridad del reviewer.
Los ocho corpus externos aprobados sólo lo están para análisis local, con derechos
de redistribución desconocidos; sólo cuatro captures ficticios están tracked.

Unsupported, no evaluado, indeterminado, negativo, sin observación, sin path declarado
y denegación explícita permanecen resultados diferentes. V146-B01 exige productor
compatible para replay y no autoriza migrar aprobaciones. Los límites aparecen en
README, instalación y notas, no sólo en informes de desarrollo.

## M. Matriz R01–R32

| Gate | Estado | Evidencia / acción |
|---|---|---|
| R01 Padre exacto | PASS | Git local/remoto ac893bc, seis jobs/run/event verificados |
| R02 Rama limpia creada | PASS | Rama correcta desde padre; recibo final limpio |
| R03 Inventario de capacidades | PASS | Contratos y tablaD, cinco especialidades |
| R04 Semántica nativa | PASS | Oracles, legacy110 artifacts,96 módulos idénticos |
| R05 Límites de protocolos | PASS WITH DOCUMENTED LIMITATION | Siete subsets; gaps externos/NULL/SLL/TCP publicados |
| R06 Capture/histórico | PASS WITH DOCUMENTED LIMITATION | Composición, replay y B01 exact-source |
| R07 Sin P0 seguridad abierto | PASS | Auditoría interna finita y regresiones; sin certificación |
| R08 Sin P0 analítico abierto | PASS | Auditoría nativa y suites |
| R09 Versión distribución | PASS | CLI/metadata1.4; native1.3 |
| R10 Compatibilidad fail-closed | PASS | Pins sin repin, excepciones exactas y adversarios |
| R11 Wheel | PASS | Instalación regular97 módulos, suite completa |
| R12 Sdist | PASS | Instalación independiente, suite y extracción/walkthrough |
| R13 Inventarios | PASS | 503 archivos; fuente, archivos y payload reaudited final |
| R14 Dependencias/licencias | PASS WITH DOCUMENTED LIMITATION | Closure14,17 avisos, OSV 16point-in-time; no dictamen jurídico |
| R15 Offline | PASS WITH DOCUMENTED LIMITATION | Hook Python heredado, runtime sin red; no air gap físico |
| R16 Workflows | PASS | Native/import/capture/protocol/history/drift/Explorer/recovery |
| R17 HTML preservado | PASS WITH DOCUMENTED LIMITATION | Renderers exactos,13 HTML, aceptación humana previa; no nuevo browserreview |
| R18 Docs coherentes | PASS | Cambios actuales sin falsear historia |
| R19 README/instalación | PASS | Sintaxis, links, comandos instalados y recovery |
| R20 Changelog/notas | PASS | Entrada por capacidades, candidato no publicado |
| R21 Rendimiento | PASS WITH DOCUMENTED LIMITATION | Cuatro cargas emparejadas,otros 96 módulos idénticos |
| R22 Hashes | PASS | Recibos/XML, manifest y delivery externos sin circularidad |
| R23 Regresión completa | PASS WITH DOCUMENTED LIMITATION | Tres suites completas; un skip ambiental explícito |
| R24 Revisión independiente | PASS | F01–F03 dispuestos; auditoría final de source/package en recibo externo |
| R25 Datos terceros | PASS | Ningún capture externo nuevo/redistribuido; cuatro ficticios tracked |
| R26 Límites divulgados | PASS | README/notas/instalación y L |
| R27 Upgrade/rollback | PASS WITH DOCUMENTED LIMITATION | Recovery real; no downgrade histórico prometido |
| R28 Assets preparados | PASS | Cuatro archivos locales, auditados; finaldelivery externo |
| R29 Review del propietario | OWNER ACTION REQUIRED | Inspeccionar artefactos O y aceptar alcance/limitaciones |
| R30 CI SHA V14-06 | OWNER ACTION REQUIRED | Push/Draft PR autorizados por dueño; seis jobs del SHA final |
| R31 Main integrado | OWNER ACTION REQUIRED | Integrar pila, fijar nuevo SHA, repetir aceptación crítica |
| R32 Sin operación remota no autorizada | PASS | Sólo lecturas de GitHub y consulta de advisories; cero push/PR/merge/tag/release/dispatch |

OWNER ACTION REQUIRED nunca se considera PASS. Esta matriz acepta preparación
local, no publicación estable ni aceptación de un futuro commit integrado.

## N. Revisión independiente final

Agente adicional read-only, distinto de los cinco implementadores. Revisa diff,
pins, excepciones, afirmaciones, paquetes, inventarios, rollback y resultados. Encuentra
F01/P1 (formato metadata inválido), F02/P2 (directorio de suite sdist en runbook) y
F03/P2 (checksums duplicados y placeholder PowerShell de tag). Se corrigen con
casos coordinados y documentación. B01 se acepta independientemente como límite
del contrato exact-source y guía de upgrade explícita, sin normalización de hashes.

El revisor comprueba primero503 hashes de fuente,97 módulos wheel,503 fuentes sdist
y checksums del primer freeze; distingue esa observación de la entrega posterior.
La vinculación final de Git/archive/paquetes y el cierre de hallazgos se registra
en `output/v146/independent-final-review.json`, después del rebuild documental.
El veredicto final sólo se entrega al propietario tras completar esa comprobación.
No se atribuye al revisor implementación ni pruebas que no ejecutó.

## O. Inspección mínima del propietario

| Prioridad | Artifact / ruta exacta desde raíz | Objetivo | Resultado esperado |
|---|---|---|---|
| 1 | `docs/development/v14-06-handoff-es.md` | Resultado, límites, gates y alcance de evidencia | Sin blocker demostrado oculto; owner gates visibles |
| 1 | `output/v146/delivery.json` y `output/v146/release-assets/release-manifest.json` | SHA/tree/fuentes/paquetes finales y checksums | Coinciden entre sí y con Git, sin circularidad |
| 1 | `docs/development/v14-06-publication-runbook-es.md` | Push/Draft PR/pila/main/release y recuperación | Comandos revisables; sin GitHub CLI obligatorio |
| 2 | `docs/installation.md` y `docs/release-notes-1.4.0.md` | Primer uso/upgrade exact-source y límites | 1.3stable separado del candidato 1.4; revisión nueva de baseline |
| 2 | `docs/development/v14-06-packaging-audit.md` y `v14-06-contracts.md` | Parches de verificación y bytes congelados | Excepciones pequeñas justificadas,96 módulos preservados |
| 2 | `output/v146/walk-wheel/historical_explorer/normal/index.html` y `dense/index.html` | Revisión representativa si lo desea | Layout previo preservado; análisis y aprobación distinguibles |
| 3 | `output/v146/full-wheel.xml`, `full-sdist.xml`, `legacy/comparison.json` | Evidencia bruta de aceptación | Recuentos/identidades coinciden con I/E |

La aceptación visual previa no obliga a repetir39 archivos si no hay cambios de
renderer. Las páginas nuevas no se declaran inspeccionadas a alto zoom por el
agente. El propietario puede revisar las dos muestras para su aceptación final.

## P. Comandos de publicación

El [runbook español](v14-06-publication-runbook-es.md) proporciona los pasos A–I
copiables para PowerShell/Git y GitHub web: Draft PR con baseV14-05, seis checks,
orden #17→#23→V14-06, retarget controlado, merge commits, source `main` exacto,
rebuild/audit, notas/checksums, tag autorizado, publicación y verificación posterior.
Squash/rebase cambian identidades y requieren nueva estrategia explícita; no se
recomienda reescribir las ramas históricas. Ningún comando remoto fue ejecutado.

## Q. Veredicto

`RELEASE_CANDIDATE_READY_WITH_OWNER_GATES_PENDING`

Preparación local instalada, auditada, reproducida y revisable. El propietario
mantiene autoridad exclusiva sobre push, Draft PR, merge, tag y publicación.
Se requiere CI del SHA final y aceptación independiente del `main` integrado antes
de generar y publicar los assets de la versión estable definitiva.
