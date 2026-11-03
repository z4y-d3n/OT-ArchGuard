# V15-01 — Entrega al propietario

**READY_FOR_OWNER_REVIEW**. Se completó el gate local con correcciones acotadas,
regresiones, mediciones reproducibles e inspección independiente sin bloqueantes.
La suite completa terminó con 4.387 PASS, 0 FAIL, 0 ERROR y 1 SKIP; ese caso de
junction pasó en una ejecución focalizada separada. v1.4.0 continúa como versión
pública estable. Este resultado no autoriza integración ni publicación de v1.5.

## Identidades y alcance

Base limpia: `c5ada13871043ed52cd43557bc7b222399f7b7eb`, `main` con upstream
`origin/main`. Fuente publicada v1.4.0:
`7d6b158f863308dfcd7d10b673bfbe2692f29b8b`. Rama local:
`codex/v15-01-product-consolidation-foundation`. Distribución/CLI `1.4.0`, motor
nativo `1.3.0`, esquema YAML `1`. No se modifica la versión porque el verificador
actual fija los 97 módulos y sólo admite la transición histórica ya aprobada.
V15-02 deberá revisar expresamente una nueva transición antes de cambiar runtime.

Implementación verificada y empaquetada: commit limpio
`b3bc51271c94a67d01aa8328aa215d4dbea45673`, inventario público SHA-256
`84475e753c15cab9a653c3e202ad3d0ebdf914a7e56380b8882e58703f36fc9a`.
La entrega añade después sólo documentación/evidencia/inventario, con auditoría
propia de fuente y paquetes. El HEAD final exacto figura en el mensaje de entrega
y en `output/v15-01/final-packages/`; no se atribuye una nueva suite completa a ese
commit documental. `git rev-parse HEAD` lo muestra sin ambigüedad. La rama local
no tiene upstream hasta que el propietario ejecute el push autorizado por él.

## Cambios y auditorías

| Cambio | Motivo | Verificación |
|---|---|---|
| Preflight compartido de tres tutoriales históricos | Padre inexistente/destino ocupado producía traceback | Regresiones de salida 2, mensaje útil y preservación de datos |
| Requisitos de tutoriales y guía de instalación actual | Comandos incompletos desde sdist limpio y referencia 1.3.0 desactualizada | Revisión de enlaces y recorrido con paquete instalado |
| Trigger `codex/v15-*` | Publicar esta rama no activaría CI de push | YAML real, patrón de rama y matriz de seis jobs |

Agente A: arquitectura, contratos y fallo doble de E/S. Agente B: cuatro
recorridos, documentación y seis reproducciones de UX. Agente C: línea base
repetida con fixtures deterministas. Agente D: paquetes e instalaciones nuevas.
Agente E: revisión crítica independiente después de integrar. Sus conclusiones
y límites se detallan en los documentos del dossier.

Se añadieron **16 pruebas únicas**: las tres CLI ante padre ausente, padre que es
archivo, archivo/directorio existente, preservación de marcador e inventario,
destino relativo válido y trigger/matriz CI. No se alteraron pruebas históricas
ni expectativas analíticas. Se ejecutaron de nuevo desde el wheel y desde el
sdist extraído; esas repeticiones no son pruebas únicas adicionales.

Archivos: helper y tres mains en `tools/`; regresiones en
`tests/test_v15_foundation.py`; workflow CI; nuevo `benchmarks/foundation.py` y
receipt; cuatro guías de uso más testing/changelog; seis documentos de este
dossier y su receipt JSON; inventarios `MANIFEST.in` y `tools/public-files.txt`.
`src/`, `pyproject.toml`, fixtures congelados, verificador, licencias y capturas
históricas permanecen intactos.

## Evidencia ejecutada

