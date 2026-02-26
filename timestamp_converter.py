#!/usr/bin/env python3
"""
Timestamp Converter Application
Converts US format timestamps in CSV files to DD-Mon-YYYY HH:MM:SS format.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
import pandas as pd
import os
import json
class TimestampConverterApp:
    def __init__(self, root):
        """Initialize the application with the main window."""
        self.root = root
        self.root.title("PI Tag Timestamp Converter")
        self.root.geometry("1200x700")
        self.root.minsize(900, 500)

        self.original_df = None
        self.converted_df = None
        self.previous_tagname_option = "None"  # Track previous selection
        self._first_filename = ""  # Store first uploaded filename for tagname default

        self._queue_source_dir = ""
        self._queue_file_path = ""
        self._queue_output_dir = ""

        self._last_preset_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "last_preset.json"
        )

        self.setup_ui()
        self._try_load_last_preset()

    def setup_ui(self):
        """Build the main UI with original/converted data panels and controls."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        self._setup_preview_panes(main_frame)
        self._setup_settings_panel(main_frame)
        self._setup_export_panel(main_frame)
        self._setup_queue_panel(main_frame)
        self._setup_status_bar(main_frame)

    def _setup_preview_panes(self, main_frame):
        """Add column headings and both data preview treeviews (rows 0-2)."""
        # ── Row 0: Column headings ─────────────────────────────────────────
        ttk.Label(main_frame, text="Original CSV (US Format)", font=("", 12, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 5)
        )
        ttk.Label(main_frame, text="Converted Preview (DD-Mon-YYYY Format)", font=("", 12, "bold")).grid(
            row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 5)
        )

        # ── Rows 1-2: Treeviews (both span 2 rows for equal height) ───────
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        self.original_tree = self.create_treeview(left_frame)

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=(10, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        self.converted_tree = self.create_treeview(right_frame)

    def _setup_settings_panel(self, main_frame):
        """Build the Settings LabelFrame (row 3, column 0)."""
        settings_lf = ttk.LabelFrame(main_frame, text="Settings", padding=8)
        settings_lf.grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=(10, 0))
        settings_lf.columnconfigure(0, weight=1)

        # Settings row 0: Upload, Hour offset, Tagname
        settings_row0 = ttk.Frame(settings_lf)
        settings_row0.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        ttk.Button(settings_row0, text="Upload CSV Files", command=self.upload_csv).pack(side=tk.LEFT)

        ttk.Label(settings_row0, text="  Hour offset:").pack(side=tk.LEFT, padx=(10, 5))
        self.offset_var = tk.StringVar(value="0")
        self.offset_entry = ttk.Entry(settings_row0, textvariable=self.offset_var, width=5)
        self.offset_entry.pack(side=tk.LEFT)

        tagname_frame = ttk.Frame(settings_row0)
        tagname_frame.pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(tagname_frame, text="Tagname:").pack(side=tk.LEFT, padx=(0, 5))
        self.tagname_option_var = tk.StringVar(value="None")
        self.tagname_combo = ttk.Combobox(
            tagname_frame,
            textvariable=self.tagname_option_var,
            values=["None", "Custom"],
            state="readonly",
            width=8
        )
        self.tagname_combo.pack(side=tk.LEFT)
        self.tagname_combo.bind("<<ComboboxSelected>>", self.on_tagname_option_changed)
        self.custom_tagname_var = tk.StringVar()
        self.custom_tagname_entry = ttk.Entry(tagname_frame, textvariable=self.custom_tagname_var, width=30)
        self.custom_tagname_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.custom_tagname_entry.pack_forget()  # Hidden by default

        # Settings row 1: Checkboxes
        settings_row1 = ttk.Frame(settings_lf)
        settings_row1.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        self.remove_bad_quality_var = tk.IntVar(value=0)
        ttk.Checkbutton(
            settings_row1, text="Remove bad quality",
            variable=self.remove_bad_quality_var, onvalue=1, offvalue=0
        ).pack(side=tk.LEFT)
        self.remove_duplicates_var = tk.IntVar(value=0)
        ttk.Checkbutton(
            settings_row1, text="Remove duplicate timestamps",
            variable=self.remove_duplicates_var, onvalue=1, offvalue=0
        ).pack(side=tk.LEFT, padx=(15, 0))

        # Highlight Apply when any setting changes
        for var in (self.offset_var, self.tagname_option_var, self.custom_tagname_var,
                    self.remove_bad_quality_var, self.remove_duplicates_var):
            var.trace_add("write", lambda *_: self._highlight_apply())

    def _setup_export_panel(self, main_frame):
        """Build the Export LabelFrame (row 3, column 1)."""
        export_lf = ttk.LabelFrame(main_frame, text="Export", padding=8)
        export_lf.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))
        export_lf.columnconfigure(0, weight=1)

        # Export row 0: Start / End date-time filters
        filter_row = ttk.Frame(export_lf)
        filter_row.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.start_filter_var, self.start_date_var, self.start_time_var, \
            self.start_date_entry, self.start_time_entry = \
            self._create_filter_row(filter_row, "Start:", "01-Jan-2025", "00:00:00")
        ttk.Label(filter_row, text="   ").pack(side=tk.LEFT)
        self.end_filter_var, self.end_date_var, self.end_time_var, \
            self.end_date_entry, self.end_time_entry = \
            self._create_filter_row(filter_row, "End:", "31-Dec-2025", "23:59:59")

        # Highlight Apply when any filter changes
        for var in (self.start_filter_var, self.end_filter_var,
                    self.start_date_var, self.end_date_var,
                    self.start_time_var, self.end_time_var):
            var.trace_add("write", lambda *_: self._highlight_apply())

        # Export row 1: Preset, Encoding, Download
        export_row = ttk.Frame(export_lf)
        export_row.grid(row=1, column=0, sticky="ew")
        ttk.Button(export_row, text="Save Preset", command=self.save_preset).pack(side=tk.LEFT)
        ttk.Button(export_row, text="Load Preset", command=self.load_preset).pack(side=tk.LEFT, padx=(5, 20))
        ttk.Label(export_row, text="Encoding:").pack(side=tk.LEFT)
        self.encoding_var = tk.StringVar(value="ANSI")
        encoding_combo = ttk.Combobox(
            export_row,
            textvariable=self.encoding_var,
            values=["ANSI", "UTF-8"],
            state="readonly",
            width=6
        )
        encoding_combo.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(export_row, text="Download Converted CSV", command=self.download_csv).pack(side=tk.RIGHT)

    def _setup_queue_panel(self, main_frame):
        """Build the Batch Queue LabelFrame (row 4)."""
        queue_lf = ttk.LabelFrame(main_frame, text="Batch Queue", padding=8)
        queue_lf.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        queue_lf.columnconfigure(2, weight=1)

        ttk.Label(queue_lf, text="Source Dir:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Button(queue_lf, text="Select", command=self._select_queue_source_dir).grid(row=0, column=1, padx=(0, 5))
        self._queue_source_dir_var = tk.StringVar(value="Not selected")
        ttk.Label(queue_lf, textvariable=self._queue_source_dir_var, anchor="w").grid(row=0, column=2, sticky="ew")

        ttk.Label(queue_lf, text="Queue File:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(4, 0))
        ttk.Button(queue_lf, text="Select", command=self._select_queue_file).grid(row=1, column=1, padx=(0, 5), pady=(4, 0))
        self._queue_file_var = tk.StringVar(value="Not selected")
        ttk.Label(queue_lf, textvariable=self._queue_file_var, anchor="w").grid(row=1, column=2, sticky="ew", pady=(4, 0))

        ttk.Label(queue_lf, text="Output Dir:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=(4, 0))
        ttk.Button(queue_lf, text="Select", command=self._select_queue_output_dir).grid(row=2, column=1, padx=(0, 5), pady=(4, 0))
        self._queue_output_dir_var = tk.StringVar(value="Not selected")
        ttk.Label(queue_lf, textvariable=self._queue_output_dir_var, anchor="w").grid(row=2, column=2, sticky="ew", pady=(4, 0))

        self.apply_btn = tk.Button(queue_lf, text="Apply", command=self.apply_conversion)
        self.apply_btn.grid(row=0, column=3, rowspan=3, sticky="ns", padx=(15, 0))
        self._apply_default_bg = self.apply_btn.cget("background")

    def _setup_status_bar(self, main_frame):
        """Build the status bar (row 5)."""
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready - Upload a CSV file to begin")
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w").grid(
            row=0, column=0, sticky="ew"
        )

        self.left_count_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.left_count_var, relief=tk.SUNKEN, anchor="center", width=20).grid(
            row=0, column=1, sticky="ew", padx=(2, 0)
        )

        self.right_count_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.right_count_var, relief=tk.SUNKEN, anchor="center", width=20).grid(
            row=0, column=2, sticky="ew", padx=(2, 0)
        )

    def create_treeview(self, parent):
        """Create a treeview widget with scrollbars."""
        # Frame for treeview and scrollbars
        tree_frame = ttk.Frame(parent)
        tree_frame.grid(row=0, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        # Treeview
        tree = ttk.Treeview(tree_frame, yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.config(command=tree.yview)
        h_scroll.config(command=tree.xview)

        # Grid layout
        tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        return tree

    def on_tagname_option_changed(self, event=None):
        """Show/hide custom tagname entry based on selection."""
        current_option = self.tagname_option_var.get()

        # Only process if the selection actually changed
        if current_option == self.previous_tagname_option:
            return

        self.previous_tagname_option = current_option

        if current_option == "Custom":
            self.custom_tagname_entry.pack(side=tk.LEFT, padx=(5, 0))
            if not self.custom_tagname_var.get() and self._first_filename:
                self.custom_tagname_var.set(self._first_filename)
        else:
            self.custom_tagname_entry.pack_forget()

    def _create_filter_row(self, parent, label, default_date, default_time):
        """Create a filter checkbox with date and time entry fields."""
        filter_var = tk.IntVar(value=0)
        date_var = tk.StringVar(value=default_date)
        time_var = tk.StringVar(value=default_time)

        date_entry = ttk.Entry(parent, textvariable=date_var, width=12, state="disabled")
        time_entry = ttk.Entry(parent, textvariable=time_var, width=8, state="disabled")

        check = ttk.Checkbutton(
            parent, text=label, variable=filter_var,
            onvalue=1, offvalue=0,
            command=lambda: self._toggle_filter(filter_var, date_entry, time_entry)
        )
        check.pack(side=tk.LEFT)
        date_entry.pack(side=tk.LEFT, padx=(5, 0))
        time_entry.pack(side=tk.LEFT, padx=(5, 0))

        return filter_var, date_var, time_var, date_entry, time_entry

    def _highlight_apply(self):
        """Highlight the Apply button to indicate pending changes."""
        self.apply_btn.configure(bg="#ffcc00", activebackground="#ffdd33")

    def _unhighlight_apply(self):
        """Reset the Apply button to its default appearance."""
        self.apply_btn.configure(bg=self._apply_default_bg, activebackground=self._apply_default_bg)

    def _clear_manual_data(self):
        """Clear manually loaded CSV data and both preview panes."""
        self.original_df = None
        self.converted_df = None
        self.original_tree.delete(*self.original_tree.get_children())
        self.converted_tree.delete(*self.converted_tree.get_children())
        self.left_count_var.set("")
        self.right_count_var.set("")

    def _clear_queue_paths(self):
        """Reset all batch queue path selections to 'Not selected'."""
        self._queue_source_dir = ""
        self._queue_source_dir_var.set("Not selected")
        self._queue_file_path = ""
        self._queue_file_var.set("Not selected")
        self._queue_output_dir = ""
        self._queue_output_dir_var.set("Not selected")

    def _toggle_filter(self, var, date_entry, time_entry):
        """Enable/disable filter date and time fields based on checkbox."""
        state = "normal" if var.get() == 1 else "disabled"
        date_entry.configure(state=state)
        time_entry.configure(state=state)

    def _parse_filter_datetime(self, date_str, time_str, default_time):
        """Parse date (DD-Mon-YYYY) and time (HH:MM:SS) strings into a datetime."""
        date = datetime.strptime(date_str.strip(), "%d-%b-%Y").date()
        try:
            t = datetime.strptime(time_str.strip(), "%H:%M:%S").time()
        except ValueError:
            t = datetime.strptime(default_time, "%H:%M:%S").time()
        return datetime.combine(date, t)

    def _convert_df(self, source_df, tagname):
        """Convert a source DataFrame applying all active filters and settings.

        Returns (converted_df, stats) where stats is a dict with keys:
        bad_quality_removed, rows_filtered, duplicates_removed.

        Raises ValueError if offset or date inputs are invalid.
        """
        try:
            hour_offset = int(self.offset_var.get())
        except ValueError:
            raise ValueError("Hour offset must be a valid integer (e.g., -5, 0, +3)")

        stats = {"bad_quality_removed": 0, "rows_filtered": 0, "duplicates_removed": 0}

        # Filter out bad quality rows
        df = source_df
        if self.remove_bad_quality_var.get() == 1:
            original_count = len(df)
            df = df[df["Quality"].astype(str).str.strip() != "0x100400c0"].reset_index(drop=True)
            stats["bad_quality_removed"] = original_count - len(df)

        # Vectorized timestamp conversion
        cleaned = df["Timestamp"].astype(str).str.strip().str.strip('"')
        cleaned = cleaned.str.replace(r' ([AP]M)\.\d+', r' \1', regex=True)
        parsed = pd.to_datetime(cleaned, format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
        if hour_offset != 0:
            parsed = parsed + pd.Timedelta(hours=hour_offset)
        converted_timestamps = parsed.dt.strftime("%d-%b-%Y %H:%M:%S")
        # Keep original string for rows that failed to parse
        failed = parsed.isna()
        if failed.any():
            converted_timestamps[failed] = df["Timestamp"][failed]

        # Build output dataframe
        if tagname:
            converted_df = pd.DataFrame({
                "Tagname": tagname,
                "Timestamp": converted_timestamps,
                "Value": df["Value"]
            })
        else:
            converted_df = pd.DataFrame({
                "Timestamp": converted_timestamps,
                "Value": df["Value"]
            })

        # Apply time range filters
        if self.start_filter_var.get() == 1 or self.end_filter_var.get() == 1:
            pre_filter_count = len(converted_df)
            parsed_ts = pd.to_datetime(
                converted_df["Timestamp"], format="%d-%b-%Y %H:%M:%S", errors="coerce"
            )
            mask = parsed_ts.notna()

            if self.start_filter_var.get() == 1:
                try:
                    start_dt = self._parse_filter_datetime(
                        self.start_date_var.get(), self.start_time_var.get(), "00:00:00"
                    )
                    mask = mask & (parsed_ts >= pd.Timestamp(start_dt))
                except ValueError:
                    raise ValueError("Invalid start date. Use DD-Mon-YYYY format (e.g. 01-Jan-2025)")

            if self.end_filter_var.get() == 1:
                try:
                    end_dt = self._parse_filter_datetime(
                        self.end_date_var.get(), self.end_time_var.get(), "23:59:59"
                    )
                    mask = mask & (parsed_ts <= pd.Timestamp(end_dt))
                except ValueError:
                    raise ValueError("Invalid end date. Use DD-Mon-YYYY format (e.g. 31-Dec-2025)")

            converted_df = converted_df[mask].reset_index(drop=True)
            stats["rows_filtered"] = pre_filter_count - len(converted_df)

        # Remove duplicate timestamps if checkbox is checked
        if self.remove_duplicates_var.get() == 1:
            original_count = len(converted_df)
            converted_df = converted_df.drop_duplicates(subset=["Timestamp"], keep="first").reset_index(drop=True)
            stats["duplicates_removed"] = original_count - len(converted_df)

        return converted_df, stats

    def apply_conversion(self):
        """Apply conversion settings and preview the loaded CSV."""
        self._unhighlight_apply()

        # Queue mode: all three queue paths are set — run batch export
        if self._queue_source_dir and self._queue_file_path and self._queue_output_dir:
            self.run_queue()
            return

        # Manual mode: preview conversion of the loaded file
        if self.original_df is None:
            messagebox.showwarning("Warning", "No data loaded. Please upload CSV files first.")
            return

        # Determine tagname
        tagname_option = self.tagname_option_var.get()
        tagname = None
        if tagname_option == "Custom":
            tagname = self.custom_tagname_var.get().strip() or None

        try:
            self.converted_df, stats = self._convert_df(self.original_df, tagname)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        # Update display
        self.populate_treeview(self.converted_tree, self.converted_df)

        # Update status and row counts
        row_count = len(self.converted_df)
        self.right_count_var.set(f"Converted: {row_count} rows")
        hour_offset = int(self.offset_var.get())
        offset_msg = f" (offset: {hour_offset:+d}h)" if hour_offset != 0 else ""
        bad_msg = f", {stats['bad_quality_removed']} bad quality removed" if stats['bad_quality_removed'] > 0 else ""
        filter_msg = f", {stats['rows_filtered']} rows filtered out" if stats['rows_filtered'] > 0 else ""
        dup_msg = f", {stats['duplicates_removed']} duplicates removed" if stats['duplicates_removed'] > 0 else ""
        self.status_var.set(f"Preview updated - {row_count} rows converted{offset_msg}{bad_msg}{filter_msg}{dup_msg}")
        self._save_last_preset()

    def _parse_opc_timestamp(self, timestamp_str):
        """Parse OPC server timestamp into a datetime object.

        Input: "11/25/2025 2:02:03 PM.2390000" (MM/DD/YYYY H:MM:SS AM/PM.milliseconds)
        Returns datetime object, or datetime.min if parsing fails.
        """
        try:
            timestamp_str = str(timestamp_str).strip().strip('"')
            if " AM." in timestamp_str:
                timestamp_str = timestamp_str.split(" AM.")[0] + " AM"
            elif " PM." in timestamp_str:
                timestamp_str = timestamp_str.split(" PM.")[0] + " PM"
            return datetime.strptime(timestamp_str, "%m/%d/%Y %I:%M:%S %p")
        except ValueError:
            return datetime.min

    def populate_treeview(self, tree, df):
        """Populate a treeview with dataframe data."""
        # Clear existing data
        tree.delete(*tree.get_children())

        # Set up columns
        columns = list(df.columns)
        tree["columns"] = columns
        tree["show"] = "headings"

        for col in columns:
            tree.heading(col, text=col)
            # Set column width based on content
            max_width = max(
                len(str(col)),
                df[col].astype(str).str.len().max() if len(df) > 0 else 0
            )
            # Ensure Timestamp column is wide enough to show full value
            if col == "Timestamp":
                tree.column(col, width=200, minwidth=180)
            else:
                tree.column(col, width=min(max_width * 10, 300), minwidth=100)

        # Insert data
        for row in df.astype(str).values.tolist():
            tree.insert("", tk.END, values=row)

    def upload_csv(self):
        """Handle multiple file upload (space-delimited OPC data or CSV)."""
        file_paths = filedialog.askopenfilenames(
            title="Select Data Files",
            filetypes=[("All supported", "*.csv *.txt"), ("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not file_paths:
            return

        # Switching to manual mode — clear entire batch queue
        self._clear_queue_paths()

        try:
            # Read and combine all selected files
            dataframes = []
            for file_path in file_paths:
                # Read comma-delimited file without headers (OPC format)
                # Format: 12/3/2025 5:28:11 AM.7480000,651.261902,0x400c0
                df = pd.read_csv(
                    file_path,
                    header=None,
                    names=["Timestamp", "Value", "Quality"]
                )
                dataframes.append(df)

            # Store first filename (without extension) for tagname default
            self._first_filename = os.path.splitext(os.path.basename(file_paths[0]))[0]

            # Concatenate all dataframes
            self.original_df = pd.concat(dataframes, ignore_index=True)

            # Sort by parsed timestamps
            self.original_df = self.original_df.sort_values(
                "Timestamp", key=lambda col: col.apply(self._parse_opc_timestamp)
            ).reset_index(drop=True)

            # Clear the converted preview (user must click Apply)
            self.converted_df = None
            self.converted_tree.delete(*self.converted_tree.get_children())

            # Display original data
            self.populate_treeview(self.original_tree, self.original_df)

            # Update status and row counts
            row_count = len(self.original_df)
            self.left_count_var.set(f"Source: {row_count} rows")
            self.right_count_var.set("")
            file_count = len(file_paths)
            if file_count == 1:
                filename = os.path.basename(file_paths[0])
                self.status_var.set(f"Loaded: {filename} - {row_count} rows. Click Apply to convert.")
            else:
                self.status_var.set(f"Loaded {file_count} files - {row_count} total rows. Click Apply to convert.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load files:\n{str(e)}")
            self.status_var.set("Error loading files")

    def download_csv(self):
        """Handle converted CSV download."""
        if self.converted_df is None:
            messagebox.showwarning("Warning", "No converted data to download. Please upload files and click Apply first.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Converted CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Get selected encoding
            encoding = "utf-8" if self.encoding_var.get() == "UTF-8" else "cp1252"
            self.converted_df.to_csv(file_path, index=False, header=False, encoding=encoding)
            self.status_var.set(f"Saved: {os.path.basename(file_path)} ({self.encoding_var.get()})")
            messagebox.showinfo("Success", f"File saved successfully:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")


    def _select_queue_source_dir(self):
        """Open dialog to select the source directory for batch queue."""
        d = filedialog.askdirectory(title="Select Source Directory")
        if d:
            self._queue_source_dir = d
            name = os.path.basename(d) or d
            self._queue_source_dir_var.set(name[:30])
            # Switching to queue mode — clear manually loaded data
            if self.original_df is not None:
                self._clear_manual_data()
            self._update_queue_status()

    def _select_queue_file(self):
        """Open dialog to select the queue text file."""
        f = filedialog.askopenfilename(
            title="Select Queue File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if f:
            self._queue_file_path = f
            name = os.path.basename(f)
            self._queue_file_var.set(name[:30])
            # Switching to queue mode — clear any manually loaded data
            if self.original_df is not None:
                self._clear_manual_data()
            self._update_queue_status()

    def _select_queue_output_dir(self):
        """Open dialog to select the output directory for batch queue."""
        d = filedialog.askdirectory(title="Select Output Directory")
        if d:
            self._queue_output_dir = d
            name = os.path.basename(d) or d
            self._queue_output_dir_var.set(name[:30])
            # Switching to queue mode — clear manually loaded data
            if self.original_df is not None:
                self._clear_manual_data()
            self._update_queue_status()

    def _update_queue_status(self):
        """Update status bar to reflect queue setup progress."""
        if self._queue_source_dir and self._queue_file_path and self._queue_output_dir:
            self._highlight_apply()
            self.status_var.set("Queue ready — click Apply to export")
        else:
            missing = []
            if not self._queue_source_dir:
                missing.append("source dir")
            if not self._queue_file_path:
                missing.append("queue file")
            if not self._queue_output_dir:
                missing.append("output dir")
            self.status_var.set(f"Queue: still need — {', '.join(missing)}")

    def run_queue(self):
        """Run the batch queue export: one output CSV per tag in the queue file."""
        # Validate all paths are set
        if not self._queue_source_dir:
            messagebox.showerror("Error", "Please select a source directory.")
            return
        if not self._queue_file_path:
            messagebox.showerror("Error", "Please select a queue file.")
            return
        if not self._queue_output_dir:
            messagebox.showerror("Error", "Please select an output directory.")
            return

        # Validate offset
        try:
            int(self.offset_var.get())
        except ValueError:
            messagebox.showerror("Error", "Hour offset must be a valid integer (e.g., -5, 0, +3)")
            return

        # Read queue file
        try:
            with open(self._queue_file_path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read queue file:\n{str(e)}")
            return

        tags = [line.strip() for line in lines if line.strip()]
        if not tags:
            messagebox.showwarning("Warning", "Queue file is empty or contains no valid tag names.")
            return

        encoding = "utf-8" if self.encoding_var.get() == "UTF-8" else "cp1252"

        exported = 0
        skipped = []
        errors = []

        for tag in tags:
            # Find matching files in source dir
            try:
                matching = [
                    fname for fname in os.listdir(self._queue_source_dir)
                    if fname.startswith(tag) and (fname.endswith(".csv") or fname.endswith(".txt"))
                ]
            except Exception as e:
                errors.append(f"{tag}: {str(e)}")
                continue

            if not matching:
                skipped.append(tag)
                continue

            # Read and concat matching files
            try:
                dataframes = []
                for fname in matching:
                    fpath = os.path.join(self._queue_source_dir, fname)
                    df = pd.read_csv(fpath, header=None, names=["Timestamp", "Value", "Quality"])
                    dataframes.append(df)

                combined = pd.concat(dataframes, ignore_index=True)
                combined = combined.sort_values(
                    "Timestamp", key=lambda col: col.apply(self._parse_opc_timestamp)
                ).reset_index(drop=True)

                converted_df, _ = self._convert_df(combined, tagname=tag)

                out_path = os.path.join(self._queue_output_dir, tag + ".csv")
                converted_df.to_csv(out_path, index=False, header=False, encoding=encoding)
                exported += 1
            except Exception as e:
                errors.append(f"{tag}: {str(e)}")
                continue

        # Update status bar
        skip_msg = f", {len(skipped)} skipped (no files found)" if skipped else ""
        err_msg = f", {len(errors)} failed" if errors else ""
        self.status_var.set(f"Queue done: {exported} exported{skip_msg}{err_msg}")
        self._save_last_preset()

        # Show summary dialog
        if skipped or errors:
            details = []
            if skipped:
                details.append("Skipped (no matching files):\n" + "\n".join(f"  \u2022 {t}" for t in skipped))
            if errors:
                details.append("Errors:\n" + "\n".join(f"  \u2022 {e}" for e in errors))
            messagebox.showinfo(
                "Queue Complete",
                f"Exported: {exported} file(s)\n\n" + "\n\n".join(details)
            )
        else:
            messagebox.showinfo("Queue Complete", f"Successfully exported {exported} file(s).")


    def _collect_preset(self):
        """Gather all current settings into a dict."""
        return {
            "hour_offset": self.offset_var.get(),
            "remove_bad_quality": self.remove_bad_quality_var.get(),
            "remove_duplicates": self.remove_duplicates_var.get(),
            "start_filter": self.start_filter_var.get(),
            "start_date": self.start_date_var.get(),
            "start_time": self.start_time_var.get(),
            "end_filter": self.end_filter_var.get(),
            "end_date": self.end_date_var.get(),
            "end_time": self.end_time_var.get(),
            "tagname_option": self.tagname_option_var.get(),
            "custom_tagname": self.custom_tagname_var.get(),
            "encoding": self.encoding_var.get(),
        }

    def _apply_preset(self, data):
        """Apply a settings dict to all UI variables."""
        self.offset_var.set(data.get("hour_offset", "0"))
        self.remove_bad_quality_var.set(data.get("remove_bad_quality", 0))
        self.remove_duplicates_var.set(data.get("remove_duplicates", 0))

        self.start_filter_var.set(data.get("start_filter", 0))
        self.start_date_var.set(data.get("start_date", "01-Jan-2025"))
        self.start_time_var.set(data.get("start_time", "00:00:00"))
        self._toggle_filter(self.start_filter_var, self.start_date_entry, self.start_time_entry)

        self.end_filter_var.set(data.get("end_filter", 0))
        self.end_date_var.set(data.get("end_date", "31-Dec-2025"))
        self.end_time_var.set(data.get("end_time", "23:59:59"))
        self._toggle_filter(self.end_filter_var, self.end_date_entry, self.end_time_entry)

        opt = data.get("tagname_option", "None")
        self.tagname_option_var.set(opt)
        self.custom_tagname_var.set(data.get("custom_tagname", ""))
        self.previous_tagname_option = opt
        if opt == "Custom":
            self.custom_tagname_entry.pack(side=tk.LEFT, padx=(5, 0))
        else:
            self.custom_tagname_entry.pack_forget()

        self.encoding_var.set(data.get("encoding", "ANSI"))

    def _save_last_preset(self):
        """Silently save current settings to last_preset.json."""
        try:
            with open(self._last_preset_path, "w", encoding="utf-8") as f:
                json.dump(self._collect_preset(), f, indent=2)
        except Exception:
            pass

    def _try_load_last_preset(self):
        """Silently load last_preset.json on startup if it exists."""
        if os.path.exists(self._last_preset_path):
            try:
                with open(self._last_preset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._apply_preset(data)
                self._unhighlight_apply()
            except Exception:
                pass

    def save_preset(self):
        """Save current settings to a user-chosen JSON file."""
        path = filedialog.asksaveasfilename(
            title="Save Preset",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            data = self._collect_preset()
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                self._save_last_preset()
                self.status_var.set(f"Preset saved: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save preset:\n{str(e)}")

    def load_preset(self):
        """Load settings from a user-chosen JSON file."""
        path = filedialog.askopenfilename(
            title="Load Preset",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._apply_preset(data)
                self._unhighlight_apply()
                self.status_var.set(f"Preset loaded: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load preset:\n{str(e)}")


def main():
    root = tk.Tk()
    app = TimestampConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
