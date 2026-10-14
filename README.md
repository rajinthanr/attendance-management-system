# Card Attendance System

A battery-powered NFC attendance logger. A student taps an ID card and the unit
confirms the tap with an LED and a vibration pulse, and stores the card number
with a timestamp in on-chip flash. Plugged into a PC over USB-C, it appears as a
USB drive, with no driver needed.

A desktop companion app for the PC keeps the student names, decides which cards
are registered and works out who attended which lecture.

The repository holds the hardware (KiCad 10), the firmware (STM32CubeIDE /
Makefile), the companion app (Python, Qt) and a 3D-printable enclosure.

## Install the companion app on Windows

1. Download the installer:
   [`Companion/dist/AttendanceLogger-Setup-1.0.0.exe`](Companion/dist/AttendanceLogger-Setup-1.0.0.exe)
   ([direct download](https://github.com/rajinthanr/attendance-management-system/raw/main/Companion/dist/AttendanceLogger-Setup-1.0.0.exe), 26 MB).
2. Run it. It installs for the current user without an admin prompt (it offers
   an all-users install too), into `%LOCALAPPDATA%\Programs\Attendance Logger`.
   Python and Qt are bundled, so nothing else needs installing.
3. Start **Attendance Logger** from the Start menu (or the optional desktop
   icon). **Attendance Logger (demo, made-up data)** shows the whole app without
   a device.

- **Requirements:** 64-bit Windows 10 or 11.
- **"Windows protected your PC":** the installer is not code-signed, so
  SmartScreen may warn the first time. Choose *More info*, then *Run anyway*.
- **Your data** lives in `%USERPROFILE%\AttendanceLogger\attendance.db`, with a
  daily backup in `backups\` (the last 14 kept). Uninstalling or upgrading the
  app leaves it in place.
- **Upgrading:** run a newer installer over the old one.

On Linux, build the `.deb` or a portable `.tar.gz` with
`sh Companion/packaging/build_linux.sh`; on macOS, or to run from source, see
[Running from source](#running-from-source). [`Companion/README.md`](Companion/README.md)
explains the app in full.

## Project status (2026-10-14)

| Area | State |
|---|---|
| Schematic and PCB | Routed except the NFC antenna loop (AE3), which still has to be placed and its feed routed. The through-hole parts (battery connector, SWD header, NTC) moved to the back on 2026-10-11 for the slim enclosure, so `PCB/production/` and `PCB/bom/` need regenerating. |
| Firmware | Runs on the board. Card reading, the reader's low-power card wake-up, LEDs, vibration, Stop 2 sleep and the USB drive work. 931 host checks pass. |
| Companion app | Qt desktop app with Windows and Linux installers, built by GitHub Actions on every change. |
| Enclosure | Two-part printed case (base and lid), designed in code and fit-checked against the board. |

## How it works

1. **Card tap.** The ST25R3916 reader sleeps in its own wake-up mode, watching
   the antenna for a card, and wakes the MCU when one comes near. It reads
   ISO14443-A cards (MIFARE Classic, NTAG and similar). The card number is the
   UID: 4-byte UIDs as they are, longer ones by their last four bytes.
2. **Check.** A card read again within 10 s, or already recorded in the current
   lecture, is a duplicate and is not recorded again. Every other card is
   recorded. The device keeps no list of students: it records every card, and
   the PC app decides who is registered.
3. **Feedback.**

   | Result | Feedback |
   |---|---|
   | Tap recorded | green LED and one short buzz |
   | Duplicate | two short buzzes |
   | New lecture started (button hold) | green and three quick buzzes |
   | Battery low | red blinks five times |
   | Log full, or reader fault | red and four buzzes |
   | Settings applied / refused | green and two buzzes / red and three buzzes |

4. **Logging.** Taps go to a RAM buffer, then to flash within 5 seconds. The log
   holds 6,858 records and survives a power cut. When it is full, new taps are
   refused rather than overwriting old ones.
5. **Lectures.** Starting a lecture writes a marker into the log, so taps are
   grouped by lecture even without the app. A lecture is started from the app,
   or on the device by holding the button for 2 s (it keeps the module and
   numbers the lecture on: *Lecture 4* becomes *Lecture 5*). A card counts once
   per lecture. The app imports every tap before a lecture starts and then has
   the device delete its copy (`#CLEARLOG`).
6. **USB.** Plug in USB-C and the device appears as a drive called
   **ATTENDANCE**. A tap while it is plugged in is not attendance: it goes to
   `LASTCARD.TXT`, so the app can register the card. Ejecting the drive or
   tapping the button applies `SETTINGS.CSV` and starts taking attendance with
   the cable still in; a quick double press brings the drive back. A USB
   charger that is not a computer is recognised after 5 s, and scanning carries
   on while it charges.
7. **Power.** Press the button to switch on; a tap shows the battery level.
   Holding it for 5 s switches the device off. On battery it switches itself off
   after 3 minutes without a tap, or when the battery is flat.

[`Firmware/docs/USER_GUIDE.md`](Firmware/docs/USER_GUIDE.md) explains the device
for the people who run a class with it.

### Files on the USB drive

| File | Contents |
|---|---|
| `ATTEND.CSV` | every tap (`DATE,TIME,CARD_ID`), read-only |
| `LECTURES.CSV` | every lecture start (date, time, module, lecture), read-only |
| `LECTURES\` | one read-only CSV per lecture, e.g. `L001_2026-10-07_14-30.csv` |
| `STATUS.TXT` | device ID, clock, battery, record count, current lecture |
| `LASTCARD.TXT` | the card last tapped while plugged in, for registering it |
| `SETTINGS.CSV` | edited by the PC: set the clock (`#TIME`), start a lecture (`#MODULE`, `#LECTURE`, `#NEWSESSION`), clear the log (`#CLEARLOG`), set the device ID (`#DEVICE`) |

## Hardware

| Function | Part | Notes |
|---|---|---|
| MCU | STM32L432**KB** (Cortex-M4F, 128 kB flash, 64 kB RAM, QFN-32) | Runs at 4 MHz from MSI, and 24 MHz during USB sessions, with a 32.768 kHz LSE crystal; sleeps in Stop 2 when idle. The 128 kB of flash holds both the firmware (72 kB) and the attendance log (56 kB). |
| NFC reader | ST25R3916 (13.56 MHz, QFN-32) on SPI1 | Differential antenna drive with an EMC filter, a matching network and a capacitive RX divider; 27.12 MHz crystal. |
| Antenna | PCB loop, `NFC_Loop_40x30_3T` (40 × 30 mm, 3 turns) | In the keep-out area at the top of the board. |
| Backup reader | 8-pin header for a PN532 breakout (Elechouse V3 SPI pinout) | Shares SPI1, with its own chip-select (PA15) and IRQ (PB6). Not fitted, and not used by the firmware yet. |
| Charger | MCP73833 Li-ion linear charger | 10 kΩ NTC and three charge-status LEDs. |
| 3.3 V rail | TPS7A0233 LDO, 200 mA | Runs from the cell. The reader's VDD/VDD_TX come straight from the battery, and its VDD_IO from 3.3 V. |
| USB | USB-C receptacle (GCT USB4110), USB 2.0 full speed | Sink-only with 5.1 kΩ CC resistors; USBLC6-2SC6 ESD protection. |
| Battery | Single-cell Li-ion, 3.7 V, 2-pin JST | Sensed through a 4.7 MΩ / 2.7 MΩ divider with 100 nF, on the ADC (PA7) and the PVD input (PB7). |
| Feedback | Red and green LEDs, vibration motor | The motor is switched by an AO3400A MOSFET with an SS14 flyback diode. |
| Buttons | Power (PA0 / WKUP1), reset, BOOT0 | |
| Debug | 4-pin SWD header: 3V3, SWDIO, SWCLK, GND | |

### MCU pin map

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| PA0 | Power button (EXTI0, WKUP1) | PB0 | ST25R3916 chip-select |
| PA2 / PA3 | Green / red LED | PB1 | ST25R3916 IRQ (EXTI1, card wake-up) |
| PA4 | Vibration motor enable | PB3 / PB4 / PB5 | SPI1 SCK / MISO / MOSI |
| PA7 | Battery sense (ADC1_IN12) | PB6 | PN532 IRQ |
| PA9 | VBUS detect (EXTI9) | PB7 | Battery sense (external PVD input) |
| PA11 / PA12 | USB D- / D+ | PA15 | PN532 chip-select |
| PA13 / PA14 | SWDIO / SWCLK | PC14 / PC15 | 32.768 kHz crystal |

`Firmware/Bsp/Inc/bsp_board.h` is the firmware's reference for the pin map, and
`Firmware/Card Attendance System.ioc` for the CubeMX configuration.

### PCB

- **Board:** 60 × 88.6 mm, 2 layers, 1.6 mm FR-4. SMD parts on the top; the
  through-hole battery connector, SWD header and NTC on the back, so the front
  stays flat.
- **Floorplan:** the NFC antenna fills the top of the board. Below it are the
  PN532 header, the MCU and the ST25R3916 front end. The power section (USB-C,
  ESD, charger, LDO, battery connector) runs along the bottom edge.
- **Schematic sheets:**
  - `power.kicad_sch`: USB-C, ESD, charger, LDO and battery.
  - `mcu.kicad_sch`: STM32, buttons, LEDs, motor driver, SWD and the PN532
    header.
  - `rfid.kicad_sch`: ST25R3916, crystal, EMC filter, matching network and
    antenna.
- **Rules:** manufacturing rules are in `PCB/Attendance Management System.kicad_dru`.
  The production files sent to JLCPCB are in `PCB/production/`.

### Enclosure

`Enclosure/` holds a slim two-part case, 18.8 mm tall: a flat lid with LED
light pipes and a flush flexure power button, and a base that clamps the battery
and motor under the board. Both parts print without supports and are also
designed to be mouldable. `enclosure.py` generates the STL files in
`Enclosure/stl/` from the board file and checks the fit; `view.py` is an
interactive section viewer. See [`Enclosure/README.md`](Enclosure/README.md).

## Firmware

The firmware is split along one rule: **the application logic (`App/`) decides,
the drivers (`Bsp/`) act.**

- **`App/`:** the state machine, ISO14443-A protocol, card presence tracking,
  button debouncing, flash log and device config, lecture sessions, the
  `SETTINGS.CSV` parser, the FAT12 volume, CSV and status files, and battery
  maths. It includes no HAL or register headers and compiles on a PC.
- **`Bsp/`:** implements the hardware contract in `App/Inc/platform_if.h`,
  handing up only raw values. It includes the register-level ST25R3916 driver
  (`bsp_nfc.c`).
- **`Tests/`:** builds all of `App/` against a RAM-backed stub platform with a
  simulated card and a simulated PC editing the drive, so the logic is tested
  without hardware.

The main loop handles events, then sleeps until the next deadline: in Stop 2
when idle, woken by LPTIM1, the button, VBUS or the reader's card wake-up.
[`Firmware/docs/ARCHITECTURE.md`](Firmware/docs/ARCHITECTURE.md) describes the
whole design: the flash layout, record, CSV and settings formats, sessions, the
USB volume, power, and known limitations.

For debugging, `dbg_*` globals defined in `Core/Src/main.c` show the battery
voltage, the last card, button presses, reader status and record counts in
STM32CubeIDE's Live Expressions view.

### Build and test

Run these from `Firmware/`:

```sh
make test    # host tests for the application logic; needs only a native C compiler
make         # cross-compiles build/card-attendance.{elf,hex,bin}
make clean
```

- **Toolchain:** `make` uses the GCC bundled with STM32CubeIDE
  (`/opt/st/stm32cubeide_*`) when one is installed, and otherwise
  `arm-none-eabi-gcc` on `PATH`.
- **Flashing and debugging:** use STM32CubeIDE over the SWD header.
- **Optional:** `Tests/fs_check.sh` checks the USB volume with real FAT tools
  (needs `mtools` and `dosfstools`).

### Data on the device

- **Flash layout:** the firmware takes the first 72 kB of the 128 kB flash; the
  last 56 kB (from `0x08012000`) is reserved for data by the linker script.
  - Its first page: configuration (device ID).
  - The other 27 pages: the attendance log, 6,858 records.
- **Records:** each record is 8 bytes (card number and seconds since
  2000-01-01), exactly one flash double-word. Lecture markers are records with
  reserved IDs from `0xFFFFFF00` up.
- **Setting up a device:** nothing is needed for it to log. The clock starts from
  the firmware's build time until it is set with `#TIME` in `SETTINGS.CSV` (the
  companion app does this when you start a lecture, or with *Set device time*).

## Companion app

`Companion/` is a desktop app for the PC the device is plugged into. It runs
entirely on that computer, with no internet. It finds the device, reads its taps
into a local SQLite database, keeps student names and cards (register a card by
tapping it on the plugged-in device), starts lectures, shows the device's
battery, and saves attendance lists as CSV or PDF.

### Installers

| Platform | Get it | Build it yourself |
|---|---|---|
| Windows | [`Companion/dist/AttendanceLogger-Setup-1.0.0.exe`](Companion/dist/AttendanceLogger-Setup-1.0.0.exe) (see [above](#install-the-companion-app-on-windows)) | `Companion\packaging\build_windows.bat` on Windows (Python 3 and Inno Setup 6), or `sh Companion/packaging/build_windows_docker.sh` from Linux (Docker) |
| Linux | build it, or download from GitHub Actions | `sh Companion/packaging/build_linux.sh`: a `.deb` (`sudo apt install ./attendance-logger_*.deb`) and a portable `.tar.gz` |

GitHub Actions (`.github/workflows/companion-installers.yml`) builds both
whenever `Companion/` changes; the files are under the run's *Artifacts* on the
Actions tab. Pushing a tag such as `companion-v1.2.0` builds that version and
attaches the installers to a GitHub release. Builds land in `Companion/dist/`;
only the Windows `.exe` is committed.

### Running from source

Needs Python 3.8 or newer. From `Companion/`:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt     # Windows: .venv\Scripts\pip install -r requirements.txt
sh start.sh                                   # Windows: start.bat
python attendance_qt.py --demo                # made-up data, no device needed
```

## Repository layout

```
Firmware/            STM32CubeIDE project + standalone Makefile
  App/               application logic (portable, host-tested)
  Bsp/               board support: HAL drivers, ST25R3916 driver, USB MSC glue
  Core/              CubeMX-generated startup code (edit only inside USER CODE blocks)
  Drivers/           ST HAL and CMSIS
  Middlewares/       ST USB Device Library (core + MSC)
  Tests/             host test harness and tools
  docs/              ARCHITECTURE.md (design), USER_GUIDE.md (for users)
  Card Attendance System.ioc   CubeMX pin and peripheral configuration
Companion/           PC app (Python, Qt): window, database, reports
  dist/              Windows installer (AttendanceLogger-Setup-<version>.exe)
  packaging/         PyInstaller spec, Inno Setup script, installer build scripts
PCB/                 KiCad 10 project, BOMs (bom/) and JLCPCB production files (production/)
Enclosure/           3D-printable enclosure (enclosure.py, STL files in stl/)
LICENSE              MIT
```

## Tools

- **PCB:** KiCad 10.0.
- **Firmware:** STM32CubeIDE 1.19 (CubeMX 6.15, STM32Cube FW_L4 V1.18.2), or
  `arm-none-eabi-gcc` with `make`.
- **Host tests:** any C11 compiler (`cc`).
- **Companion app:** Python 3.8+ with PySide6 (Qt), or none with the installer.
- **Enclosure:** Python with `manifold3d` (and `pyvista` for the viewer).

## Known issues

- **External footprint library.** Some footprints come from a SnapEDA library at
  an absolute path outside the repository, so a fresh clone can't resolve them
  until the library is added or the paths are updated.

## License

MIT. See [LICENSE](LICENSE).
