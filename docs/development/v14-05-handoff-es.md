# V14-05 — Entrega local para revisión del propietario

Fecha: 29 de octubre de 2026. Distribución `1.4.0.dev1`; motor nativo `1.3.0`.

## A. Conclusión ejecutiva

**LISTO PARA REVISIÓN LOCAL, CON LIMITACIONES DOCUMENTADAS.** V14-05 fortalece
la evidencia de los siete decodificadores y de su composición con el histórico,
drift, replay y publicación. Añade 81 casos únicos: 32 de corpus, 30 de fronteras
de protocolo, 14 de integridad histórica y cinco de integridad de medición.
La suite completa del repositorio pasa **4.272 casos**, con **un SKIP ambiental**,
sin fallos ni errores; 4.273 casos únicos en total. No se suman ejecuciones repetidas.

No se demostró un defecto de producción que requiriera corregir un decodificador,
el motor nativo o el lifecycle. Los 97 módulos de producción, los contratos
congelados, los renderers y el verificador histórico conservan sus bytes.
Las mejoras son evidencia independiente, regresiones adversariales compuestas,
medición reproducible y consistencia de inventarios. No se inventó una
optimización ni se amplió soporte para obtener positivos.

Persisten los positivos externos pendientes de Modbus/DCP/IEC104, NULL/SLL sin
soporte, ausencia de reensamblado TCP, revisiones humanas locales no autenticadas
y el modelo de un solo escritor. La CI del candidato corresponde al propietario.
No hay certificación industrial, validación en planta ni pentest independiente.
Este trabajo no sustituye la campaña pública adversarial previa a v1.5.

## B. Identidades y límites Git

| Identidad | Valor verificable |
|---|---|
| Padre V14-04 | `d898516e24dec922179696e4cb50a262b3466a46` |
| CI del padre | [40808096253](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40808096253), seis trabajos correctos para ese SHA exacto |
| Rama local | `codex/v14-05-corpus-interoperability-hardening` |
| Implementación y freeze | `e4d8234acd504ca30d6d0aef66f316b8cf1c86d0` |
| Inventario público del freeze | `b5b65b8c97125d68aba15fd97190a3628b40a39477c0fba1dc0fa74a3a075ce3`, 480 archivos |
| Inventario de los 97 módulos instalados | `e8900197961db578c83aca3576cf4883077b40dce243b4bc9af02553d8759cf2`, idéntico al padre |
| Nativo v1.2 inmutable | `f52c792b683cb499dc7de765b65b5cc897a96854` |
| Presentación V14-04 aprobada | `117318393ead604a023a24bad7d53eb429faa13f` |
| Commit final y estado del árbol | `output/v145/delivery.json`; `git log -2 --oneline` y `git status --short` |
| Inventario final de entrega | `output/v145/delivery-source.json`, auditado contra los blobs del commit final |

El commit posterior al freeze agrega documentación y recibos compactos; no cambia
producción, pruebas ni harnesses. El recibo externo al árbol versionado contiene
el SHA final y su inventario, evitando una referencia circular al hash del propio
documento. Árbol final limpio. Se realizaron lecturas públicas de CI e índices;
**cero mutaciones remotas**: sin push, PR, merge, tag, release ni dispatch.

## C. Trabajo efectivamente completado por agentes

| Agente | Responsabilidad independiente | Hallazgos y cambios | Pruebas ejecutadas | Brechas |
|---|---|---|---|---|
| A — corpus | Bytes originales, procedencia y oracle externo | PCAP original de 28 paquetes; expectativas literales; TShark 4.6.9, 36 coincidencias en 14 joins positivos; builder sin imports del producto | 32 PASS; Ruff/format/mypy PASS | Sin nuevos positivos externos de Modbus/DCP/IEC104 ni permisos nuevos de redistribución |
| B — interoperabilidad | Transiciones de confianza y límites de framing | Siete invariantes de privacidad; parada ante registro intermedio inválido; límites exactos; cuatro variantes PCAP; puertos ambiguos y publicación rechazada | 30 PASS; Ruff/format/mypy PASS | NULL/SLL, TCP segmentado, familias/formas fuera del subconjunto |
| C — histórico | Composición real desde PCAP hasta Explorer/replay | Reinterpretación física/analítica; supersesión; fuentes seleccionadas y no seleccionadas; revocación durante render; presupuesto exacto de bundle | 14 PASS; Ruff/format/mypy PASS | Datos ficticios, autoridad no autenticada y escritor único |

