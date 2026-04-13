# PMX Static Importer

A desktop tool for importing 3D models (PMX, FBX, OBJ, GLB) into Garry's Mod as runtime-rendered static props, paired with a Garry's Mod Lua addon that loads and displays them in-game.

## Project Structure

```
pmx_static_importer_project/
├── importer_tool/    # Python desktop application (tkinter GUI)
│   ├── main.py       # Entry point
│   └── ...
└── gmod_addon/       # Garry's Mod Lua addon (installed into garrysmod/addons/)
    └── lua/
```

## Requirements

- **Python 3.10+** with **tkinter** support
- **Windows** (the build scripts target Windows; the importer GUI uses Windows-specific paths)
- **Garry's Mod** (for the runtime addon)

## Building from Source

### 1. Clone the repository

```bash
git clone <repo-url>
cd pmx_static_importer_project
```

### 2. Install dependencies

```bash
cd importer_tool
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Build the executable

There are three build modes available:

#### Standard build (one-directory)

Creates a folder with the executable and supporting files:

```bash
python build_windows.py
```

Or use the batch file:

```bash
build_windows.bat
```

Output: `importer_tool/dist/PMXStaticImporter/PMXStaticImporter.exe`

#### Single-file build

Packs everything into a single `.exe`:

```bash
python build_windows.py --onefile
```

Or use the batch file:

```bash
build_windows_onefile.bat
```

Output: `importer_tool/dist/PMXStaticImporter.exe`

#### Debug build (with console window)

Builds a one-directory executable that keeps a console window open for debugging:

```bash
python build_windows.py --console
```

Or use the batch file:

```bash
build_windows_console_debug.bat
```

### Build options

| Flag | Description |
|---|---|
| `--onefile` | Produce a single-file executable instead of a directory |
| `--console` | Keep the console window visible (useful for debugging) |
| `--keep-build` | Skip cleaning `build/` and `dist/` before building |

## Installing the Garry's Mod Addon

Subscribe to the runtime addon on the Steam Workshop:

**[PMX Static Importer Runtime](https://steamcommunity.com/workshop/filedetails/?id=3467707027)**

The addon appears in-game under **Construction → Model Importer → Static Model Importer** in the toolgun menu.

## Running from Source (without building)

```bash
cd importer_tool
python main.py
```

Pass `--help` for available command-line options:

```bash
python main.py --help
```

## Supported Model Formats

| Format | Extension |
|---|---|
| MikuMikuDance | `.pmx` |
| Autodesk FBX | `.fbx` |
| Wavefront OBJ | `.obj` |
| glTF Binary | `.glb` |

Models can also be loaded from `.zip` or `.rar` archives containing a supported model file.

## License

See the repository for license information.
