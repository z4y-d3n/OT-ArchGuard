# V14-06 — Procedimiento del propietario para integración y publicación

Este documento prepara acciones futuras. El agente no ejecutó push, cambios de
PR, merge, tags, releases ni dispatch. La versión pública estable continúa siendo
v1.3.0. Todos los comandos siguientes requieren la decisión del propietario.
Use PowerShell desde la raíz del repositorio; no necesita GitHub CLI.

## A. Publicar la rama y crear el Draft PR V14-06

Revise primero el [handoff](v14-06-handoff-es.md), sus limitaciones y el recibo
local `output/v146/delivery.json`, que identifica el SHA final sin autorreferencia.
El árbol debe estar limpio y la rama debe descender del padre exacto.

```powershell
git switch codex/v14-06-final-release-readiness
git status --short
git rev-parse HEAD
git merge-base --is-ancestor ac893bc3174f0a7ace67454d19ad6e61116425af HEAD
if ($LASTEXITCODE -ne 0) { throw 'Padre inesperado' }
# Solamente después de aceptar la entrega local:
git push -u origin codex/v14-06-final-release-readiness
```

En GitHub abra **Pull requests → New pull request**. Seleccione base
`codex/v14-05-corpus-interoperability-hardening`, compare
`codex/v14-06-final-release-readiness`. Revise el diff y elija **Create draft pull
request**. No use `main` como base inicial de este PR apilado.

## B. Esperar seis resultados del SHA exacto

El workflow `Python verification` se activa al push de `codex/v14-*`. Registre
run ID, evento, `head_sha`, intento y artifacts. Deben pasar Windows, Ubuntu y
macOS con Python 3.12 y 3.14: seis trabajos, sin exclusiones silenciosas. Revise
skips, instalación wheel/sdist, suite completa, source/archive audit, Ruff, mypy,
pip check, compatibilidad histórica y walkthroughs offline. Descargue los
artifacts `candidate-integrity-*`; los benchmarks tienen retención menor.

La CI del padre `40880668115`, evento push, SHA `ac893bc...`, seis PASS, solamente
acepta el padre. Un push nuevo necesita su propio run. Los eventos PR del workflow
actual están limitados a bases `main`/`v1.2`; un PR apilado depende de su run push.
Una comprobación obligatoria ausente es un bloqueo, no un PASS. Ajustes de rulesets
o workflow solamente corresponden al propietario y necesitan revisión explícita.

## C. Integrar la pila en orden

Se verificaron los siguientes PR abiertos y Draft al iniciar V14-06:

| Orden | PR | Rama compare | Base original |
|---|---|---|---|
| 1 | #17, V14-00 | codex/v14-00-evidence-lifecycle-foundation | main |
| 2 | #18, V14-01 | codex/v14-01-industrial-protocols-and-corpus | V14-00 |
| 3 | #19, V14-02 | codex/v14-02-evidence-revisions-and-baselines | V14-01 |
| 4 | #20, V14-02P | codex/v14-02p-history-performance-hardening | V14-02 |
| 5 | #21, V14-03 | codex/v14-03-historical-drift-analysis | V14-02P |
| 6 | #22, V14-04 | codex/v14-04-historical-explorer | V14-03 |
| 7 | #23, V14-05 | codex/v14-05-corpus-interoperability-hardening | V14-04 |
| 8 | Draft nuevo, V14-06 | codex/v14-06-final-release-readiness | V14-05 |

Reconfirme estado, heads y bases en la interfaz antes de actuar. Se recomienda
**Create a merge commit**, preservando la ascendencia. Integre #17 en `main`.
Después cambie explícitamente la base del siguiente PR a `main`, revise su diff
restante, resuelva conflictos y espere las comprobaciones del resultado propuesto.
Marque ready solamente el PR que ya haya aceptado. Repita hasta V14-06. No elimine
ramas base mientras dependan de ellas otros PR; no dependa de retarget automático.
Respete aprobaciones y protecciones existentes; nunca las omita para obtener verde.

Squash o rebase cambian identidades y pueden dejar cambios de padres apareciendo
otra vez en los PR descendientes. Si el repositorio exige esa estrategia, detenga
la secuencia, revise la ascendencia/diffs y prepare una integración explícita con
nueva verificación. No aplique comandos de rebase/force-push a las ramas históricas.
Una resolución manual de conflictos constituye código nuevo y exige aceptación.

## D. Verificar el `main` integrado

```powershell
git status --short
# Continuar únicamente si está limpio:
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git diff codex/v14-06-final-release-readiness HEAD -- src tests tools pyproject.toml
```

Registre el SHA final de `main`, su árbol y cada diferencia frente al candidato.
Incluso si los árboles coinciden, identifique explícitamente la nueva aceptación
de integración. Si difieren, clasifique y verifique todos los efectos. Espere seis
trabajos exitosos para el SHA integrado. No reutilice como prueba suficiente la
CI anterior del PR ni sus hashes de artifacts.

## E. Reconstruir desde la fuente aceptada

Con Python y las dependencias aprobadas disponibles, en un entorno separado:

```powershell
python -m venv .venv-release
.venv-release/Scripts/python.exe -m pip install -r tools/verification-requirements.txt
.venv-release/Scripts/python.exe tools/verify_source_checkout.py --output output/release-source.json
.venv-release/Scripts/python.exe -m tools.prepare_release --output output/release-1.4.0-final
.venv-release/Scripts/python.exe -m tools.prepare_release --output output/release-1.4.0-final --verify
.venv-release/Scripts/python.exe -m pip install --no-deps output/release-1.4.0-final/otarchguard-1.4.0-py3-none-any.whl
.venv-release/Scripts/python.exe tools/verify_environment.py --output output/release-environment.json
.venv-release/Scripts/otarchguard.exe --version
.venv-release/Scripts/python.exe -m pip check
```

