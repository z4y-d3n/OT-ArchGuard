# OT-ArchGuard V14-01 — entrega local

Fecha: 26 de octubre de 2026. Desarrollo local, sin publicación ni aprobación de
release. Este documento consolida capacidades, evidencia ejecutada y límites.

## A. Resultado ejecutivo

Se implementaron los cinco decodificadores pendientes: EtherNet/IP con CIP
limitado, S7comm clásico, IEC-104, OPC UA Binary y DNP3 con CRC obligatorio.
Junto con Modbus TCP y PROFINET DCP existen siete subconjuntos pasivos y acotados.
Se integraron despacho, validación estricta de campos, límites, referencias de
paquete, CLI, documentación e inventarios de distribución.

El enriquecimiento conserva esquema 1 y emite revisión de decodificador 2.
El consumidor acepta estrictamente la revisión 1 con su inventario original;
no permite introducir protocolos nuevos mediante un simple rehash. No cambian
observación 2, captura 1, asociaciones 1, comparación nativa 1, catálogo 1 ni
YAML 1. No se crean activos, autorizaciones, asociaciones aprobadas ni cambios de
alcanzabilidad a partir de cabeceras industriales.

Se adquirieron ocho capturas externas pequeñas desde repositorios de pruebas
de CISA ICSNPP. Cinco permitieron comprobar cuatro familias: 615 registros
estructurales y 2.194 comparaciones de campos contra TShark 4.6.7, sin diferencias.
Tres conservaron resultados explícitos de enlace no soportado. Sus bytes quedan
en `output/v14-external/`, ignorados por Git; ninguna se redistribuye. No existe
evidencia suficiente para atribuirlas a plantas industriales de producción.

## B. Matriz de siete protocolos

«Positivo» significa estructura del subconjunto documentado; nunca autenticidad,
autorización, comunicación exitosa ni ejecución de una operación.

| Protocolo | Subconjunto implementado | Pruebas positivas | Pruebas negativas | Captura externa probada | Decodificador independiente | Casos conocidos fuera de alcance | Estado |
|---|---|---|---|---|---|---|---|
| Modbus TCP | MBAP y formas PDU existentes, puerto 502 | Solicitudes/respuestas/excepciones; compatibilidad V14-00 | Longitudes, funciones, división, falsos puertos, mutación | No; bytes externos autorizados pendientes | TShark 4.6.7 sobre fixture original | Reensamblado, funciones no incluidas, valores | Implementado y sintético PASS; externo pendiente |
| PROFINET DCP | Ethernet/VLAN; Get, Set, Identify compatibles | Fixture Identify y pruebas existentes | FrameID ajeno, TLV, servicios, truncamiento | No; permiso por captura pendiente | TShark 4.6.7 sobre fixture original | Hello, otros servicios/FrameID, datos de configuración | Implementado y sintético PASS; externo pendiente |
| EtherNet/IP / CIP | Cabecera 24 B, comandos allowlist, CPF; CIP genérico de SendRRData | Comandos y solicitudes/respuestas CIP; encapsulación conectada opaca | CPF anidado, EPATH, versiones, ListIdentity, longitudes, respuestas | Dos PCAPNG: dos positivos de encapsulación | TShark: dos comandos comparados; CIP conectado deliberadamente opaco | UDP/implicit I/O, tags, múltiples servicios internos, perfiles conectados | Implementado; sintético PASS; externo parcial PASS |
| S7comm clásico | TPKT/COTP clase 0, ROSCTR, SetupCommunication, ReadVar, WriteVar | Solicitudes/respuestas, ACK y error vacío | COTP, TPKT parcial, ROSCTR, S7-plus, datos/longitudes | Snap7: 11 positivos; 53 variantes no soportadas. Mixto S7-plus: enlace no soportado | TShark: 21 comparaciones de ROSCTR/función | Programación, userdata, otros tipos de variable y COTP fragmentado | Implementado; sintético PASS; externo parcial PASS |
| IEC-104 | I/S/U; seis controles U y ASDU de formas explícitas | I/S/U, coalescencia y ASDU completos | Controles combinados, ASDU desconocido, longitudes, división, COT reservado | No; falta referencia autorizada pequeña | TShark 4.6.7 reconoce U STARTDT_ACT sintético | ASDU no incluidos, semántica COT/tipo, reensamblado | Implementado y sintético PASS; externo pendiente |
| OPC UA Binary | HEL/ACK/ERR/RHE; OPN/MSG/CLO como envolturas opacas | Handshakes completos; MSG F/C; OPN/CLO F | Tamaños, marcadores, abort A, prefijos, strings/certificados acotados | Ethernet gap/handshake: 237 positivos, 171 hints, tres truncados; dos NULL no soportados | TShark: 711 campos coinciden | Servicios, NodeIds, URLs exportadas, contenido cifrado, abort, reensamblado | Implementado; sintético PASS; externo parcial PASS |
| DNP3 TCP | Link con CRC de cabecera y cada bloque; aplicaciones completas limitadas | Link/confirm/read de clases/restart/respuestas | CRC, dirección, longitud, fragmentación, funciones desconocidas | 365 positivos; 469 no soportados en 834 paquetes | TShark: 1.460 campos coinciden; sin banderas CRC incorrecto | SELECT/OPERATE, write, SA, fragmentos de transporte/aplicación, UDP | Implementado; sintético PASS; externo parcial PASS |

