# Death Must Die Inventory Extractor

A read-only command-line tool for exporting a Death Must Die inventory from a local save file. It supports Windows 11 and macOS, and never modifies the save, Steam Cloud, or the game.

Herramienta de línea de comandos de solo lectura para exportar el inventario de Death Must Die desde una partida local. Es compatible con Windows 11 y macOS; nunca modifica la partida, Steam Cloud ni el juego.

## Quick start | Inicio rápido

Requirements: Python 3.11 or newer. Git is needed only to clone the repository.

Requisitos: Python 3.11 o superior. Git solo es necesario para clonar el repositorio.

```powershell
git clone https://github.com/Emanullh/DMD_MCP.git
cd DMD_MCP
py -3 dmd_inventory.py dump
```

On macOS, run `python3 dmd_inventory.py dump` instead of `py -3 dmd_inventory.py dump`.

En macOS, usa `python3 dmd_inventory.py dump` en lugar de `py -3 dmd_inventory.py dump`.

Close the game before running the command so the exported snapshot is consistent.

Cierra el juego antes de ejecutar el comando para que la copia exportada sea consistente.

## Save locations | Ubicación de las partidas

The tool detects `.sav` files automatically in the following folders. If more than one file is found, choose one interactively or pass its path with `--save`.

La herramienta detecta automáticamente los archivos `.sav` en las siguientes carpetas. Si encuentra más de uno, elige uno de forma interactiva o indica su ruta con `--save`.

| Platform | Default save folder |
| --- | --- |
| Windows 11 | `%USERPROFILE%\AppData\LocalLow\Realm Archive\Death Must Die\Saves` |
| macOS | `~/Library/Application Support/Realm Archive/Death Must Die/Saves` |

## Commands | Comandos

| Command | English | Español |
| --- | --- | --- |
| `dump` | Exports the inventory to JSON files. | Exporta el inventario a archivos JSON. |
| `dump --save PATH` | Exports a specific `.sav` file. | Exporta un archivo `.sav` específico. |
| `dump --output DIRECTORY` | Writes files to another output directory. | Escribe los archivos en otra carpeta de salida. |
| `dump --debug-dump` | Adds structural metadata for troubleshooting. | Añade metadatos estructurales para diagnóstico. |
| `inspect --save PATH` | Prints a save summary without creating output files. | Muestra un resumen de la partida sin crear archivos. |
| `validate output/inventory.json` | Checks that an exported inventory is internally consistent. | Comprueba la consistencia interna de un inventario exportado. |

Use `py -3 dmd_inventory.py <command>` on Windows and `python3 dmd_inventory.py <command>` on macOS.

Usa `py -3 dmd_inventory.py <comando>` en Windows y `python3 dmd_inventory.py <comando>` en macOS.

## Output | Archivos generados

By default, `dump` creates an `output` folder outside the save directory.

Por defecto, `dump` crea una carpeta `output` fuera del directorio de partidas.

| File | English | Español |
| --- | --- | --- |
| `inventory_raw.json` | Raw ProfileState, repository entries, containers, locations, and original item fields. | ProfileState, repositorio, contenedores, ubicaciones y campos originales. |
| `inventory.json` | Stable item list for analysis or LLM use; unknown labels remain `null`. | Lista estable para análisis o LLM; las etiquetas desconocidas quedan en `null`. |
| `unresolved.json` | Unknown affix IDs and structural issues found during extraction. | IDs de afijos desconocidos y problemas estructurales detectados. |
| `inventory_bundle.zip` | Archive containing `inventory.json` and `unresolved.json`. | Archivo comprimido con `inventory.json` y `unresolved.json`. |
| `debug_structure.json` | Optional structural metadata, created only with `--debug-dump`. | Metadatos opcionales, creados solo con `--debug-dump`. |

## Safety and troubleshooting | Seguridad y solución rápida

- The tool only reads the selected save and works from a temporary snapshot.
- Output inside the game's save directory is rejected to protect the original files.
- If no save is detected, pass its full path: `dump --save "PATH\TO\Save_0.sav"`.
- If validation fails, keep `inventory_raw.json` and `unresolved.json`; they contain the data needed to inspect the problem.

- La herramienta solo lee la partida seleccionada y trabaja desde una copia temporal.
- Se rechaza cualquier salida dentro de la carpeta de partidas para proteger los archivos originales.
- Si no se detecta una partida, indica la ruta completa: `dump --save "RUTA\A\Save_0.sav"`.
- Si la validación falla, conserva `inventory_raw.json` y `unresolved.json`; contienen los datos necesarios para revisar el problema.