| Control | Resultado real |
|---|---|
| Suite completa, wheel regular nuevo, Windows/CPython 3.12.14 | 4.387 PASS / 0 FAIL / 0 ERROR / 1 SKIP; 4.388 casos únicos; 824,39 s |
| Junction omitida por permisos del sandbox | 1 PASS separada fuera del sandbox, rutas temporales dentro del output; mismo caso |
| Regresiones focalizadas wheel / sdist extraído | 16 PASS en cada uno; sin fallos/errores/skips; conteos superpuestos |
| Ruff lint/formato, mypy estricto, pip check | PASS; 409 archivos revisados de formato / 266 de tipos |
| Compatibilidad nativa/presentación | PASS; 124 artefactos, 110 analíticos, 13 apéndices HTML JSON, 54 archivos de tests históricos comprobados |
| Consumidores congelados supported/limited | Ambos exit 0 |
| Instalaciones nuevas | Wheel, sdist aislado y sdist con backend preparado: PASS; 97 módulos equivalentes |
| Primer reporte desde fuera del checkout | PASS en los tres entornos; versión, imports y dependencias verificados |
| Tutoriales reales desde el sdist extraído | Lifecycle, drift y Historical Explorer: PASS |
| Auditoría E | Sin hallazgos bloqueantes; corroboró hashes, JUnit, paquetes, contratos y mediciones |

Receipt compacto: [v15-01-evidence.json](v15-01-evidence.json).
Logs/JUnit/entornos y recibos detallados: `output/v15-01/`, ignorado por Git.
La suite completa del sdist **no se repitió**: se comprobó independientemente su
identidad, las pruebas focalizadas y los tres tutoriales afectados. Tampoco se
repite ni se atribuye al harness tipado la matriz medida por el script original.

Se conservaron 41 comandos del ensayo de paquetes: 40 exitosos y un fallo inicial
de bootstrap por TEMP del sandbox. Se resolvió usando TEMP/TMP escribibles y
entornos nuevos; un NameError breve del driver local de recuperación también
consta en el recibo. No fueron defectos del producto ni motivo para cambiar tests.
La resolución de dependencias usó wheelhouse local y `--no-index`; no se ejecutó
instalación desde un índice online ni se afirma desconexión física. El entorno
conocido `.venv-v146-py312` conservó los 97 módulos.

## Línea base de rendimiento

24 cargas, 120 muestras sin tracing, warmup explícito y 22 ensayos separados de
asignaciones. Memoria de los dos procesos CLI hijos no medida; RSS es máximo de
vida del proceso compartido, no asignaciones Python ni RSS aislado por carga.
Fuente de medición `c5ada13871043ed52cd43557bc7b222399f7b7eb`, CPython 3.12.14,
Windows, 12 procesadores lógicos; identidades de fixtures y resultados registradas.
Módulos runtime iguales antes/después y en el candidato; no hay comparación
pareada ni afirmación de aceleración o ausencia cuantitativa de regresiones.

Medianas: Explorer arquitectónico pequeño/medio/grande 1,293/10,059/34,596 s;
captura 10.000 paquetes 0,359 s; siete protocolos/700 paquetes 0,052 s; drift512
3,127 s; replay512 4,950 s; Explorer histórico512 17,667 s; inicio CLI 0,580 s.
Escala512 es cardinalidad del productor ficticio, no 512 colecciones ni capacidad
máxima. [Metodología, dispersión, memoria y backlog](v15-01-performance.md).

## Contratos, límites y diferidos

No se cambian módulos de runtime, decodificadores, renderizadores, límites de
recursos, hashes históricos ni aprobaciones. Se conserva la operación pasiva,
offline y sin reensamblado TCP. No se han tocado assets publicados ni registros
de aceptación históricos.

La auditoría A reprodujo mediante inyección de fallos que un error al borrar un
temporal puede ocultar el diagnóstico de sustitución de reporte; el reporte
anterior se conserva. Es P2, diferido por el contrato de fuente congelada, sin
atribuir pérdida ordinaria de datos. El acoplamiento entre helpers privados
merece revisión posterior; no justifica un refactor general en este gate.

