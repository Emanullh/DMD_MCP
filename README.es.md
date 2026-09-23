# Extractor de inventario de Death Must Die

([English version](README.md))

Herramienta de línea de comandos de solo lectura para exportar el inventario de Death Must Die desde una partida local. Es compatible con Windows 11 y macOS; nunca modifica la partida, Steam Cloud ni el juego.

## Inicio rápido

Requisitos: Python 3.11 o superior. Git solo es necesario para clonar el repositorio.

```powershell
git clone https://github.com/Emanullh/DMD_MCP.git
cd DMD_MCP
python dmd_inventory.py dump
```

Si tu instalación de Windows incluye Python Launcher, también puedes usar `py -3 dmd_inventory.py dump`. En macOS, usa `python3 dmd_inventory.py dump`.

Cierra el juego antes de ejecutar el comando para que la copia exportada sea consistente.

## Ubicación de las partidas

La herramienta detecta automáticamente los archivos `.sav` en las siguientes carpetas. Si encuentra más de uno, elige uno de forma interactiva o indica su ruta con `--save`.

| Plataforma | Carpeta predeterminada |
| --- | --- |
| Windows 11 | `%USERPROFILE%\AppData\LocalLow\Realm Archive\Death Must Die\Saves` |
| macOS | `~/Library/Application Support/Realm Archive/Death Must Die/Saves` |

## Comandos

| Comando | Descripción |
| --- | --- |
| `dump` | Exporta el inventario a archivos JSON. |
| `dump --save PATH` | Exporta un archivo `.sav` específico. |
| `dump --output DIRECTORY` | Escribe los archivos en otra carpeta de salida. |
| `dump --debug-dump` | Añade metadatos estructurales para diagnóstico. |
| `inspect --save PATH` | Muestra un resumen de la partida sin crear archivos. |
| `validate output/inventory.json` | Comprueba la consistencia interna de un inventario exportado. |

Usa `python dmd_inventory.py <comando>` en Windows y `python3 dmd_inventory.py <comando>` en macOS. Si Windows incluye Python Launcher, puedes usar `py -3` en lugar de `python`.

## Archivos generados

Por defecto, `dump` crea una carpeta `output` fuera del directorio de partidas.

| Archivo | Contenido |
| --- | --- |
| `inventory_raw.json` | ProfileState, repositorio, contenedores, ubicaciones y campos originales. |
| `inventory.json` | Lista estable para análisis o LLM; las etiquetas desconocidas quedan en `null`. |
| `unresolved.json` | IDs de afijos desconocidos y problemas estructurales detectados. |
| `inventory_bundle.zip` | Archivo comprimido con `inventory.json` y `unresolved.json`. |
| `debug_structure.json` | Metadatos opcionales, creados solo con `--debug-dump`. |

## Seguridad y solución rápida

- La herramienta solo lee la partida seleccionada y trabaja desde una copia temporal.
- Se rechaza cualquier salida dentro de la carpeta de partidas para proteger los archivos originales.
- Si no se detecta una partida, indica la ruta completa: `dump --save "RUTA\A\Save_0.sav"`.
- Si la validación falla, conserva `inventory_raw.json` y `unresolved.json`; contienen los datos necesarios para revisar el problema.
