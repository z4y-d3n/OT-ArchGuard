# V15-06 — entrega al propietario

El candidato local cambia distribución/CLI `1.5.0.dev3` → `1.5.0`; no está
publicado. Motor nativo `1.3.0`, esquema YAML `1`, límites, formatos de evidencia
y semántica analítica se conservan. Solo cambia el literal de distribución en
`__init__.py`; los otros 96 módulos son idénticos. El veredicto definitivo y los
resultados ejecutados figuran en [aceptación](v15-06-acceptance.md).

Base integrada V15-05: `7c5d6cb5c0efd6ee5946943bf8b83e12e98a9057`, árbol
`e2c40a52a3f5d9370d2053474d9f2aab1d1463b4`. PR #30 está fusionada; sus seis
trabajos finales aprobaron en run 42138952966. SHA/árbol final local, inventario,
comandos y hashes de los cuatro activos se registran externamente en
`output/v15-06/final/freeze.json` y `checks.json`. Esos hashes no se insertan
en los mismos archivos cuya identidad describen.

## Revisión técnica

- Revisar [matriz P0/P1](v15-06-safety-assurance.md), sus fixtures ficticios,
  oráculo independiente y propagación del rechazo frente al negativo del modelo.
  Un deny ajeno no elimina otra ruta permitida; ninguna interfaz implica forwarding.
- Revisar [compatibilidad](v15-06-compatibility.md), autorización V15-06,
  equivalencia nativa/captura, suites históricas en su versión y ensayos negativos.
  Los verificadores anteriores permanecen intactos.
- Confirmar que versiones no amplían certeza: observación no es autorización,
  ausencia no es bloqueo y reconocimiento de cabecera no es ejecución industrial.
- Confirmar rechazo de replay dev3 por el productor estable, recuperación con
  dev3, integridad portable y archivos históricos inmutables. No transferir
  aprobaciones. Renderizador histórico conserva identidad y cinco módulos.
- Examinar suite completa, lint/formato/mypy/dependencias, instalaciones regulares
  wheel/sdist, walkthroughs y logs reales; no sumar ejecuciones repetidas como
  pruebas únicas. Distinguir validaciones no ejecutadas de aprobaciones.
- Revisar `tools/prepare_v15_release.py`, inventarios públicos y manifiesto/lista
  de checksums. El ensayo tiene exactamente cuatro activos y no constituye
  aprobación de CI, integración ni publicación. No se afirma reproducibilidad
  binaria entre builds.

Archivos cambiados: literal runtime, `pyproject.toml`, dos assertions de versión,
workflow CI, nuevo verificador/ensamblador y tres suites V15-06, documentación
actual, notas de versión, cuatro documentos del dossier e inventarios
`MANIFEST.in`/`tools/public-files.txt`. La lista exacta está en `git diff` frente
a la base. No hay refactor ni capacidad industrial nueva.

## Publicar la rama y abrir la PR: propietario solamente

Tras aceptar el dossier local, ejecutar PowerShell con Git ordinario. Detenerse
ante cualquier error; revisar el diff antes del push. Estos comandos no fueron
ejecutados remotamente por el agente.

```powershell
git switch codex/v15-06-final-release-readiness
if ($LASTEXITCODE -ne 0) { throw 'Rama no disponible' }
git status --short --branch
git log --oneline -4
git diff --stat 7c5d6cb5c0efd6ee5946943bf8b83e12e98a9057 HEAD
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git push -u origin codex/v15-06-final-release-readiness
if ($LASTEXITCODE -ne 0) { throw 'Push falló' }
```

Abrir manualmente una PR contra `main` desde la interfaz de GitHub usando la
rama publicada. Git no dispone de un comando para crear PR. No se requiere `gh`.
Revisar los seis trabajos Windows/Ubuntu/macOS × Python 3.12/3.14 del **SHA final
de la PR**; si el head cambia, verificar de nuevo. Resolver cualquier fallo P0/P1,
de integridad, empaquetado o CI antes de aceptar. Fusionar únicamente por decisión
del propietario.

## Fuente integrada y activos definitivos

La fusión puede producir otro commit. No usar automáticamente el head de PR ni
reutilizar los activos del ensayo como si pertenecieran a la integración.

```powershell
git fetch --no-tags origin main
if ($LASTEXITCODE -ne 0) { throw 'Fetch falló' }
git switch main
if ($LASTEXITCODE -ne 0) { throw 'Switch falló' }
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw 'Fast-forward falló' }
$IntegratedSha = (git rev-parse HEAD).Trim()
$IntegratedTree = (git rev-parse 'HEAD^{tree}').Trim()
if (git status --porcelain=v1) { throw 'La fuente debe estar limpia' }
$IntegratedSha
$IntegratedTree
```

