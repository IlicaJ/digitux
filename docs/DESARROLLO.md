# DigiTux — Documentación técnica

Editor libre para el **DigiTech RP360 / RP360XP** en Linux. Licencia GPL-3.0.

## Objetivo

Reemplazar el editor oficial *DigiTech Nexus* (solo Windows/Mac, discontinuado)
con una aplicación nativa de Linux que habla con el pedal por su protocolo
**serie JSON** (no MIDI). También cubre un hueco que *gdigi* nunca llenó: gdigi
usa SysEx/MIDI (`snd_rawmidi`) y no soporta el RP360/XP.

## Hardware y protocolo

- **USB**: VID `1210`, PID `0032`, dispositivo CDC-ACM (`/dev/ttyACM0`), 115200 baud.
- **Framing** (ver `transport.py`): `55 LEN CHAN SEQ ... payload CKSUM` con
  `CHAN 0x43 (host→dev)`, `0x42 (dev→host)`, `0x41 (ACK dev)`, `0x02 (ACK host)`,
  `CKSUM = (256 - sum(pkt[1:-1])) & 0xFF`, `SEND_CHUNK 249`.
- **JSON**: `["cmd", host_id, path, valor]`. Comandos: `rp` (leer), `rc` (leer
  colección), `sp` (set param), `ssc` (set colección), `mc` (mover/copiar),
  `dc` (borrar), `shc` (reordenar cadena). Notificaciones `np`, `cm`, `ndc`,
  `nsc`, `nac`.
- **Handshake**: `rp STATE`, `rp VERSION`, `sbs 1`, `rp system/SYNC`.
- **Controladores** (desde binario/XML): `treadle`, `altTreadle` (expresión),
  `lfo1`, `ctrlA/B/C/ctrlVSw` (footswitch). Rutas `preset/ctrls/{ctrl}/{LNK,MIN,MAX,SPEED,WAVEFORM}`.

## Base de datos de efectos

`nexus/rp360_effects.json`: **140 efectos + 27 cabinets**, provenientes del
`RPPedalInfo.xml` del paquete oficial (ingeniería inversa), con `address`,
`displayName`, `model`, `image`, `params` (min/max/unit/knobType) y `cabType`.

Cadena de señal (10 posiciones fijas, máx. 1 efecto por categoría):

```
0 Wah · 1 Compressor · 2 Distortion · 3 Amplifier · 4 EQ · 5 Gate ·
6 Volume · 7 Mod · 8 Delay · 9 Reverb
```

## Arquitectura

```
nexus/
  transport.py     # serie 115200, framing
  protocol.py      # JSON + despacho de notificaciones
  device.py        # API de alto nivel (carga, edición, controllers, backup)
  model.py         # Preset / FxSlot / Ctrl
  effects_db.py    # DB de efectos + SLOT_CATEGORY + natural_positions()
  runtime.py       # resolución de rutas (fuente / binario congelado / deb)
  rp360_effects.json
  data/nexus_factory_presets.json   # 99 presets de fábrica
  assets/img/      # gráficos generados por código (pedals, amps, cabs, ui)
  ui/
    main.py          # entrada + splash
    main_window.py   # ventana principal (title bar, menú, amp-cab, pedalboard, control panel)
    pedalboard_view.py  # cadena 10 posiciones + drag-drop + pin de amp
    pedal_widget.py  # pedal: imagen + knobs + LED + animación press
    amp_cab_block.py # amp (knobs sobre imagen, LED/palanca ON-Bypass) + cabinet
    effect_picker.py # galería gráfica contextual de efectos
    control_panel.py # Stompbox / Expression / LFO / Wah
    knob.py          # perilla rotatoria dibujada por código
```

## Reglas de negocio

- **Máximo 1 efecto por categoría** en la cadena (no 2 distorsiones, 2 mods…).
- Posiciones naturales por categoría (`SLOT_CATEGORY`); `Volume` y `Mod` pueden
  intercambiar posiciones 6/7.
- El selector de efectos es **contextual**: al cambiar un pedal, solo lista su
  categoría; al *añadir*, solo lista las categorías no presentes.
- Reordenación de cadena vía `shc` (`reorder_chain`), verificado contra hardware.

## Resolución de rutas (`runtime.py`)

El código usa `img_path()` / `data_path()` / `asset_path()` en lugar de
`Path(__file__)`. Esto permite que **los mismos recursos** funcionen en:
fuente, binario PyInstaller/AppImage (`sys._MEIPASS`) y `.deb`/pip
(`site-packages`). Los assets están en `nexus/assets`, los datos en `nexus/data`.

## Distribución

| Formato | Herramienta | Comando |
|---|---|---|
| Binario | PyInstaller (`packaging/digitux.spec`) | `pyinstaller packaging/digitux.spec` |
| AppImage | appimagetool (`packaging/digitux_onedir.spec`) | `appimagetool packaging/AppDir dist/DigiTux-x86_64.AppImage` |
| .deb | stdeb (`setup.py` + `stdeb.cfg`) | `python setup.py --command-packages=stdeb.command bdist_deb` |
| pip | `setup.py` / `pyproject.toml` | `pip install .` |

Todo reproducible con `bash packaging/build_all.sh` (usa el venv de build
`/tmp/opencode/buildenv` con `pyinstaller`, `stdeb`, `PyQt5` y `pyserial`).

Dependencias de runtime: `python3-pyqt5`, `python3-serial` (paquetes del sistema).

## Regla udev

`packaging/99-rp360.rules`:
```
SUBSYSTEM=="tty", ATTRS{idVendor}=="1210", ATTRS{idProduct}=="0032", MODE="0666", SYMLINK+="rp360"
```
El `.deb` la instala en `/etc/udev/rules.d/`.

## Grafícos

Generados 100% por código (`generate_assets.py`, PIL): carcasa redondeada +
placa + nombre + perillas, en estilo *cartoon plano*. No incluye material
protegido. Los nombres de efectos/amplificadores se normalizaron a descriptores
genéricos (sin marcas registradas).

## Publicación

- Repo: https://github.com/IlicaJ/digitux
- Release: https://github.com/IlicaJ/digitux/releases (v0.2.0)
- Licencia: GPL-3.0 (archivo `LICENSE`).
- Donación: https://buymeacoffee.com/lica