Las mediciones separan tiempo sin tracing, asignaciones de Python y RSS del
proceso. No hay optimización implementada ni promesa de aceleración.

El HTML histórico v1.2 no es idéntico al cambio semántico ya aprobado en v1.4;
la comparación con la presentación V14 aprobada sí pasa. No se alteró ninguna
excepción congelada para conseguirlo. Las revisiones de esta misma fuente estable
conservan productor; esto no concede replay transparente de revisiones dev1 ni
transfiere aprobaciones. Tampoco certifica protocolos, accesibilidad ni seguridad
industrial. Continúan las limitaciones documentadas, incluidas las validaciones
externas positivas pendientes.

E detectó dos riesgos de los recibos del nuevo harness; C corrigió antes del
freeze el registro de argv completo y los estados pendientes/error sin declarar
coincidencia prematura. E verificó después la correspondencia con el script
realmente medido y sus hashes.
El harness requiere el checkout Git revisado; el replay del benchmark desde un
archivo aislado no está soportado. Se difieren perfilado de Explorer/replay,
revisión de helpers privados y transición explícita de fuente/versionado.

## Revisión del propietario y Git

1. Inspeccionar el diff y este dossier; revisar los receipts y límites reales.
2. Abrir el primer reporte y los Explorers de captura/historia offline; comprobar
   teclado/foco, zoom 200%, ancho reducido, textos largos/IPv6 e impresión.
3. Publicar sólo la rama revisada si se acepta el trabajo; ejecutar los seis jobs
   del SHA exacto y exigir resultados reales antes de integrar.
4. Mantener entornos históricos compatibles y decisiones de aprobación separadas.

Desde `C:\Users\PC\Desktop\OT-ArchGuard-CLEAN`, ejemplos ya generados:

```powershell
Invoke-Item .\output\v15-01\first-report\index.html
$Extracted = Join-Path (Get-Location) 'output/v15-01/packaging/extracted/otarchguard-1.4.0'
$HistoricalSite = Join-Path $Extracted 'output/historical_explorer/normal'
$HistoryWorkspace = Join-Path $Extracted 'output/historical_explorer/sources/history'
Invoke-Item (Join-Path $HistoricalSite 'index.html')
$SdistConsole = (Resolve-Path 'output/v15-01/packaging/env-sdist-retry/Scripts/otarchguard.exe').Path
& $SdistConsole evidence drift explore-verify $HistoricalSite
& $SdistConsole evidence drift explore-verify $HistoricalSite --workspace $HistoryWorkspace
```

Recorrer Overview → dominio → hallazgo → evidencia → contexto; revisar también
`incomplete`, `decoder`, `revoked` y `dense`. Distinguir aprobación registrada de
estado actual revocado, integridad portable de reproducción y diferencias de
metadatos de cambios físicos. El navegador de la herramienta rechazó `file:`;
no se intentó un workaround. Quedan revisión humana de teclado/foco, zoom200%,
ancho reducido, identificadores largos/IPv6 donde corresponda, impresión y lector
de pantalla. Deben ejecutarse los seis jobs hosted para el HEAD final; sólo se
ejecutó Windows/Python3.12 localmente. Las otras combinaciones tienen revisión
estática de configuración e instrucciones, sin resultados inventados.

```powershell
git status --short --branch
git rev-parse HEAD
git log --oneline main..HEAD
git diff --stat main...HEAD
git diff main...HEAD
# Sólo el propietario, después de revisar:
git push -u origin codex/v15-01-product-consolidation-foundation
```

[Comparación para crear PR contra main](https://github.com/z4y-d3n/OT-ArchGuard/compare/main...codex/v15-01-product-consolidation-foundation?expand=1).
No se requiere GitHub CLI. Ninguna operación remota se ejecutará en este trabajo.

Objetivo recomendado V15-02: aprobar una transición de identidad/fuente de
desarrollo que conserve oráculos inmutables y límites de replay histórico,
antes de corregir runtime o introducir una versión 1.5 de desarrollo.
