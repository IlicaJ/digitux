# AGENTS.md — Memoria del proyecto

Guía para agentes/colaboradores que trabajen en **DigiTux**.

## Qué es

Editor libre (GPL-3.0) para el **DigiTech RP360 / RP360XP** en Linux.
Reemplaza al editor oficial *Nexus* (Windows/Mac) usando el protocolo serie JSON
real del pedal. Cubre el hueco que *gdigi* nunca llenó (usa MIDI/SysEx, el RP360
no es MIDI).

- Repo: https://github.com/IlicaJ/digitux
- Release: https://github.com/IlicaJ/digitux/releases
- Licencia: GPL-3.0 (`LICENSE`)

## Comandos habituales

```bash
# Ejecutar en modo fuente
python3 -m nexus.ui.main          # necesita PYTHONPATH=. o estar en la raíz
./run.sh                          # lanzador portable

# Verificar compilación
python3 -m py_compile nexus/*.py nexus/ui/*.py

# Regenerar los gráficos (arte por código)
python3 generate_assets.py

# Empaquetar todo (binario + AppImage + .deb)
bash packaging/build_all.sh
```

El venv de build está en `/tmp/opencode/buildenv` (con `pyinstaller`, `stdeb`,
`PyQt5`, `pyserial`). `appimagetool` está en `/tmp/opencode/appimagetool`.

## Dónde está cada cosa

- **Backend** (`nexus/`): `transport.py` (serie/framing), `protocol.py` (JSON),
  `device.py` (API alto nivel), `model.py` (Preset/FxSlot/Ctrl), `effects_db.py`
  (DB + reglas de cadena), `runtime.py` (rutas).
- **UI** (`nexus/ui/`): `main_window.py` (ventana), `pedalboard_view.py`,
  `pedal_widget.py`, `amp_cab_block.py`, `effect_picker.py`, `control_panel.py`,
  `knob.py`, `main.py`.
- **Datos**: `nexus/rp360_effects.json` (140 efectos + 27 cabinets),
  `nexus/data/nexus_factory_presets.json` (99 presets), `nexus/assets/img/`
  (gráficos generados).
- **Empaquetado**: `packaging/` (specs, `.desktop`, udev, `build_all.sh`),
  `setup.py`, `stdeb.cfg`, `pyproject.toml`.
- **Docs**: `README.md`, `docs/DESARROLLO.md`, `REDDIT_POST.md` (local).

## Reglas importantes (no romper)

1. **Rutas**: SIEMPRE usar `runtime.img_path()` / `data_path()` / `asset_path()`,
   NUNCA `Path(__file__).parents[...]`. Los recursos deben funcionar tanto en
   fuente como en binario congelado/`.deb`.
2. **Assets y data viven DENTRO de `nexus/`** (`nexus/assets/`, `nexus/data/`)
   para que viajen en todos los formatos de distribución.
3. **Arte y nombres**: los gráficos se generan por código; NO añadir material
   propietario ni nombres de marcas registradas (se sanean a genéricos).
4. **Cadena de señal**: máximo 1 efecto por categoría (`SLOT_CATEGORY` y
   `natural_positions()` en `effects_db.py`). Volume y Mod pueden intercambiar 6/7.
5. **`.gitignore` excluye `dist/`, `build/`, `deb_dist/`, `*.deb`, `*.AppImage`,
   `*.tar.gz`, `*.jpeg`, `*.jpg`**: los binarios van al release, no al repo.
6. **El `.deb`** instala la regla udev y el `.desktop` vía `data_files` de `setup.py`.

## Protocolo clave (para referencia rápida)

- USB `1210:0032` (`/dev/ttyACM0`), 115200, framing `55 LEN CHAN SEQ...CKSUM`.
- Comandos: `rp`, `rc`, `sp`, `ssc`, `mc`, `dc`, `shc`; notif `np`, `cm`, `ndc/nsc/nac`.
- Controllers: `treadle`, `altTreadle`, `lfo1`, `ctrlA/B/C/ctrlVSw`.
- Handshake: `rp STATE`, `rp VERSION`, `sbs 1`, `rp system/SYNC`.
- `set_model` → `ssc preset/fxc/{slot}` con `{"fx":{"name":"prefix.ADDRESS"}}`.
- `send_preset` → `ssc "" {"preset": {...}}` con timeout 15 s.

## Estado / pendientes

Hecho: backend completo + UI + selector contextual + control panel + reordenación
por drag-drop + distribución multi-formato (binario/AppImage/`.deb`/pip) + release
v0.2.0 en GitHub.

Posibles siguientes pasos (no pedidos aún): `snapcraft.yaml` para Snap Store,
paquete Debian nativo (`debian/`) para PPA, empaquetado arm64 para otros usuarios.