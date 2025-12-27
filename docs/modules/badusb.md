# `badusb` module

The `badusb` module manages BadUSB scripts stored on the Flipper’s SD card and can execute them via the BadUSB app.

## UAT notes (USB / serial disconnect)

BadUSB works by making the Flipper enumerate as a **USB HID keyboard/mouse** to a *target* computer. On many firmwares/configurations, switching into BadUSB/HID mode will **disrupt the USB CDC serial connection** used for protobuf RPC.

Practical implications for UAT:

- **Upload/inspect scripts while connected over RPC** (USB serial or WiFi).
- **Expect the RPC connection to drop when you start BadUSB** (this is normal).
- If RPC app-launch doesn’t work on your firmware, **start BadUSB manually on the Flipper** and run the script from the device UI.

If you want to keep MCP connected while testing HID on a target machine, prefer a non-USB RPC transport (e.g. WiFi) so the Flipper’s USB can be dedicated to HID.

## UAT checklist (recommended safe flow)

### Prerequisites

- MicroSD card inserted and accessible (verify with `systeminfo_get`)
- A safe “demo” target: ideally a throwaway VM or test machine, not your primary workstation
- A clearly safe script (e.g. opens Notepad/Terminal and types a message)

### Step 1 — Verify device + SD card

1. Run `systeminfo_get`
2. Confirm it reports **MicroSD Card: Detected and accessible**

### Step 2 — Generate and save a safe script

1. Run `badusb_generate` with a benign description, for example:
   - Description: “Open Notepad and type `UAT ok`”
   - Target OS: `windows`
   - Filename: `uat_notepad.txt`
2. Review the generated DuckyScript output (ensure it’s harmless)

### Step 3 — Confirm the script is on the Flipper

1. Run `badusb_list` and confirm `uat_notepad.txt` appears
2. Run `badusb_read` for `uat_notepad.txt` and verify contents

### Step 4A — Execute via MCP (expect possible disconnect)

1. Plug the Flipper into the **target** machine over USB
2. Run `badusb_execute` with:
   - `filename`: `uat_notepad.txt`
   - `confirm`: `true`
3. Observe:
   - Keystrokes on the target machine (Notepad opens + text appears)
   - Your MCP/RPC connection may drop during/after launch (expected)

### Step 4B — Execute manually on the Flipper (fallback / most reliable)

1. Plug the Flipper into the **target** machine over USB
2. On the Flipper: open **BadUSB**
3. Select the script from `/ext/badusb` (e.g. `uat_notepad.txt`)
4. Run it and observe the same expected behavior on the target

## Storage location

- Scripts are stored under `/ext/badusb`
- This module requires a MicroSD card for file operations and execution

## Tools

### `badusb_list`

List scripts under `/ext/badusb`.

### `badusb_read`

Read a script from `/ext/badusb/<filename>`.

Parameters:

- `filename` (string)

### `badusb_generate`

Generate and save a BadUSB script.

Parameters:

- `description` (string)
- `target_os` (string enum: `windows`, `macos`, `linux`; default: `windows`)
- `filename` (string; default: `ai_generated.txt`)

Notes:

- Script generation is currently template/pattern based (see `flipper_mcp.modules.badusb.generator.DuckyScriptGenerator`).
- Scripts are validated with `flipper_mcp.modules.badusb.validator.ScriptValidator`.

### `badusb_execute`

Execute a script immediately.

Parameters:

- `filename` (string)
- `confirm` (boolean; must be `true`)

### `badusb_workflow`

Generate, validate, save, and optionally guide the user toward execution.

Parameters:

- `description` (string)
- `target_os` (string enum; default: `windows`)
- `execute` (boolean; default: `false`)

Notes:

- `execute=true` does not bypass confirmation; execution still requires an explicit `badusb_execute(..., confirm=true)`.


