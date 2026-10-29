# V14-06 — Auditoría independiente de distribución y dependencias

Subagente E. Padre verificado: `ac893bc3174f0a7ace67454d19ad6e61116425af`.
Esta auditoría local no publica archivos, no crea tags y no acepta por sí sola
el commit integrado ni la CI futura. El integrador conserva la responsabilidad
de vincular los paquetes finales con el freeze y las instalaciones verificadas.

## Hallazgos reproducidos y disposición

| ID / gravedad | Reproducción independiente y resultado anterior | Corrección y prueba | Límite residual |
|---|---|---|---|
| V146-E01 / P1 | Sobre wheel y sdist reales del padre, agregar `Version: 9.9.9` como segunda cabecera en METADATA y ambos PKG-INFO; recalcular RECORD. La auditoría aceptaba la identidad ambigua. También aceptaba un comando adicional en ambos entry_points y cambios a Wheel-Version, Root-Is-Purelib o Tag. Se esperaba rechazo. | `tools/audit_release.py` exige una sola cabecera de identidad con su valor revisado, Metadata-Version único y consistente, perfil wheel `1.0` / `true` / `py3-none-any`, y tabla `console_scripts` exactamente igual a `project.scripts`. Rechaza defaults, secciones/comandos extra, duplicados, cambios de mayúsculas y sintaxis inválida. Generator no se fija artificialmente. 39 regresiones pasan usando archivos reales construidos desde una copia aislada de las fuentes públicas. | No es autenticación del editor ni firma criptográfica. No se amplía la lista de dependencias ni de miembros permitidos. |
| V146-E02 / P1 | El nuevo ensamblador invocaba dos hooks usando `sys.argv[1]`; setuptools altera argv durante el primero. El sdist se generaba en `bdist_wheel/`, aunque el proceso terminaba con código cero. | El integrador guarda el destino antes de ejecutar los hooks. La auditoría/reapertura posterior debe encontrar ambos archivos en el destino solicitado. | El ensayo final desde commit limpio pertenece a la aceptación del integrador; una construcción aislada no lo sustituye. |
| V146-E03 / P2 | Los avisos de herramientas nombraban versiones antiguas de pip mientras el entorno aprobado usa 26.2.2. | Corrección acotada en `THIRD_PARTY_NOTICES.md`. | Las versiones resueltas futuras requieren otra revisión. |

Las reproducciones previas a la corrección quedan en
`output/v146/packaging-metadata-probe.json`,
`output/v146/packaging-additional-metadata-probes.json` y
`output/v146/packaging-build-investigate.log`. Los archivos manipulados están
aislados bajo `output/v146/packaging-*-probe/`; no forman parte de los paquetes.

## Inventarios, licencias y dependencias

El padre contiene 483 archivos públicos/tracked y 97 módulos Python de producción.
Antes de la transición ambos inventarios coinciden exactamente. Después de ella,
96 módulos siguen iguales; sólo cambia el literal de distribución en `__init__.py`.
Los nuevos tests, documentos y herramientas deben incorporarse a las dos listas
explícitas antes del freeze. Las cifras finales corresponden al recibo del
integrador, no al inventario inicial del padre.

No se justifica retirar el recibo de rendimiento V14-02P de 2.201.252 bytes:
conserva evidencia histórica. Es el mayor archivo tracked revisado. El wheel
contiene código del proyecto y sus avisos; los recibos, ejemplos y documentación
se distinguen explícitamente del payload ejecutable. El sdist sigue la lista
pública completa. No se agrega ningún PCAP externo ni se amplían permisos de
redistribución de los corpus existentes.

El entorno Windows Python 3.14.5 resuelve esta clausura de ejecución de 14 paquetes:

| Paquete | Versión | Licencia revisada |
|---|---|---|
| typer | 0.27.3 | MIT; Click incluido conserva BSD-3-Clause |
| PyYAML | 6.0.3 | MIT |
| pydantic | 2.14.1 | MIT |
| pydantic-core | 2.50.1 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| rich | 15.0.0 | MIT |
| markdown-it-py | 4.2.0 | MIT; aviso adicional de markdown-it |
| mdurl | 0.1.2 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| shellingham | 1.5.4 | ISC |
| colorama | 0.4.6 | BSD-3-Clause |

Se verificaron 17 archivos de avisos/licencias no vacíos, incluyendo
`typer/_click/LICENSE.txt` y `LICENSE.markdown-it`; sus hashes están en
`output/v146/packaging-source-notices.json`. `pip check` del entorno inspeccionado
pasa. Las dependencias de desarrollo/build permanecen separadas y no se vendorizan
en el wheel. No hubo actualización de dependencias ni revisión jurídica profesional.

## Consulta de avisos de seguridad

Se consultó el endpoint oficial OSV `https://api.osv.dev/v1/querybatch` con las
versiones exactas de esos 14 paquetes, setuptools 84.2.1 y pip 26.2.2: 16 respuestas
vacías, sin avisos coincidentes devueltos. El recibo conserva fecha UTC, solicitud y
respuesta en `output/v146/packaging-advisory-query-host.json`. La primera tentativa
en sandbox falló por DNS; una consulta de sólo lectura autorizada por la revisión
automática del host permitió obtener el resultado. Se enviaron únicamente nombres
y versiones públicos, sin datos importados ni capturas.

La [base de avisos de PyPA](https://github.com/pypa/advisory-database) documenta su
integración con OSV. Ésta es una consulta puntual de avisos conocidos para esas
16 versiones; no demuestra ausencia de vulnerabilidades desconocidas, no escanea
todo componente nativo del SO y no cubre automáticamente versiones futuras ni
todas las herramientas de desarrollo instaladas. No añade red al producto.

## Verificación focalizada

```powershell
.venv/Scripts/python.exe -m pytest tests/test_v146_packaging_audit.py -q --tb=short `
  --basetemp=output/v146/packaging-audit-final-tmp `
  --junitxml=output/v146/packaging-audit-final.xml
.venv/Scripts/python.exe -m ruff check tools/audit_release.py tests/test_v146_packaging_audit.py
.venv/Scripts/python.exe -m ruff format --check tools/audit_release.py tests/test_v146_packaging_audit.py
.venv/Scripts/python.exe -m mypy tools/audit_release.py tests/test_v146_packaging_audit.py
```

Resultado focalizado: **39 PASS**, sin skips/fallos/errores; Ruff lint/format y mypy
estricto pasan. No se suman estas ejecuciones a los casos únicos de la suite final.
La prueba de archivos intactos confirma aceptación antes de las mutaciones;
los ataques recalculan RECORD y, para entrypoints, coordinan ambos formatos.
Los fallos iniciales del propio harness (argv y separadores CRLF) se corrigieron
antes de esta aceptación; no se ocultaron ajustando el comportamiento del producto.

R11–R14 y R28 requieren además el ensayo final del integrador: auditoría desde
fuente comprometida y limpia, inventarios exactos, instalación independiente de
wheel y sdist, comprobación de imports/consola, dependencias y reapertura de los
cuatro assets. Este informe no convierte esos pasos pendientes en PASS.
