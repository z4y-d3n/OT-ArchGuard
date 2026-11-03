# V15-02 — Entrega de ingeniería

## 1. Veredicto ejecutivo

**READY_FOR_OWNER_REVIEW**. V15-02 entrega una transición de fuente explícita,
distribución de desarrollo, lista vertical de limitaciones y corrección F06.
Las comprobaciones locales y la auditoría independiente respaldan este hito.
La revisión humana y CI alojado siguen pendientes. No es una versión estable.

## 2. Identidades Git inicial y final

Inicio limpio: `867516be2c274a12d251c89bc0310a441b91da45`, rama V15-01.
Base integrada: `b3adcc9de21dfff6ad58946028a241844ff88294`, árbol
`b2a2ec908d02cc36339a7a3d2d3cd736671db3e0`.
Suite completa: `762a9db78c01d3259617a6cfb040d45120f2bd41`.
Último código de verificación: `b007eb1841a12d92eecef1813a05ec8c3c7cdc3d`.
El cierre posterior sólo actualiza documentación; el SHA/árbol exacto entregado
consta en `output/v15-02/final-source.json` y en el mensaje de entrega.
Los 97 módulos de producción conservan los mismos bytes durante la campaña final.

## 3. Dependencia de V15-01

PR #26 figura integrado en GitHub. Se actualizó metadata mediante lectura y
`git fetch --no-tags origin main`, se comprobó la ascendencia del head revisado
y se avanzó `main` limpiamente. Su árbol coincide con la revisión V15-01.
V15-02 parte de ese `main` en `codex/v15-02-compatibility-evolution`; no depende
de una rama apilada sin integrar. Antes de publicar debe revisarse cualquier
avance posterior de `main`.

## 4. Arquitectura de compatibilidad

El [contrato](v15-02-compatibility-contract.md) separa el verificador histórico
V14, intacto y ejecutado sobre el predecesor, del nuevo verificador V15.
Éste deriva 97 módulos de un commit inmutable y fija cuatro hashes candidatos
revisables; no acepta autorización desde un manifiesto generado por el candidato.
Protege pruebas, fixtures, esquema y herramientas anteriores. Las dos literales
de distribución y una adaptación exacta de fixture histórico son excepciones
explícitas; ninguna expectativa analítica cambia.

Ejecutar con `python -I tools/verify_v15_transition.py --output output/NUEVO`.
El aislamiento excluye sombreado de biblioteca estándar; los bytes instalados se
comprueban antes de importarlos. El comparador compila bytes Git inmutables,
Git se resuelve fuera del checkout y prefijos de caché nuevos evitan `.pyc`
ajenos. `--source-only` informa explícitamente que no ejecuta replay histórico.
La revisión del propio verificador sigue siendo la raíz de autorización externa;
los hashes no constituyen firmas ni autentican autores.

## 5. Versiones

Distribución, metadata instalada y CLI: **1.5.0.dev1**. Motor nativo y alias
histórico `__version__`: **1.3.0**. YAML nativo: **1**. Captura, observaciones,
protocolos, revisión y drift conservan sus contratos/versiones anteriores.
La versión pública estable sigue siendo v1.4.0; no se creó v1.5.0 ni una etiqueta.

## 6. Producción modificada

Sólo cuatro módulos: `__init__.py` (distribución), `drift/explorer_render.py`
(lista local y revisión del renderer), `drift/explorer_bundle.py` (aceptación de
la nueva revisión) y `reporting.py` (precedencia diagnóstica).
No hay adiciones ni eliminaciones de módulos; otros 93 mantienen su hash.
Los hashes anteriores/candidatos completos constan en el contrato y en
`transition-final/transition.json`. Los cambios de herramientas, CI y documentos
son infraestructura revisable y no autorizan modificar otros módulos.

## 7. Major limitations

La causa era el flex compartido de `evidence-values`. La sección ahora usa un
`ul.major-limitations` con siete `li` escapados, marcadores nativos, sangría,
espaciado y ajuste de línea. El helper compartido permanece intacto.
La prueba literal conserva exactamente contenido/orden, enlaces, navegación,
JSON canónico y HTML ajeno a la sección frente al renderer Git independiente.
Identidad nueva: `1.5.0.dev1-historical-explorer.1`; digest de cinco fuentes:
`442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b`.
Las revisiones históricas `.1` y `.2` conservan integridad portátil.