No se reclutó un cuarto agente. El integrador revisó los cambios, agregó cinco
casos que impiden publicar recibos de medición con entradas o resultados cambiados,
integró manifiesto/CI y ejecutó las verificaciones finales. Los archivos nuevos
de cada agente tuvieron propiedad exclusiva; no hubo escritores concurrentes
sobre parsers, manifiestos ni contratos compartidos.

## D. Cobertura de los siete protocolos

El corpus nuevo es **Tier 1 original**, no tráfico externo. Tiene 2.460 bytes,
14 formas positivas, siete truncadas y siete no soportadas. SHA-256:
`9035464f34c6d2b45c528678b1f1d2af87b4d428b6707c395564239bfe0de3c2`.
El inventario actual contiene dos Tier 1, cero Tier 2, ocho Tier 3 aprobados
para análisis local y cuatro candidatos Tier 3 sin aprobación.

| Protocolo | Positivo sintético nuevo | Negativo/adversarial | Referencia independiente | Cobertura externa existente | Límite pendiente |
|---|---|---|---|---|---|
| Modbus TCP | FC16 y excepción | MBAP incompleto, función desconocida, longitud contradictoria, puertos ambiguos | Literales; 4 campos TShark | Ninguna | Sin dirección de petición ni ejecución; brecha externa |
| PROFINET DCP | Get y respuesta, VLAN37 | TLV/selector/límites, Hello, FrameID ajeno en regresiones existentes | Literales; 8 campos TShark | Ninguna | No valores de configuración; brecha externa |
| EtherNet/IP/CIP | SendRRData y respuesta CIP | Prefijo truncado, comando desconocido, CPF/forma no soportada | Literales; 4 campos TShark | Dos referencias de encapsulación; CIP conectado opaco | Sin éxito de servicio ni interpretación conectada |
| S7comm clásico | ReadVar y ACK-data de error | TPKT truncado/incorrecto, Plus, registros coalescidos | Literales; 3 campos TShark | Snap7 clásico | Plus/segmentación no soportados; otra referencia tiene SLL |
| IEC-104 | I tipo1 y S | APCI incompleto, U no soportado, control/longitud contradictorios | Literales; 3 campos TShark | Ninguna | Sin significado de proceso; brecha externa |
| OPC UA Binary | HEL y ERR | Prefijo, chunk abortado, tamaño inválido y cadenas hostiles privadas | Literales; 6 campos TShark | Referencia gap/handshake | Servicios seguros opacos; otras referencias usan NULL |
| DNP3/TCP | Lectura y respuesta con CRC | Prefijo, transporte fragmentado, CRC corrupto y cuerpo privado | Literales; 8 campos TShark; CRC independiente en pruebas de frontera | Referencia DNP3 | CRC no autentica; objetos de proceso no interpretados |

La [matriz de corpus](v14-05-corpus-coverage.md) contiene hashes de especificación
y recibo, referencias de framing y reproducción. El [informe de fronteras](v14-05-interoperability.md)
documenta las clases equivalentes. Los 36 campos seleccionados no representan
una verificación independiente de cada campo ni soporte de protocolos completos.

Los ocho archivos externos siguen en `output/v14-external/`, excluidos de Git
y de distribuciones. Se verificaron nuevamente sus hashes/tamaños/framing y se
ejecutó el producto actual: ocho digest/counters reproducen exactamente los
recibos históricos. Los **615 positivos / 2.194 comparaciones** son el resultado
histórico TShark 4.6.7; no se presenta como una comparación TShark externa nueva.
Los tres resultados NULL/SLL permanecen no soportados. Publicar un índice o
una licencia raíz no establece permiso de redistribución por captura.

## E. Integridad entre componentes

