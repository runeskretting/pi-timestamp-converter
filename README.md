# PI Tag Timestamp Converter

A Python GUI application that converts US format timestamps in CSV files to DD-Mon-YYYY format, commonly required for PI tag data imports.

## Timestamp Conversion

| Input (OPC Server Format) | Output (PI Tag Format) |
|---------------------------|------------------------|
| `12/3/2025 5:28:11 AM.7480000` | `03-Dec-2025 05:28:11` |
| MM/DD/YYYY H:MM:SS AM/PM.ms | DD-Mon-YYYY HH:MM:SS (24-hour) |

Milliseconds are dropped from the output.

### Hour Offset (Timezone Adjustment)

Use the **Hour offset** field to adjust timestamps when OPC server data is in a different timezone than required. Enter a positive or negative integer to shift all timestamps.

| Input | Offset | Output |
|-------|--------|--------|
| `11/25/2025 2:02:03 PM` | `-5` | `25-Nov-2025 09:02:03` |
| `11/26/2025 1:30:00 AM` | `-3` | `25-Nov-2025 22:30:00` |

The date automatically adjusts when the offset crosses midnight.

## Requirements

- Python 3.8+
- tkinter (usually included with Python)
- pandas

### Installing tkinter

**Arch Linux:**
```bash
sudo pacman -S tk
```

**Ubuntu/Debian:**
```bash
sudo apt install python3-tk
```

**Fedora:**
```bash
sudo dnf install python3-tkinter
```

## Installation

### Linux

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Windows 11

1. Install Python from [python.org](https://www.python.org/downloads/) (tkinter is included)

2. Create and activate a virtual environment:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

### WSL2 (Windows 11)

WSL2 with WSLg supports GUI applications natively. Follow the Linux instructions above.

For older WSL without WSLg, install an X server (VcXsrv) and set:
```bash
export DISPLAY=:0
```

## Usage

1. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

2. Run the application:
   ```bash
   python timestamp_converter.py
   ```

3. Click **Upload CSV File** to select a data file

4. Review the original timestamps (left panel) and converted timestamps (right panel)

5. Click **Download Converted CSV** to save the converted file

## Data Format

The application reads comma-delimited OPC server output (no headers). Columns: Timestamp, Value, Quality.

Example input:
```
12/3/2025 5:28:11 AM.7480000,651.261902,0x400c0
12/3/2025 5:28:13 AM.7540000,651.261841,0x400c0
12/3/2025 5:28:15 AM.7470000,651.273376,0x400c0
```

A sample file (`sample_data.csv`) is included for testing.