## 8. F06

La inyección previa demostró que un `PermissionError` de limpieza ocultaba
`REPORT_IO_ERROR`; el CLI emitía `INTERNAL_ERROR`. El informe previo sobrevivía.
Ahora se capturan deliberadamente los dos fallos de I/O y se conserva el error
primario, código/categoría y salida CLI 2 sin stdout. La limpieza secundaria
añade contexto genérico sin rutas sensibles. Si sólo falla la limpieza tras
reemplazo correcto, se informa que el reporte ya fue escrito. No hay falsa
ausencia del archivo ni supresión genérica de excepciones. Un temporal puede
persistir si el sistema impide borrarlo; no se promete eliminación inexistente.

## 9. Pruebas y resultados reales

| Ejecución | PASS | FAIL | ERROR | SKIP |
|---|---:|---:|---:|---:|
| Suite completa, rueda regular, 980.25 s | 4439 | 0 | 0 | 1 |
| Mismo caso junction fuera del sandbox | 1 | 0 | 0 | 0 |
| Regresiones finales de V15-02 | 55 | 0 | 0 | 0 |
| Sdist instalado, regresiones y foundation | 71 | 0 | 0 | 0 |
| Sdist realmente extraído, I/O y foundation | 26 | 0 | 0 | 0 |

Son campañas superpuestas. La suite recolectó 4.440 casos; tres casos nuevos del
bootstrap se añadieron después y pasaron en campañas dirigidas. Hay evidencia
exitosa de los 4.443 casos únicos actuales, sin afirmar una ejecución completa
única de ese tamaño. El junction es el mismo caso inicialmente omitido.
Ruff, formato (421 archivos), mypy estricto (271), pip check y consumidores
congelados pasan. V14 y V15 verifican cada uno 124 artefactos; los 123 archivos
no manifiesto del candidato conservan bytes exactos del predecesor.

Se conservan el primer resultado dirigido 40 PASS/3 FAIL, la reproducción del
fixture 3 PASS/2 FAIL, una suite temprana interrumpida y fallos ambientales de
TEMP, desinstalación, caché y dependencias anidadas. Fueron corregidos y no se
presentan como PASS. Los [detalles](v15-02-acceptance.md) y recibos distinguen cada
fuente, cobertura y reejecución. El hook de red de pytest no equivale a aislamiento
físico; los padres `-I` ignoran `PYTHONPATH`, aunque su código aprobado opera offline.

## 10. Referencias históricas preservadas

Nativo `f52c792b683cb499dc7de765b65b5cc897a96854`; presentación V14
`117318393ead604a023a24bad7d53eb429faa13f`; fuente publicada
`7d6b158f863308dfcd7d10b673bfbe2692f29b8b`. La etiqueta anotada v1.4.0
`4821b751eb4963018b0e68edadb85f351e5dfbb4` sigue apuntando a esa fuente.
No se reescribieron revisiones, aprobaciones, manifiestos, bundles previos,
fixtures u oráculos para hacer pasar este gate.

## 11. Fronteras del replay

`evidence/revisions.py` vincula 34 fuentes, incluida `__init__.py`. La nueva
distribución crea otro productor y otras revisiones aunque el cálculo nativo
sea equivalente. El consumidor nuevo rechaza revisiones antiguas con
`EVIDENCE_REVISION`; el entorno original las reproduce y conserva sus archivos.
Integridad portátil no significa replay, autoría ni aprobación actual.
Las mismas capturas/snapshot físicos originaron IDs analíticos y reviews distintos
en la campaña pareada. No se transfirió autoridad ni se atribuyó el cambio de
productor a tráfico físico. No se promete migración universal.

## 12. Paquetes e instalaciones

Rueda y sdist de desarrollo se construyen con setuptools, auditando inventarios,
metadata, RECORD, licencias, entrada CLI, dependencias y 97 hashes instalados.
Se usan entornos regulares separados; el entorno conocido de v1.4 se conserva.
Ejemplos, proyecto, captura, Architecture Explorer e Historical Explorer funcionan
desde el sdist extraído. No se repitió localmente toda la suite del sdist: se
verificó identidad exacta y flujos/pruebas afectados; CI conserva ambas suites
completas. Los archivos finales/instalaciones se vinculan en
`output/v15-02/final-packages/`; los recibos ignorados no se distribuyen públicamente.