| Componente | Invariante y evidencia | Resultado / límite |
|---|---|---|
| Captura | Cuatro endian/precisiones PCAP; índices, offsets, longitud y tiempo racional exactos | PASS; NULL/SLL y linktype147 abstienen |
| Enrichment | Campos permitidos, orden, denominadores, límites y privacidad | PASS; reconocer escritura no prueba ejecución |
| Colección histórica | SHA físico estable, snapshot preservado, dependencias completas | PASS; metadata no autentica PCAP original |
| Revisión analítica | Mismo PCAP con límites distintos genera otra revisión y una sola colección | PASS; diferencia operacional de protocolo retenida como no evaluable |
| Baselines | Membresía/scope exactos y propuesta sin aprobación heredada | PASS; casos nuevos y suite existente |
| Reviews | Revocación/supersesión separan autoridad actual de afirmación registrada | PASS; etiquetas humanas no autenticadas |
| Drift | Replay exacto; enriquecimiento de otra captura rechazado; incertidumbre preservada | PASS; no inferencia de bloqueo, incidente o ausencia global |
| Explorer histórico | Sin cambio de renderer; fuentes modificadas durante render rechazan finalización | PASS; ningún manifest de éxito ante mutación |
| Verificación dependiente de fuentes | Una dependencia no seleccionada ausente invalida una verificación fresca | PASS; integridad portátil sola no es reproducción analítica |
| Evidencia canónica/nativa | 126 archivos de producción/fixtures/gates idénticos al padre; comparación inmutable | PASS; 124 archivos capturados, 110 artefactos analíticos y 13 HTML aprobados |

## F. Amenazas y contraejemplos reproducibles

| Clase de entrada o fallo | Resultado real y esperado | Prueba reproducible | Reparación / límite |
|---|---|---|---|
| Valores privados sustituidos en siete familias | Identidades fuente cambian; registros públicos permanecen idénticos | `test_private_value_substitution_preserves_only_allowed_header_evidence` | Sin cambio de producto; no prueba privacidad fuera del allowlist |
| Mensaje inválido entre dos completos | Positivo inicial y abstención terminal, sin resincronización especulativa | `test_bad_middle_record_stops_packet_without_resynchronizing_later_valid_bytes` | Sin reensamblado ni búsqueda por offsets |
| Framing exterior NULL/SLL con bytes internos reconocibles | Cero registros y contador explícito no soportado | `test_recognizable_inner_payload_cannot_override_unsupported_null_or_sll` | Sin conversión de linktype |
| Registro PCAP fatal después de un positivo | CLI exit2, diagnóstico y ningún archivo de enrichment publicado | `test_fatal_later_container_record_prevents_cli_publication_after_valid_protocol` | No salida parcial exitosa |
| Revocación o bytes cambiados tras replay, durante render | `EVIDENCE_CHANGED`, sin manifest de éxito | `test_source_changes_after_replay_prevent_completion_even_after_rendering` | Supone escritor único, no sandbox contra escritor privilegiado |
| Dependencia ajena a la selección eliminada tras una verificación correcta | Nueva adquisición completa rechaza; integridad portátil no concede autoridad | `test_fresh_source_verification_checks_unselected_dependencies_after_prior_success` | Fuentes deben seguir disponibles |
| Bundle coherente repite aprobación antigua | Verificador fresco expone REVOKED y autoridad de generación no autenticada | `test_rehashed_generation_assertion_does_not_authenticate_current_authority` | Hash no prueba autoridad ni fecha |
| Presupuesto exacto y un byte menos | Exacto acepta bytes idénticos; menor rechaza antes de crear salida | `test_exact_bundle_byte_ceiling_accepts_and_one_byte_less_rejects_entire_workflow` | Techo de trabajo, no garantía RSS/latencia |
| Entradas/resultados cambiados al medir | No se publica recibo de aceptación | `tests/test_v145_performance.py` | Equivalencia de medición no sustituye oracle semántico |

Las pruebas existentes de grafos falsificados, interrupciones, goldens y errores
de fuente también pasaron dentro de la suite completa. Ningún éxito finito
demuestra inmunidad general. No hubo corrección de producción ni relajación
de códigos/goldens para obtener PASS; la cifra de entradas aprobadas se actualizó
de nueve a diez por la incorporación real del segundo corpus original.

## G. Rendimiento

El [estudio de rendimiento](v14-05-performance.md) registra cargas exactas,
commits, entorno, medianas/rangos, memoria separada, resultados más lentos y
comandos. Su recibo compacto versionado es
`benchmarks/receipts/v14-05-windows.json`; los recibos completos se conservan bajo
`output/v145/`. Se usaron el mismo intérprete, bytes, límites y warmups, sin suites
concurrentes durante las mediciones. El código de producción es idéntico: no se
atribuye variación observada a una optimización ni se promete capacidad industrial.

