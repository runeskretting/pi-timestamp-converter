# PI Tag Timestamp Converter

A Python GUI application that converts OPC server timestamps in CSV files to the DD-Mon-YYYY format required for PI tag data imports.

## Timestamp Conversion

| Input (OPC Server Format) | Output (PI Tag Format) |
|---------------------------|------------------------|
| `12/3/2025 5:28:11 AM.7480000` | `03-Dec-2025 05:28:11` |
| MM/DD/YYYY H:MM:SS AM/PM.ms | DD-Mon-YYYY HH:MM:SS (24-hour) |

Milliseconds are dropped from the output. The Quality column is dropped from the output.

---

## Features

### Multi-file Upload

Click **Upload CSV Files** to select one or more OPC data files at once. All files are merged into a single dataset and sorted chronologically by timestamp before display.

Supported file types: `.csv`, `.txt`.

### Hour Offset (Timezone Adjustment)

Use the **Hour offset** field to shift all timestamps by a fixed number of hours. Accepts positive or negative integers. The date adjusts automatically when the offset crosses midnight.

| Input | Offset | Output |
|-------|--------|--------|
| `11/25/2025 2:02:03 PM` | `-5` | `25-Nov-2025 09:02:03` |
| `11/26/2025 1:30:00 AM` | `-3` | `25-Nov-2025 22:30:00` |

### Tagname Column

Use the **Tagname** dropdown to control whether the output includes a tag identifier column:

| Option | Output columns | Behaviour |
|--------|---------------|-----------|
| None | Timestamp, Value | No tagname column |
| Custom | Tagname, Timestamp, Value | Enter any tag name; auto-fills with the first uploaded filename (without extension) if the field is empty when selected |

### Filters

#### Remove Bad Quality
Check **Remove bad quality** to drop all rows where the Quality field equals `0x100400c0` (OPC "bad" quality code) before conversion.

#### Remove Duplicate Timestamps
Check **Remove duplicate timestamps** to keep only the first occurrence of each timestamp after conversion.

#### Date/Time Range
Enable the **Start** and/or **End** checkboxes in the Export panel to restrict output to a specific time window. Date format: `DD-Mon-YYYY` (e.g. `01-Jan-2025`). Time format: `HH:MM:SS`.

### Apply Button

The **Apply** button converts the loaded data using the current settings and updates the right-hand preview panel. The button highlights yellow whenever any setting changes, indicating that the preview is out of date. Clicking Apply resets it.

### Export

- **Encoding** — choose **ANSI** (`cp1252`, default) or **UTF-8** for the output file. Choose ANSI for compatibility with PI DataLink and most PI tools on Windows.
- **Download Converted CSV** — saves the converted data to a file of your choice. Output has no header row.

### Presets

Save and restore all settings (offset, filters, tagname, encoding, date range) as a JSON file.

- **Save Preset** — writes current settings to a `.json` file.
- **Load Preset** — restores settings from a `.json` file.
- **Auto-save / auto-load** — settings are automatically saved to `last_preset.json` on every Apply or Save Preset, and restored on the next startup.

### Batch Queue

Process multiple tags in one operation without manual file-by-file uploads.

**How it works:**

1. Prepare a plain-text queue file with one tag name per line (e.g. `SENSOR_001`).
2. Place all source CSV/TXT files in a single source directory. Files are matched to tags by filename prefix (a file named `SENSOR_001_export.csv` matches the tag `SENSOR_001`).
3. In the **Batch Queue** panel, select:
   - **Source Dir** — folder containing the source files.
   - **Queue File** — the text file listing tag names.
   - **Output Dir** — folder where converted files will be written.
4. Click **Apply**. One output CSV is created per tag. All active settings (offset, filters, tagname, encoding) are applied to each file.

The status bar reports how many tags were exported, skipped (no matching file found), or failed.

**Queue file example:**
```
SENSOR_001
SENSOR_002
PUMP_FLOW_A
```

**Note:** Selecting any batch queue path clears the manually loaded data, and uploading a file manually clears the queue paths. The two modes are mutually exclusive.

---

## Data Format

Input files are comma-delimited with no header row. Columns: `Timestamp`, `Value`, `Quality`.

**Example input:**
```
12/3/2025 5:28:11 AM.7480000,651.261902,0x400c0
12/3/2025 5:28:13 AM.7540000,651.261841,0x400c0
12/3/2025 5:28:15 AM.7470000,651.273376,0x400c0
```

**Example output (tagname: Custom = `SENSOR_001`):**
```
SENSOR_001,03-Dec-2025 05:28:11,651.261902
SENSOR_001,03-Dec-2025 05:28:13,651.261841
SENSOR_001,03-Dec-2025 05:28:15,651.273376
```

A sample file (`sample_data.csv`) is included for testing.

---

## Installation

### Windows

1. **Install Python 3.8+** from [python.org](https://www.python.org/downloads/).
   - During installation, tick **"Add Python to PATH"**.
   - tkinter is included with the official Windows installer — no extra step needed.

2. **Download the repository** (clone with git or download the ZIP and extract it).

3. Open **Command Prompt** or **PowerShell** in the project folder.

4. Create and activate a virtual environment:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```

5. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

6. Run the application:
   ```cmd
   python timestamp_converter.py
   ```

### Arch Linux

1. **Install Python and tkinter** (tkinter is a separate package on Arch):
   ```bash
   sudo pacman -S python tk
   ```

2. **Download the repository** (clone with git or download and extract the archive):
   ```bash
   git clone <repository-url>
   cd pi-timestamp-converter
   ```

3. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the application:
   ```bash
   python timestamp_converter.py
   ```

---

## Usage Workflow

### Manual (single or multi-file)

1. Activate the virtual environment and launch the application (see Installation above).
2. Click **Upload CSV Files** and select one or more OPC data files.
3. The original data appears in the left panel.
4. Adjust settings as needed: hour offset, tagname, filters, encoding.
5. Click **Apply** — the converted preview appears in the right panel. The status bar shows row counts and a summary of removed/filtered rows.
6. Click **Download Converted CSV** to save the result.

### Batch Queue

1. Launch the application.
2. Configure settings (offset, filters, tagname option will be overridden to **Custom** using each tag name from the queue file, encoding).
3. In the **Batch Queue** panel, select the source directory, queue file, and output directory.
4. Click **Apply**. A summary dialog reports the result.