## 13. Rendimiento

Windows/CPython 3.12.14; escala ficticia 512; un calentamiento y tres muestras
sin instrumentación por operación, antes/después secuenciales. Todas las versiones
de dependencias resueltas coinciden salvo OT-ArchGuard. Medianas: generación
18.2093 → 18.2000 s; replay 5.0574 → 5.0196 s; escritura de 1 MiB
3.098 → 2.338 ms; arranque CLI 0.7308 → 0.7209 s.
No se observa regresión material. No se afirma optimización por diferencias
submilisegundo; no se comparó memoria. La primera campaña contaminada por trabajo
concurrente/fallo ambiental se conserva y se descarta como comparación.

## 14. Especialistas y auditor independiente

A: política inmutable y productores; B: renderer/UX y siete afirmaciones;
C: reproducción F06 y matriz adversarial; D: paquetes, CI e instalaciones.
Los cuatro investigaron sin editar archivos versionados. El integrador hizo las
modificaciones. E revisó independientemente fuente y evidencia, con pruebas
aisladas de falsificación. Sus cuatro hallazgos demostrados —parser mutable,
fixture de versión, sombreado de biblioteca e import previo al hash— están
resueltos y sus pruebas negativas se preservan. También verificó bytecode
envenenado, conteos, HTML, identidad y tiempos. No quedan hallazgos bloqueantes;
no se promete ausencia exhaustiva de defectos.

## 15. Límites y trabajo diferido

Pendientes los seis jobs alojados para el SHA publicado y la revisión visual/
teclado/impresión del propietario. Las pruebas estructurales no son un navegador.
No se añadieron protocolos, escaneo, reensamblado TCP, interpretación industrial,
cacheo funcional, nuevas semánticas nativas ni optimizaciones especulativas.
Cada gate futuro debe aprobar una transición nueva; no actualizar los hashes de
V15-02 para autorizar modificaciones posteriores.

## 16. Revisión requerida del propietario

Abrir `output/v15-02/owner-review/revoked/index.html` sin instalar frameworks GUI.

1. Siete limitaciones verticales independientes.
2. Viñetas nativas visibles.
3. Sangría consistente.
4. Separación vertical cómoda.
5. Lectura al 100%.
6. Lectura al 200%.
7. Ausencia de desbordamiento horizontal de la lista a ancho estrecho.
8. Ajuste de afirmaciones largas.
9. Teclado y foco visible.
10. Navegación Overview → evidencia.
11. Diferenciar aprobación registrada de revocación actual.
12. Uso HTML offline.
13. Impresión legible.

Aceptación humana: **PENDING**. El dossier no sustituye este control.

## 17. Inspección y publicación por el propietario

No se ejecutó push, creación de PR, merge nuevo, tag o Release.
Inspección con Git y PowerShell, sin GitHub CLI:

```powershell
Set-Location 'C:\Users\PC\Desktop\OT-ArchGuard-CLEAN'
git status --short --branch
git log --oneline main..HEAD
git diff --stat main...HEAD
git diff main...HEAD -- src tools/verify_v15_transition.py .github/workflows/ci.yml
git show --stat HEAD
```

Después de revisar y aprobar el resultado, comprobar avances de main y publicar:

```powershell
git fetch --no-tags origin main
git log --oneline HEAD..origin/main
git push -u origin codex/v15-02-compatibility-evolution
```

Si `main` avanzó, reconciliar y volver a verificar la fuente resultante antes de
integrarla. Crear el PR desde la interfaz de GitHub y exigir los seis jobs para
el head real. No realizar force-push ni sustituir activos de v1.4.0.

## 18. Propuesta V15-03

Mejorar primer uso y navegación entre Overview, evidencia, fuentes y autoridad
de revisión, partiendo de observaciones reales del propietario con teclado y
zoom. Conservar las siete limitaciones y contratos analíticos. Tratar cualquier
optimización perfilada como trabajo separado con nuevas muestras pareadas.
