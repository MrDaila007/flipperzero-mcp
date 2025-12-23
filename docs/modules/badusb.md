# `badusb` module

The `badusb` module manages BadUSB scripts stored on the Flipper’s SD card and can execute them via the BadUSB app.

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