Todas las familias conservan abstenciones ante fragmentación IP, truncamiento
de captura y enlaces exteriores no soportados. El bridge soporta Ethernet hasta
dos VLAN, IPv4 y IPv6 directo con TCP, y DCP L2; no convierte NULL/SLL ni reconstruye
TCP. La selección usa puertos estándar y precedencia determinista, sin búsqueda
especulativa dentro de datos arbitrarios. El modo explícito Modbus existente se
conserva. Los contadores separan positivo, hint, truncado, malformado y no soportado.

Subconjuntos y referencias primarias:
[EtherNet/IP/S7](v14-enip-s7.md), [IEC104/OPC UA/DNP3](v14-iec-opc-dnp.md),
[contrato común](v14-enrichment-contract.md).

## C. Corpus real externo y derechos

Los archivos proceden de `testing/traces/` en estos commits:

- [ICSNPP ENIP](https://github.com/cisagov/icsnpp-enip/tree/3fbd32e3d2838d5e2bcd6c9ed79f036d23a0642e): `3fbd32e3d2838d5e2bcd6c9ed79f036d23a0642e`.
- [ICSNPP S7comm](https://github.com/cisagov/icsnpp-s7comm/tree/102a35c8f967f20640bd2427bb28a7c609b37493): `102a35c8f967f20640bd2427bb28a7c609b37493`.
- [ICSNPP OPC UA](https://github.com/cisagov/icsnpp-opcua-binary/tree/d7fd8894d23baabcaf59989abc3cbab6b469c074): `d7fd8894d23baabcaf59989abc3cbab6b469c074`.
- [ICSNPP DNP3](https://github.com/cisagov/icsnpp-dnp3/tree/b31dbadeceb1cbcda16aef89c650559cd177dd7e): `b31dbadeceb1cbcda16aef89c650559cd177dd7e`.

Se revisaron las licencias BSD-3-Clause y avisos Battelle de los repositorios.
No se estableció por separado el autor original ni un permiso de redistribución
por captura. Las ocho son Tier 3, aprobadas para análisis local; redistribución
**desconocida/no aprobada**. Las atribuciones y avisos aplicables deben preservarse
si posteriormente se obtiene un permiso. La revisión de sensibilidad se limita a
contenedores/cabeceras y metadatos retenidos; no certifica la ausencia de datos
sensibles dentro de los originales.

| Archivo original / origen | Bytes reales | SHA-256 calculado | Resultado de referencia y producto / expectativa negativa |
|---|---:|---|---|
| `multiple_service_packet_cip.pcapng` / ENIP | 344 | `4eed29d01d6fe3c827e3c947694526e7669d937ff8973d5c420979565597087c` | Un encabezado TShark y un positivo de encapsulación; no interpretar CIP conectado |
| `set_attribute_single_service_cip.pcapng` / ENIP | 500 | `9b24d02e6f15a40f2109c2476bb117e2273bc9485077a50044269d3738cea8dc` | Un encabezado TShark y un positivo; no inferir escritura ejecutada |
| `snap7.pcap` / S7 | 8.260 | `2b91f6a8a203ec83e4f2dbb69d5e61602845f23da0baa31d95d029fb24cbd427` | TShark 64 cabeceras; producto 11 positivas, 33 funciones y 20 userdata no soportados |
| `s7comm_plus.pcap` / S7 | 33.464 | `2f9befe0667443fb86b7184b6ff7fcc4eb61fae67d3ce30793ce7b2937067b0c` | TShark 34 cabeceras clásicas; producto 262 omisiones SLL; no declararlo negativo S7-plus puro |
| `open62541_client-server_mainloop.pcap` / OPC | 22.412 | `07dd69db7de730928601e4f66d94382d94257a344ae3a5f9147b7dec108bcefd` | TShark 66 cabeceras; producto 154 omisiones NULL, sin PASS de interoperabilidad |
| `open62541_client-server_mainloop-no-handshake-12345.pcap` / OPC | 17.159 | `da507c9d8798e978ef452efa761da3ab8a3b28c5ad9cb68c150edfb27c7619a9` | TShark 54 con decode-as explícito; producto 113 omisiones NULL; no atribuirlo únicamente al puerto |
| `dnp3_example.pcap` / DNP3 | 115.403 | `d9b22ee7b5ece4a78d8f9995aff20d55bfb315752ce136f97c77eb5ce73511bf` | 834 cabeceras TShark; 365 positivas, 267 funciones y 202 fragmentos no soportados |
| `opcua_with-gap_with-handshake.pcap` / OPC | 83.524 | `030950345b2c79eaf3bedf8a04c2325cfe4a5d8b40225d250ed693daf350b6b6` | TShark 240 cabeceras; producto 237 positivas, 171 hints, tres truncadas; no reconstruirlas |

Herramienta independiente: `TShark (Wireshark) 4.6.7 (v4.6.7-0-gb439fb7b47a9)`.
Desegmentación TCP/ENIP/DNP3 desactivada. Las comparaciones se unieron por número
de paquete original, sin normalizar ni convertir capturas. Cero discrepancias
observadas en los campos emitidos no implica cobertura total ni cero falsos
negativos: los casos no soportados se registran por separado.

Los recibos comprometidos son
`tests/fixtures/protocol-corpus/external-tshark-receipts.json` y
`external-product-receipts.json`; contienen identidades reales, argumentos,
ejemplos acotados, resultados y hashes de fuentes del protocolo. El replay con
fuentes finales produjo igualdad completa con el recibo comprometido.

Bloqueos de otros candidatos: PCAP4SICS es laboratorio y su menor archivo ronda
25 MB, por encima del límite de 16 MiB; ICS_PCAPS de Coimbra declara CC-BY 3.0 y
citación, pero sus ZIP revisados son de 194–670 MB y no se extraen automáticamente;
Wireshark DCP/IEC104 carece de permiso/collector por archivo establecido en esta
revisión; automayt tiene derechos mezclados sin licencia suficiente y el Modbus
inspeccionado era un puntero LFS. No hay capturas IEC104 en el árbol lib60870
inspeccionado ni un submódulo IEC104 en el ICSNPP revisado. La
[revisión detallada](v14-external-corpus.md) preserva revisiones, enlaces e
instrucciones manuales precisas. No se declara validación externa para esas familias.

El descargador optativo `tools.protocol_external` solo admite ocho entradas con
HTTPS, revisión, hash y tamaño exactos. Requiere `--allow-network`, rechaza
redirecciones, límites, rutas inseguras, LFS, sobrescritura y archivos no revisados;
publica localmente sin reemplazo. No extrae archivos ni se invoca desde runtime
o tests ordinarios. La adquisición real del ejemplo de 344 bytes se reprodujo.

## D. Calidad de ingeniería y mediciones

Plataforma local: Windows 11 AMD64, Python 3.14.5. Instalaciones regulares en
`.venv-v141-wheel` y `.venv-v141-sdist`, sin instalación editable ni importación
de `src` durante las suites completas; red Python denegada en procesos hijos.

| Gate local | Resultado ejecutado | Recibo en `output/` |
|---|---|---|
| Suite completa wheel | 3.380 PASS; 0 fallos/errores/skips; 711,66 s | `v141-final-wheel-suite.xml` |
| Suite completa sdist, entorno separado | 3.380 PASS; 0 fallos/errores/skips; 728,38 s | `v141-final-sdist-suite.xml` |
| Foco V14-00/V14-01 | 565 PASS; 9,41 s | `v141-final-focused.xml` |
| Ruff / formato | PASS | Ejecución local; 0 errores |
| Mypy estricto | PASS; 194 archivos | Ejecución local; 0 errores |
| `pip check` | PASS en ambos entornos y `.venv` restaurado | Sin dependencias rotas |
| Compatibilidad nativa inmutable | PASS; 124 archivos; solo excepciones originales CLI/reachability | `v141-final-native-compatibility/comparison.json` |
| Lectores congelados supported/limited | Ambos PASS | `v141-final-reader-*.json` |
| Walkthroughs evidence/capture/project/Explorer/document/quality y ejemplos | Todos PASS con instalaciones finales y offline | `v141-final-*-walkthrough/walkthrough.json`, `v141-final-examples.log` |
| Fuente y paquetes | PASS; inventarios explícitos y módulos instalados iguales a fuentes | `v141-delivery-source-checkout.json`, `v141-delivery-archive-audit.json`, `v141-final-*-environment.json` |

Los tests ejercitan fuente/producto congelados en el commit `450f552`; el commit
posterior solo incorpora esta entrega, guías e inventarios. La auditoría de
entrega se repite sobre ese último árbol para incluir toda la documentación, sin
cambiar fuentes Python, tests, fixtures ni resultados históricos.

Inventario final: 3.380 tests únicos, de los cuales 388 se agregan sobre
los 2.992 de V14-00. Incluye 239 casos de decodificadores nuevos, 58 de auditoría
cruzada, 56 de integración, 18 de identidad y 17 de corpus externo. Los runs
solapados o repetidos no se suman como tests únicos.

Las auditorías independientes corrigieron versión/familia/padding ListIdentity,
marcadores OPN/CLO y mínimos de cuerpos OPC UA. La suite detectó el cambio de
import en reconciliación; se restauraron los bytes originales, sin modificar
`CORE_SHA256` ni fixtures. La revisión de identidad detectó `None` en campos
obligatorios del probe; ahora se rechaza junto con tipos incorrectos.

Un run preliminar, anterior al freeze final, terminó con 3 fallos y 3.374 pases:
el hash de fuente indicado, una aserción de inventario que cambió mientras ese
proceso ya había cargado el test, y un acceso transitorio denegado de Windows al
publicar un fixture local. No se usa ese run como aceptación. Los runs finales
se ejecutan con fuentes congeladas y entornos nuevos separados; sus resultados
se registran en la tabla final, sin sumar ejecuciones repetidas.

Se preservan bytes congelados de observaciones/capturas, parser, contrato y
reconciliación. El comparador histórico no cambia. Las excepciones de la prueba
de versión son sustituciones exactas de identidad de producto/API, sin cambiar
evaluaciones esperadas ni permitir modificaciones arbitrarias de tests.

[Mediciones reproducibles](v14-protocol-performance.md): con 7.000 paquetes
mixtos, entrada 575.024 B, JSON 8.519.687 B, 3,106 s trazados, pico Python
27.794.655 B y RSS histórico del proceso 84.889.600 B. Para 1.000 registros por
familia, JSON entre 1.048.548 y 1.397.642 B. Una carga de 21.000 paquetes fue
rechazada por el techo de bytes de metadatos sin artefacto parcial. No se afirma
haber alcanzado primero el techo de registros. RSS no es un delta aislado y
tracemalloc no equivale a RSS; son observaciones finitas, sin promesa de capacidad.
No se elimina trazabilidad ni se cambia silenciosamente el formato para comprimirlo.

La captura sintética original de siete paquetes mide 599 B y tiene SHA-256
`2d2523670c7992c33d64599ceff9e854d44ebd814a2c9253e3c7867803cfe9fa`.
TShark 4.6.7 reconoció las siete familias en sus paquetes respectivos; para IEC104
informó `iec60870_104.type=0x00000003` y `utype=0x00000001`, coherentes con U
STARTDT_ACT. Es evidencia sintética independiente adicional, no una captura externa.
Los resultados locales quedan en `output/v141-seven-tshark.txt` y
`output/v141-iec-tshark.txt`. Se reproduce sobre `mixed-7.pcap` generado por el
benchmark con `-n -o tcp.desegment_tcp_streams:FALSE -T fields -e frame.number
-e frame.protocols -e iec60870_104.type -e iec60870_104.utype`.

## E. Decisiones de arquitectura

- Producto/CLI/distribución: `DISTRIBUTION_VERSION = 1.4.0.dev1`.
  Motor nativo: `NATIVE_ENGINE_VERSION = 1.3.0`. La API histórica `__version__`
  sigue siendo alias del motor para conservar fuentes congeladas; para conocer
  el producto usar metadata de distribución, la constante explícita o el CLI.
  Los archivos modificados no se presentan como release estable v1.3.0.
- Enriquecimiento: esquema 1/revisión 2, lector estricto de revisiones 1 y 2.
  Workspace/snapshot siguen en 1, sin migración automática ni extensiones ocultas.
- Identidad física: captura SHA-256. Identidad analítica: todos los hashes de
  observación/enriquecimiento/modelo/mapping/comparación/política y semántica del
  productor. Identidad de revisión/baseline: decisión humana separada, acotada a
  esos inputs. Reanalizar una captura no crea otra colección independiente.
- Solo se añade un probe experimental en `tools/evidence_identity.py`, sin API
  de almacenamiento, aprobación ni ingestión. V1 conserva `DUPLICATE_CAPTURE`.
  [ADR de versiones](v14-version-identity-adr.md) y
  [ADR de revisiones analíticas](v14-analysis-revisions-adr.md).

## F. Git, CI y acción del propietario

Rama: `codex/v14-01-industrial-protocols-and-corpus`, derivada de
`3201f5d39db4c9bb4fbd565dd62fcc28145800b4`, no de main.
Base remota revisada: main `1febf7a864c074d2a3d3ac78005ea1bf2853009a`.
Tag estable v1.3.0: `10d7de6c416ec6f0ee364c671ebe9292ee69e672`.

Commits locales de implementación (el posterior commit documental cierra esta entrega):

- `d12bd874aebaa75d1d5ffc29ce92bdb1f989bfd8`: siete decodificadores, corpus, tests, ADR e integración.
- `e9a9f2eed7384a10fd0db88d5c1ca2cf5cd9f097`: bytes LF del descargador de desarrollo.
- `450f552dba21b357a27b22e2caf6781b0d8a900d`: separación compatible de versión, fuentes nativas intactas y probe estricto.

El estado final del árbol Git es limpio; resultados generados, entornos y bytes
externos permanecen ignorados. Son 48 archivos cambiados respecto del checkpoint
V14-00; ningún archivo Python/test cambia después del commit de implementación
verificado. Los commits de V14-00 y el tag estable se conservaron sin reescribirlos.

La lista exacta de archivos se obtiene con
`git diff --name-only 3201f5d39db4c9bb4fbd565dd62fcc28145800b4..HEAD`.
Los cambios cubren decodificadores/validadores, fixtures sintéticos originales,
recibos sin payload, corpus de desarrollo, tests, benchmarks, CLI/versiones,
inventarios explícitos y documentación. No incluyen PCAP externos.
El árbol de entrega final comprende 395 archivos públicos; los inventarios
`MANIFEST.in` y `tools/public-files.txt` enumeran el contenido permitido.

El [Draft PR #17](https://github.com/z4y-d3n/OT-ArchGuard/pull/17) seguía abierto,
draft y sin merge en el head original verificado. Sus seis jobs pasaron en
[run 40369757990](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40369757990).
Eso valida V14-00, no estos commits. La matriz CI de seis configuraciones no se
modificó. V14-01 no tiene CI hospedado porque no se autorizó publicación remota.
No se ejecutaron push, merge, tags, PR nuevos, releases ni cambios remotos.

Acción recomendada: revisar esta rama y sus límites; si el propietario autoriza
publicarla, ejecutar los seis jobs sobre su head exacto y revisar los artefactos
antes de una decisión de integración. No actualizar silenciosamente el Draft #17.

## G. Handoff priorizado de V14-02

1. Fijar contratos de attachments con validación acotada y joins exactos a
   captura, observación, enriquecimiento, arquitectura y mapping revisado.
2. Especificar un workspace nuevo con revisiones analíticas separadas de
   colecciones, manifiesto de semántica del productor y migración explícita a
   destino nuevo; conservar todos los objetos v1 sin reescribirlos.
3. Implementar decisiones humanas acotadas y baselines seleccionados por el
   propietario, con supersesión/revocación y sin transferir aprobación cuando
   cambian inputs. Definir denominadores por colección y cobertura compatible.
4. Auditar rehash malicioso, joins obsoletos, fragmentos ausentes, duplicados,
   versiones desconocidas, límites e interrupciones antes de exponer comandos.
5. Completar referencias externas autorizadas para Modbus/DCP/IEC104 y mantener
   los casos actuales no soportados. Comparación histórica, drift y Explorer
   siguen siendo hitos posteriores. El freeze final y CI hospedado continúan
   siendo requisitos previos a cualquier release.

## Inventario exacto de archivos cambiados

```text
CHANGELOG.md
MANIFEST.in
README.md
benchmarks/protocols.py
docs/development/v14-01-handoff-es.md
docs/development/v14-analysis-revisions-adr.md
docs/development/v14-architecture.md
docs/development/v14-enip-s7.md
docs/development/v14-enrichment-contract.md
docs/development/v14-evidence-contract.md
docs/development/v14-external-corpus.md
docs/development/v14-iec-opc-dnp.md
docs/development/v14-progress.md
docs/development/v14-protocol-corpus.md
docs/development/v14-protocol-performance.md
docs/development/v14-version-identity-adr.md
docs/v14-foundation.md
pyproject.toml
src/otarchguard/__init__.py
src/otarchguard/capture/cli.py
src/otarchguard/capture/protocols/__init__.py
src/otarchguard/capture/protocols/dnp3.py
src/otarchguard/capture/protocols/enip.py
src/otarchguard/capture/protocols/header_validation.py
src/otarchguard/capture/protocols/iec104.py
src/otarchguard/capture/protocols/opcua.py
src/otarchguard/capture/protocols/s7comm.py
src/otarchguard/capture/protocols/validation.py
src/otarchguard/cli.py
tests/fixtures/protocol-corpus/external-product-receipts.json
tests/fixtures/protocol-corpus/external-tshark-receipts.json
tests/fixtures/protocol-corpus/manifest.json
tests/test_cli.py
tests/test_protocol_corpus.py
tests/test_protocol_enip_s7.py
tests/test_protocol_external.py
tests/test_protocol_iec_opc_dnp.py
tests/test_release_candidate.py
tests/test_v141_cross_audit.py
tests/test_v141_enip_s7_audit.py
tests/test_v141_identity.py
tests/test_v141_protocol_integration.py
tools/evidence_identity.py
tools/protocol_external.py
tools/protocol_workloads.py
tools/public-files.txt
tools/verify_environment.py
tools/verify_legacy_candidate.py
```
