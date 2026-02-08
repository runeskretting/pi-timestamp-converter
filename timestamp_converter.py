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

        self.setup_ui()

    def setup_ui(self):
        """Build the main UI with original/converted data panels and controls."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights for responsive layout
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=0)
        main_frame.rowconfigure(2, weight=1)

        # Left panel - Original CSV
        left_label = ttk.Label(main_frame, text="Original CSV (US Format)", font=("", 12, "bold"))
        left_label.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 5))

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        # Original data treeview with scrollbars
        self.original_tree = self.create_treeview(left_frame)

        # Upload button and hour offset in a row
        left_controls = ttk.Frame(main_frame)
        left_controls.grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=10)

        upload_btn = ttk.Button(left_controls, text="Upload CSV Files", command=self.upload_csv)
        upload_btn.pack(side=tk.LEFT)

        ttk.Label(left_controls, text="  Hour offset:").pack(side=tk.LEFT, padx=(10, 5))
        self.offset_var = tk.StringVar(value="0")
        self.offset_entry = ttk.Entry(left_controls, textvariable=self.offset_var, width=5)
        self.offset_entry.pack(side=tk.LEFT)

        # Tagname section in its own frame to keep entry next to dropdown
        tagname_frame = ttk.Frame(left_controls)
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

        self.remove_bad_quality_var = tk.IntVar(value=0)
        remove_bad_check = ttk.Checkbutton(
            left_controls,
            text="Remove bad quality",
            variable=self.remove_bad_quality_var,
            onvalue=1,
            offvalue=0
        )
        remove_bad_check.pack(side=tk.LEFT, padx=(15, 0))

        self.remove_duplicates_var = tk.IntVar(value=0)
        remove_dup_check = ttk.Checkbutton(
            left_controls,
            text="Remove duplicate timestamps",
            variable=self.remove_duplicates_var,
            onvalue=1,
            offvalue=0
        )
        remove_dup_check.pack(side=tk.LEFT, padx=(15, 0))

        self.apply_btn = tk.Button(left_controls, text="Apply", command=self.apply_conversion)
        self.apply_btn.pack(side=tk.RIGHT)
        self._apply_default_bg = self.apply_btn.cget("background")

        # Highlight Apply button when any option changes
        self.offset_var.trace_add("write", lambda *_: self._highlight_apply())
        self.tagname_option_var.trace_add("write", lambda *_: self._highlight_apply())
        self.custom_tagname_var.trace_add("write", lambda *_: self._highlight_apply())
        self.remove_bad_quality_var.trace_add("write", lambda *_: self._highlight_apply())
        self.remove_duplicates_var.trace_add("write", lambda *_: self._highlight_apply())

        # Right panel - Converted CSV
        right_label = ttk.Label(main_frame, text="Converted Preview (DD-Mon-YYYY Format)", font=("", 12, "bold"))
        right_label.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 5))

        # Filter controls above the converted treeview
        filter_frame = ttk.Frame(main_frame)
        filter_frame.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 5))

        # Start filter
        self.start_filter_var = tk.IntVar(value=0)
        start_check = ttk.Checkbutton(
            filter_frame, text="Start:",
            variable=self.start_filter_var,
            onvalue=1, offvalue=0,
            command=self._toggle_start_filter
        )
        start_check.pack(side=tk.LEFT)

        self.start_date_var = tk.StringVar(value="01-Jan-2025")
        self.start_date_entry = ttk.Entry(
            filter_frame, textvariable=self.start_date_var,
            width=12, state="disabled"
        )
        self.start_date_entry.pack(side=tk.LEFT, padx=(5, 0))

        self.start_time_var = tk.StringVar(value="00:00:00")
        self.start_time_entry = ttk.Entry(
            filter_frame, textvariable=self.start_time_var,
            width=8, state="disabled"
        )
        self.start_time_entry.pack(side=tk.LEFT, padx=(5, 0))

        # Spacer
        ttk.Label(filter_frame, text="   ").pack(side=tk.LEFT)

        # End filter
        self.end_filter_var = tk.IntVar(value=0)
        end_check = ttk.Checkbutton(
            filter_frame, text="End:",
            variable=self.end_filter_var,
            onvalue=1, offvalue=0,
            command=self._toggle_end_filter
        )
        end_check.pack(side=tk.LEFT)

        self.end_date_var = tk.StringVar(value="31-Dec-2025")
        self.end_date_entry = ttk.Entry(
            filter_frame, textvariable=self.end_date_var,
            width=12, state="disabled"
        )
        self.end_date_entry.pack(side=tk.LEFT, padx=(5, 0))

        self.end_time_var = tk.StringVar(value="23:59:59")
        self.end_time_entry = ttk.Entry(
            filter_frame, textvariable=self.end_time_var,
            width=8, state="disabled"
        )
        self.end_time_entry.pack(side=tk.LEFT, padx=(5, 0))

        # Highlight Apply button when filter options change
        self.start_filter_var.trace_add("write", lambda *_: self._highlight_apply())
        self.end_filter_var.trace_add("write", lambda *_: self._highlight_apply())
        self.start_date_var.trace_add("write", lambda *_: self._highlight_apply())
        self.end_date_var.trace_add("write", lambda *_: self._highlight_apply())
        self.start_time_var.trace_add("write", lambda *_: self._highlight_apply())
        self.end_time_var.trace_add("write", lambda *_: self._highlight_apply())

        # Converted data treeview with scrollbars (below filters)
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=2, column=1, sticky="nsew", padx=(10, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

        self.converted_tree = self.create_treeview(right_frame)

        # Right panel controls
        right_controls = ttk.Frame(main_frame)
        right_controls.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=10)

        ttk.Label(right_controls, text="Encoding:").pack(side=tk.LEFT)
        self.encoding_var = tk.StringVar(value="ANSI")
        encoding_combo = ttk.Combobox(
            right_controls,
            textvariable=self.encoding_var,
            values=["ANSI", "UTF-8"],
            state="readonly",
            width=6
        )
        encoding_combo.pack(side=tk.LEFT, padx=(5, 0))

        download_btn = ttk.Button(right_controls, text="Download Converted CSV", command=self.download_csv)
        download_btn.pack(side=tk.RIGHT)

        # Status bar with row counts
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready - Upload a CSV file to begin")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_label.grid(row=0, column=0, sticky="ew")

        self.left_count_var = tk.StringVar(value="")
        left_count_label = ttk.Label(status_frame, textvariable=self.left_count_var, relief=tk.SUNKEN, anchor="center", width=20)
        left_count_label.grid(row=0, column=1, sticky="ew", padx=(2, 0))

        self.right_count_var = tk.StringVar(value="")
        right_count_label = ttk.Label(status_frame, textvariable=self.right_count_var, relief=tk.SUNKEN, anchor="center", width=20)
        right_count_label.grid(row=0, column=2, sticky="ew", padx=(2, 0))

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

    def _highlight_apply(self):
        """Highlight the Apply button to indicate pending changes."""
        self.apply_btn.configure(bg="#ffcc00", activebackground="#ffdd33")

    def _unhighlight_apply(self):
        """Reset the Apply button to its default appearance."""
        self.apply_btn.configure(bg=self._apply_default_bg, activebackground=self._apply_default_bg)

    def _toggle_start_filter(self):
        """Enable/disable start filter date and time fields."""
        if self.start_filter_var.get() == 1:
            self.start_date_entry.configure(state="normal")
            self.start_time_entry.configure(state="normal")
        else:
            self.start_date_entry.configure(state="disabled")
            self.start_time_entry.configure(state="disabled")

    def _toggle_end_filter(self):
        """Enable/disable end filter date and time fields."""
        if self.end_filter_var.get() == 1:
            self.end_date_entry.configure(state="normal")
            self.end_time_entry.configure(state="normal")
        else:
            self.end_date_entry.configure(state="disabled")
            self.end_time_entry.configure(state="disabled")

    def _parse_filter_datetime(self, date_str, time_str, default_time):
        """Parse date (DD-Mon-YYYY) and time (HH:MM:SS) strings into a datetime."""
        date = datetime.strptime(date_str.strip(), "%d-%b-%Y").date()
        try:
            t = datetime.strptime(time_str.strip(), "%H:%M:%S").time()
        except ValueError:
            t = datetime.strptime(default_time, "%H:%M:%S").time()
        return datetime.combine(date, t)

    def apply_conversion(self):
        """Apply conversion settings and update the preview panel."""
        self._unhighlight_apply()
        if self.original_df is None:
            messagebox.showwarning("Warning", "No data loaded. Please upload CSV files first.")
            return

        try:
            hour_offset = int(self.offset_var.get())
        except ValueError:
            messagebox.showerror("Error", "Hour offset must be a valid integer (e.g., -5, 0, +3)")
            return

        # Determine tagname
        tagname_option = self.tagname_option_var.get()
        tagname = None
        if tagname_option == "Custom":
            tagname = self.custom_tagname_var.get().strip() or None

        # Filter out bad quality rows
        bad_quality_removed = 0
        source_df = self.original_df
        if self.remove_bad_quality_var.get() == 1:
            original_count = len(source_df)
            source_df = source_df[source_df["Quality"].astype(str).str.strip() != "0x100400c0"].reset_index(drop=True)
            bad_quality_removed = original_count - len(source_df)

        # Convert timestamps
        converted_timestamps = source_df["Timestamp"].apply(
            lambda ts: self.convert_timestamp(ts, hour_offset)
        )

        # Build output dataframe
        if tagname:
            self.converted_df = pd.DataFrame({
                "Tagname": tagname,
                "Timestamp": converted_timestamps,
                "Value": source_df["Value"]
            })
        else:
            self.converted_df = pd.DataFrame({
                "Timestamp": converted_timestamps,
                "Value": source_df["Value"]
            })

        # Apply time range filters
        rows_filtered = 0
        if self.start_filter_var.get() == 1 or self.end_filter_var.get() == 1:
            pre_filter_count = len(self.converted_df)
            parsed_ts = pd.to_datetime(
                self.converted_df["Timestamp"], format="%d-%b-%Y %H:%M:%S", errors="coerce"
            )
            mask = parsed_ts.notna()

            if self.start_filter_var.get() == 1:
                try:
                    start_dt = self._parse_filter_datetime(
                        self.start_date_var.get(), self.start_time_var.get(), "00:00:00"
                    )
                    mask = mask & (parsed_ts >= pd.Timestamp(start_dt))
                except ValueError:
                    messagebox.showerror("Error", "Invalid start date. Use DD-Mon-YYYY format (e.g. 01-Jan-2025)")
                    return

            if self.end_filter_var.get() == 1:
                try:
                    end_dt = self._parse_filter_datetime(
                        self.end_date_var.get(), self.end_time_var.get(), "23:59:59"
                    )
                    mask = mask & (parsed_ts <= pd.Timestamp(end_dt))
                except ValueError:
                    messagebox.showerror("Error", "Invalid end date. Use DD-Mon-YYYY format (e.g. 31-Dec-2025)")
                    return

            self.converted_df = self.converted_df[mask].reset_index(drop=True)
            rows_filtered = pre_filter_count - len(self.converted_df)

        # Remove duplicate timestamps if checkbox is checked
        duplicates_removed = 0
        if self.remove_duplicates_var.get() == 1:
            original_count = len(self.converted_df)
            self.converted_df = self.converted_df.drop_duplicates(subset=["Timestamp"], keep="first").reset_index(drop=True)
            duplicates_removed = original_count - len(self.converted_df)

        # Update display
        self.populate_treeview(self.converted_tree, self.converted_df)

        # Update status and row counts
        row_count = len(self.converted_df)
        self.right_count_var.set(f"Converted: {row_count} rows")
        offset_msg = f" (offset: {hour_offset:+d}h)" if hour_offset != 0 else ""
        bad_msg = f", {bad_quality_removed} bad quality removed" if bad_quality_removed > 0 else ""
        filter_msg = f", {rows_filtered} rows filtered out" if rows_filtered > 0 else ""
        dup_msg = f", {duplicates_removed} duplicates removed" if duplicates_removed > 0 else ""
        self.status_var.set(f"Preview updated - {row_count} rows converted{offset_msg}{bad_msg}{filter_msg}{dup_msg}")

    def convert_timestamp(self, timestamp_str, hour_offset=0):
        """
        Convert OPC server timestamp to DD-Mon-YYYY HH:MM:SS format.

        Input: "11/25/2025 2:02:03 PM.2390000" (MM/DD/YYYY H:MM:SS AM/PM.milliseconds)
        Output: "25-Nov-2025 14:02:03" (DD-Mon-YYYY HH:MM:SS, 24-hour, no milliseconds)

        Args:
            timestamp_str: The timestamp string to convert
            hour_offset: Hours to add/subtract for timezone adjustment
        """
        try:
            timestamp_str = str(timestamp_str).strip().strip('"')

            # Remove milliseconds (everything after AM/PM)
            if " AM." in timestamp_str:
                timestamp_str = timestamp_str.split(" AM.")[0] + " AM"
            elif " PM." in timestamp_str:
                timestamp_str = timestamp_str.split(" PM.")[0] + " PM"

            # Parse OPC format: MM/DD/YYYY H:MM:SS AM/PM
            dt = datetime.strptime(timestamp_str, "%m/%d/%Y %I:%M:%S %p")

            # Apply hour offset for timezone adjustment
            if hour_offset != 0:
                dt = dt + timedelta(hours=hour_offset)

            # Convert to output format
            return dt.strftime("%d-%b-%Y %H:%M:%S")
        except ValueError:
            # Return original if conversion fails
            return timestamp_str

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
        for _, row in df.iterrows():
            values = [str(v) for v in row]
            tree.insert("", tk.END, values=values)

    def parse_timestamp_for_sort(self, timestamp_str):
        """Parse OPC timestamp for sorting purposes."""
        try:
            timestamp_str = str(timestamp_str).strip().strip('"')

            # Remove milliseconds (everything after AM/PM)
            if " AM." in timestamp_str:
                timestamp_str = timestamp_str.split(" AM.")[0] + " AM"
            elif " PM." in timestamp_str:
                timestamp_str = timestamp_str.split(" PM.")[0] + " PM"

            # Parse OPC format: MM/DD/YYYY H:MM:SS AM/PM
            return datetime.strptime(timestamp_str, "%m/%d/%Y %I:%M:%S %p")
        except ValueError:
            # Return a default datetime for unparseable timestamps
            return datetime.min

    def upload_csv(self):
        """Handle multiple file upload (space-delimited OPC data or CSV)."""
        file_paths = filedialog.askopenfilenames(
            title="Select Data Files",
            filetypes=[("All supported", "*.csv *.txt"), ("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not file_paths:
            return

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

            # Parse timestamps for sorting
            self.original_df["_parsed_ts"] = self.original_df["Timestamp"].apply(self.parse_timestamp_for_sort)
            self.original_df = self.original_df.sort_values("_parsed_ts").reset_index(drop=True)

            # Drop the helper column
            self.original_df = self.original_df.drop(columns=["_parsed_ts"])

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


def main():
    root = tk.Tk()
    app = TimestampConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