## H. Recibos finales de verificación

Todos los paths de esta tabla existen en el checkout local. Los voluminosos
permanecen ignorados por Git y pueden contener metadatos sensibles.

| Gate | Resultado | Path exacto desde la raíz |
|---|---|---|
| Casos nuevos únicos | 81 PASS dentro de la suite final | `output/v145/full-source.xml`; cuatro `tests/test_v145_*.py` |
| Integración enfocada | 589 PASS, 1 SKIP, 70,41 s | `output/v145/focused.xml`, `focused.log` |
| Suite completa única del repositorio, wheel regular idéntico a fuente | 4.272 PASS, 1 SKIP, 0 FAIL/ERROR, 868,32 s | `output/v145/full-source.xml`, `full-source.log` |
| Python 3.12.14, wheel regular | 128 PASS, 0 SKIP/FAIL, 43,80 s | `output/v145/py312-focused.xml`, `py312-environment.json` |
| Replay cruzado 3.14 → 3.12 | PASS; reporte reproducido y Explorer histórico actualmente REVOKED | `output/v145/py312-cross-reproduction.json` |
| Ruff y formato global | PASS en freeze y entrega | `output/v145/ruff-check.log`, `ruff-format.log`, `delivery-ruff-check.log`, `delivery-ruff-format.log` |
| Mypy estricto global | PASS; 256 archivos fuente | `output/v145/mypy.log` |
| Dependencias, wheel/sdist/3.12 | PASS | `output/v145/pip-check.log`, entornos `wheel-environment.json`, `sdist-environment.json`, `py312-environment.json` |
| Wheel/sdist e inventarios instalados | PASS; 97 módulos exactos | `output/v145/archive-audit.json`; entrega: `delivery-archive-audit.json` |
| Nativo/presentación inmutables | PASS; 124 archivos, 110 analíticos, 13 HTML | `output/v145/native-compatibility/comparison.json` y `command-*.stdout/stderr` |
| Readers congelados soportado/limitado | Ambos PASS | `output/v145/consumer-supported.json`, `consumer-limited.json` |
| Corpus original y oracle independiente | PASS; 28 paquetes, 36 campos seleccionados, cero discrepancias | `output/v145/corpus-integrity.json`; `tests/fixtures/protocol-corpus/v145-tshark-receipt.json` |
| Referencias externas locales | Ocho hashes y ocho digest/counters reproducidos | `output/v145/existing-external-integrity.json`, `external-product-replay.json` |
| Walkthrough wheel, cinco escenarios más revocación/repetición | PASS; bytes repetidos idénticos y fuente intacta | `output/v145/wheel-historical-walkthrough/walkthrough.json` |
| Walkthroughs instalados desde sdist | PASS histórico y drift | `output/v145/sdist-history-walkthrough/walkthrough.json`, `sdist-drift-walkthrough/walkthrough.json` |
| Ejemplos offline | PASS; exit1 analítico esperado en casos negativos | `output/v145/examples.log` |
| Bloqueo de red | DNS y creación/conexión de socket rechazados por `OFFLINE_GUARD` | `output/v145/offline-enforcement.json` |
| Conservación del padre | PASS; 126 archivos exactos | `output/v145/preservation.json` |
| Reproducción pública de carga histórica | PASS; 83 archivos / 721.436 bytes idénticos | `output/v145/original83-reproduction.json` |
| Fuente exacta y commit de entrega | PASS | `output/v145/delivery-source.json`, `delivery.json` |

Único SKIP: `tests/test_historical_explorer_bundle.py:560`, el SO no concede
crear una junction. No se altera esa prueba ni se declara ejecutada. No quedan
fallos locales sin resolver. No se ejecutaron suites completas adicionales bajo
todas las permutaciones; wheel/sdist y 3.12 tienen sus verificaciones indicadas.
La CI nueva de seis plataformas permanece **NOT EXECUTED**, a cargo del propietario.

## I. Aceptación mínima del propietario

