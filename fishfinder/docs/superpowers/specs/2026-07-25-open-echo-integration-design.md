# Open Echo SONAR Integration — Design Spec

## Overview

Adapt the Open Echo SONAR ecosystem (Neumi/open_echo) to an existing fishfinder
project based on Arduino Uno + JSN-SR04T + ILI9341 TFT. The JSN-SR04T provides
real distance readings; synthetic echo profiles are generated on the Arduino
to feed the Open Echo binary serial protocol, enabling the full Python PC
waterfall visualization without requiring new sensor hardware.

## Architecture

```
JSN-SR04T → Arduino Uno ─┬─ ILI9341 TFT (existing local display)
                          │
                          └─ USB Serial (CH340 @ 250000 baud)
                               └─ Python Desktop (PyQt5 + pyqtgraph)
                                    └─ TCP output (NMEA DBT stream)
```

## Components

### 1. Arduino Firmware (`fishfinder.ino`)

- **Real ping:** JSN-SR04T on pins TRIG=6, ECHO=7, returns `distance_m`
- **Synthetic echo profile:** 1800× uint8_t samples representing envelope
  amplitude over the receive window (~18m range in water at 12µs/sample):
  - Water column: low noise floor (Perlin-like, amplitude 5-20)
  - Bottom return: Gaussian pulse at the sample index matching `distance_m`
  - Fish echoes: optional smaller pulses at ~50-70% of bottom depth
  - Blanking zone: first ~40 samples zeroed (simulate TX ringdown)
- **Binary frame:** matches the Open Echo `Frame` struct (0xAA start,
  depth_index, temp_scaled, vDrv_scaled, samples[1800], checksum)
- **TFT display:** unchanged — same sonar scrolling chart, header, panel
- **Serial rate:** 10 fps at 250000 baud (~180 ms per frame + 7 bytes header)

### 2. Serial Protocol (Open Echo compatible)

```
struct Frame {
  uint8_t  start = 0xAA;
  uint16_t depth_index;     // sample index of strongest reflection
  int16_t  temp_scaled;     // temperature * 100 (fake or from DS18B20)
  uint16_t vDrv_scaled;     // drive voltage * 100 (20.0V → 2000)
  uint8_t  samples[1800];   // synthetic echo amplitudes
  uint8_t  checksum;        // XOR of all bytes above
} __attribute__((packed));
```

Total frame size = 1807 bytes. At 250000 baud (~25000 bytes/s), each frame
takes ~72 ms to transmit. 10 fps is achievable.

### 3. Python Desktop Interface (`echo_interface.py`)

Adapted from Open Echo's `echo_interface.py` (~890 lines):

- **Serial reader thread:** reads binary frames from COM port, validates
  checksum, parses into numpy array
- **Waterfall chart:** pyqtgraph `ImageItem` with scrolling colormap
  (echo amplitude vs time)
- **Depth readout:** from `depth_index` converted to meters
- **Signal bar:** 5-segment RSSI indicator
- **TCP output:** NMEA0183 DBT sentence on port 2000 (optional)
- **Controls:** COM port selector, gain/range sliders

Dependencies: `numpy`, `pyserial>=3`, `PyQt5`, `pyqtgraph`, `pyqtdarktheme`

### 4. Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `fishfinder.ino` | Modify | Add synthetic echo generation + binary serial output |
| `echo_interface.py` | Create | Python desktop waterfall viewer (adapted from Open Echo) |
| `requirements.txt` | Create | Python dependencies |
| `settings.h` | Create | Shared pin defines and tuning params |
| `arduino_fishfinder_assembly_guide.html` | Keep | Already complete, minor updates |
| `TUSS4470_shield_002/` | Create | Reference copy of Open Echo shield docs |

### 5. Edge Cases & Error Handling

- **No serial connection:** TFT-only mode continues working independently
- **Frame corruption:** checksum mismatch → discard frame, increment error
  counter on UI
- **Out of range (>4.5m):** `depth_index` set to 0xFFFF, TFT shows "---",
  synthetic profile shows noise only
- **Synthetic edge cases:** if `distance_m` is 0 or invalid → noise floor
  only (no bottom return)

### 6. Future Hardware Upgrade Path

The binary frame protocol and Python interface are identical whether samples
come from simulation or a real transducer. To upgrade later:

- `#define USE_REAL_ECHO 1` in `settings.h`
- Wire raw 40kHz transducer + NPN driver + envelope detector to pins D9/A1
- No Python changes needed — same frame format, real data