Antes de construir: comprobar en GitHub los seis trabajos exitosos para ese
`$IntegratedSha`, conservar sus IDs/receipts y revisar que el árbol sea el
esperado. No atribuirle CI de otra fuente. Preparar un entorno nuevo con las
dependencias aprobadas (o wheelhouse del destino), y destinos nuevos:

```powershell
python -m venv .venv-v15-final
if ($LASTEXITCODE -ne 0) { throw 'Entorno falló' }
$ReleasePython = (Resolve-Path .venv-v15-final/Scripts/python.exe).Path
& $ReleasePython -m pip install -r tools/verification-requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependencias fallaron' }
$FinalAssets = "output/v15-final-$IntegratedSha"
& $ReleasePython -m tools.prepare_v15_release --output $FinalAssets
if ($LASTEXITCODE -ne 0) { throw 'Ensamblado falló' }
& $ReleasePython -m tools.prepare_v15_release --verify --output $FinalAssets
if ($LASTEXITCODE -ne 0) { throw 'Auditoría independiente falló' }
Get-ChildItem -LiteralPath $FinalAssets -File | Get-FileHash -Algorithm SHA256
& $ReleasePython -m pip install --no-index --no-deps "$FinalAssets/otarchguard-1.5.0-py3-none-any.whl"
if ($LASTEXITCODE -ne 0) { throw 'Wheel falló' }
& $ReleasePython -I tools/verify_v15_06_transition.py --source-only --output "output/v15-final-authorized-$IntegratedSha.json"
if ($LASTEXITCODE -ne 0) { throw 'Autorización falló' }
& $ReleasePython tools/verify_environment.py --output "output/v15-final-environment-$IntegratedSha.json"
if ($LASTEXITCODE -ne 0) { throw 'Identidad instalada falló' }
& $ReleasePython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependencias inconsistentes' }
```

Repetir instalación regular en otro entorno nuevo con el sdist auditado,
`--no-index --no-deps --no-build-isolation`, y verificaciones de identidad/CLI,
primer modelo/Explorer, captura e historia documentadas. Ejecutar la cadena
completa V15-06 y las verificaciones exigidas por el checklist para esa fuente.
Conservar resultados y hashes de **los cuatro** archivos en un receipt externo.
Confirmar exactamente cuatro activos, todos regulares, sin archivos adicionales.
`SHA256SUMS.txt` contiene los tres restantes, nunca su propio hash.

## Tag y Release: autorización posterior explícita

Solo tras integrar, validar el CI exacto, auditar/instalar ambos paquetes y
aprobar explícitamente SHA/árbol/hashes definitivos, el propietario puede ejecutar:

```powershell
if ((git rev-parse HEAD).Trim() -ne $IntegratedSha) { throw 'HEAD cambió' }
if (git status --porcelain=v1) { throw 'Fuente sucia' }
git show-ref --verify --quiet refs/tags/v1.5.0
if ($LASTEXITCODE -eq 0) { throw 'El tag ya existe; no reemplazar' }
git tag -a v1.5.0 $IntegratedSha -m 'OT-ArchGuard v1.5.0'
if ($LASTEXITCODE -ne 0) { throw 'Tag falló' }
git push origin refs/tags/v1.5.0
if ($LASTEXITCODE -ne 0) { throw 'Publicación del tag falló' }
```

Crear manualmente la GitHub Release para ese tag, revisar las
[notas](../release-notes-1.5.0.md), y subir exclusivamente wheel, sdist,
`release-manifest.json`, `SHA256SUMS.txt` definitivos. No sobrescribir tags,
historia ni activos v1.4.0. El agente no ha autorizado ni realizado estos pasos.

Descargar los cuatro activos en otro directorio, comparar tamaños/SHA-256 con
el receipt externo, comprobar las tres líneas de checksums y volver a ejecutar
`prepare_v15_release --verify` desde el checkout limpio del commit etiquetado,
apuntando a esa carpeta descargada. Confirmar el tag anotado y su commit con
`git rev-parse 'v1.5.0^{commit}'`. Repetir instalación representativa del activo
descargado. Registrar URL real, fecha real, SHA/árbol y hashes publicados.

Solo entonces actualizar en una PR documental README latest-stable/Quick Start,
instalación, notas y checklist con los datos publicados. Conservar referencias
históricas v1.4 y procedencia de screenshots; no inventar imágenes ni certificación.

No se ejecutaron publicación de rama/PR, fusión, CI del candidato, tag, Release,
upload, descarga final, acceso OT real ni validación local en otros sistemas.
La suite local no sustituye esos requisitos del propietario.