Si existe `output/release-1.4.0-final`, use un directorio nuevo; no sustituya assets
anteriores. La preparación exige árbol versionado limpio y audita cada miembro.
Su manifiesto no afirma por sí solo aceptación de CI ni publicación. Para preparar
offline, reúna previamente los wheels y sustituya instalación de dependencias por
`--no-index --find-links=wheelhouse`; la instalación offline requiere todos los
artefactos compatibles, incluido el backend al instalar sdist.

Repita la aceptación completa registrada en el handoff sobre el source final:
suite wheel, instalación independiente de sdist y su suite, Python 3.12 real,
Ruff/format/mypy, compatibilidad inmutable, consumidores congelados y workflows.
Para denegar red Python durante pruebas y subprocesses:

```powershell
$env:OTARCHGUARD_OFFLINE_CHECK = '1'
$env:PYTHONPATH = (Resolve-Path tools/offline).Path
$env:PIP_NO_INDEX = '1'
.venv-release/Scripts/python.exe -m pytest --basetemp=output/release-suite-tmp --junitxml=output/release-suite.xml
.venv-release/Scripts/python.exe -m tools.verify_legacy_candidate --output output/release-legacy
.venv-release/Scripts/python.exe -m tools.historical_explorer_walkthrough --output output/release-history-walkthrough
```

Use destinos nuevos para cada ejecución. El hook no demuestra un air gap físico.
La suite sdist usa las pruebas del checkout aceptado con el paquete sdist
instalado regularmente, como la CI: algunas pruebas necesitan los pins de Git.
Verifique el import en su site-packages independiente; nunca agregue `src` a
PYTHONPATH para esa aceptación. Ejecute además los ejemplos desde la extracción
auditada del sdist cuando no necesiten el historial Git.

## F. Revisar notas y checksums

Los únicos cuatro assets esperados son wheel, sdist, `release-manifest.json` y
`SHA256SUMS.txt`. Reabra todos con `tools.prepare_release --verify`; registre sus
tamaños y SHA-256. Verificación independiente de los tres checksums sin hash circular:

```powershell
$assetDirectory = Resolve-Path output/release-1.4.0-final
$checksumLines = @(Get-Content (Join-Path $assetDirectory 'SHA256SUMS.txt'))
if ($checksumLines.Count -ne 3) { throw 'Se esperaban tres checksums' }
foreach ($line in $checksumLines) {
    $parts = $line -split '  ', 2
    if ($parts.Count -ne 2 -or $parts[1] -notin @('otarchguard-1.4.0-py3-none-any.whl','otarchguard-1.4.0.tar.gz','release-manifest.json')) { throw 'Nombre inesperado' }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $assetDirectory $parts[1])).Hash.ToLowerInvariant()
    if ($actual -ne $parts[0]) { throw 'Checksum incorrecto' }
}
```

Revise [release notes](../release-notes-1.4.0.md), versión CLI/metadata/motor,
filenames, source SHA del manifiesto y enlaces. Los enlaces futuros a v1.4.0 no
son prueba de publicación. Hashes prueban identidad, no autoría ni firma.

## G. Tag y GitHub Release: solamente con autorización final

Después de todos los gates anteriores, compruebe que `v1.4.0` no existe y que HEAD
es exactamente el SHA de `main` aceptado. Sustituya el placeholder por ese SHA:

```powershell
git tag --list v1.4.0
git ls-remote --tags origin v1.4.0
# Detenerse si existe cualquiera de ellos.
git tag -a v1.4.0 <SHA_MAIN_ACEPTADO> -m 'OT-ArchGuard v1.4.0'
git show --no-patch v1.4.0
git push origin refs/tags/v1.4.0
```

En GitHub: **Releases → Draft a new release**, seleccione ese tag existente,
revise el target, copie las notas aceptadas y adjunte exactamente los cuatro
assets reconstruidos. Revise primero el Draft. Solamente el propietario decide
**Publish release** y su designación de latest. No modifique v1.3.0. No publique
un artifact de V14-06 si no está vinculado al source final aceptado.

## H. Verificación posterior

Desde una descarga nueva, compruebe el tag público, SHA al que resuelve, los
cuatro nombres/tamaños/hashes y manifiesto. Instale el wheel descargado en otro
entorno, ejecute `--version`, valide el ejemplo nativo y abra un reporte offline.
Confirme que README, instalación y notas públicas corresponden al source/tag
publicado. Si se corrige la documentación después, no afirme que cambió el tag ni
sus assets originales. Conserve recibos y ruta de recuperación.

## I. Recuperación

Conserve el entorno y los assets conocidos de v1.3.0; pruebe v1.4 en otro venv.
Para volver, active el entorno v1.3.0 conservado o reinstale su wheel original
verificado. Desinstale únicamente el paquete del entorno que desee retirar.
No prometa que workspaces de v1.4 pueden abrirse o degradarse a v1.3.

Los workspaces de desarrollo `1.4.0.dev1` requieren además su productor exacto:
conserve ese entorno y los datos originales. Para stable cree un workspace nuevo
desde observaciones/adjuntos preservados y regenere revisiones, propuesta y review.
Nunca edite hashes/IDs anteriores ni herede aprobaciones. No sobrescriba o borre
tags/assets publicados como mecanismo de rollback; una incidencia pública necesita
una decisión explícita y trazable del propietario.