| Prioridad | Objetivo | Path exacto existente | Inspección | Resultado esperado |
|---|---|---|---|---|
| P0 | Corpus, procedencia y gaps | `docs/development/v14-05-corpus-coverage.md` | Matriz, derechos, hashes y distinción sintético/externo | Siete familias; Modbus/DCP/IEC104 externos pendientes |
| P0 | Oracle independiente | `tests/fixtures/protocol-corpus/v145-tshark-receipt.json` | Versión, flags, input SHA y joins con `v145-cases.json` | 36 campos positivos coinciden; negativos no se elevan |
| P0 | Framing hostil y recursos | `output/v145/focused.xml` | Casos `test_v145_interoperability` y límites de bundle | Rechazo/abstención explícitos; sin publicación exitosa parcial |
| P0 | Lifecycle/drift/replay | `output/v145/wheel-historical-walkthrough/walkthrough.json` | Repetición, reinterpretación, incompleto y autoridad fresca | Reproducción exacta, fuente intacta, revocación visible |
| P0 | Nativo y HTML aprobado preservados | `output/v145/native-compatibility/comparison.json` | Pins, 110 artefactos y 13 HTML exactos | PASS; verificador sin cambios |
| P1 | Rendimiento comparado | `benchmarks/receipts/v14-05-windows.json` | Bytes/cargas iguales, rangos, memoria y filas más lentas | Coincidencia canónica; ninguna promesa industrial |
| P0 | Paquetes y CI-readiness | `output/v145/delivery-archive-audit.json` | Inventarios exactos; bytes externos excluidos | Wheel/sdist y fuente coherentes |
| P0 | Pruebas, SHA final y árbol | `output/v145/delivery.json` | Fuente exacta, suite y Git status | 4.272 PASS/1 SKIP; commit local limpio |

No se solicita otra auditoría visual global: los renderers y la presentación
aprobada no cambiaron. Los HTML generados para walkthroughs/medición son recibos
de las mismas vistas, no una nueva experiencia que requiera aceptación visual.

## J. Documentación, compatibilidad y trabajo diferido

Se agregan builder/corpus/recibo independientes, cuatro archivos de pruebas,
un benchmark de protocolo con latencia y allocations separadas, el recibo compacto
y cinco documentos V14-05. Se actualizan registro de corpus, cifra de aprobación,
CI, progreso e inventarios públicos. `MANIFEST.in` se alinea además con cinco
archivos que ya estaban en el inventario público. La auditoría exacta de los
archivos fuente/paquete, no una suposición sobre setuptools, establece aceptación.
El listado exhaustivo está en `git diff --name-only d898516e24dec922179696e4cb50a262b3466a46 HEAD`.

Sin nuevas dependencias, soporte de linktype, revisión de decoder, esquema,
interpretación nativa, infraestructura de seguridad genérica ni cambio visual.
Sólo se redistribuyen bytes sintéticos originales y metadata segura de oracles.
Los ocho PCAP externos conservan redistribución desconocida y permanecen locales.
La falta de un grant específico y de bytes pequeños autorizados justifica retener
las tres brechas externas, en lugar de convertir sintéticos en evidencia externa.

V14-06 recibe consolidación de release, revisión de propietario y resultado de
CI, sin obligación inventada de agregar protocolos o linktypes. La investigación
externa futura debe preservar originales, revisar derechos/tamaño/sensibilidad
y distinguir laboratorio de planta. La campaña adversarial pública previa a v1.5
mantiene su alcance propio; no se declara satisfecha por estos casos finitos.

## K. Publicación por el propietario

Comprobar primero el SHA en `output/v145/delivery.json` y el árbol limpio.
Los siguientes comandos son instrucciones; **no se ejecutaron**:

```powershell
git switch codex/v14-05-corpus-interoperability-hardening
git rev-parse HEAD
git status --short
git push --set-upstream origin codex/v14-05-corpus-interoperability-hardening
gh pr create --draft --base codex/v14-04-historical-explorer --head codex/v14-05-corpus-interoperability-hardening --title "V14-05: independent industrial corpus and evidence integrity hardening" --body-file output/v145/pr-body.md
```

La descripción preparada en `output/v145/pr-body.md` explica el problema,
resultado, validación y límites. Si no está instalado `gh`, usar los mismos
base/compare/título y esa descripción en GitHub. No modificar el Draft PR del
padre. Tras publicar, comprobar los seis trabajos del **SHA final del candidato**;
el éxito del padre no concede aceptación al hijo.
