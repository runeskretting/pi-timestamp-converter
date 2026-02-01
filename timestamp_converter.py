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
        self.current_filename = None
        self.pending_update = None  # For debounced updates

        self.setup_ui()

    def setup_ui(self):
        """Build the main UI with original/converted data panels and controls."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights for responsive layout
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Left panel - Original CSV
        left_label = ttk.Label(main_frame, text="Original CSV (US Format)", font=("", 12, "bold"))
        left_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        # Original data treeview with scrollbars
        self.original_tree = self.create_treeview(left_frame)

        # Upload button and hour offset in a row
        left_controls = ttk.Frame(main_frame)
        left_controls.grid(row=2, column=0, sticky="w", pady=10)

        upload_btn = ttk.Button(left_controls, text="Upload CSV File", command=self.upload_csv)
        upload_btn.pack(side=tk.LEFT)

        ttk.Label(left_controls, text="  Hour offset:").pack(side=tk.LEFT, padx=(10, 5))
        self.offset_var = tk.StringVar(value="0")
        self.offset_entry = ttk.Entry(left_controls, textvariable=self.offset_var, width=5)
        self.offset_entry.pack(side=tk.LEFT)

        ttk.Label(left_controls, text="  Tagname:").pack(side=tk.LEFT, padx=(10, 5))
        self.tagname_option_var = tk.StringVar(value="None")
        self.tagname_combo = ttk.Combobox(
            left_controls,
            textvariable=self.tagname_option_var,
            values=["None", "Filename", "Custom"],
            state="readonly",
            width=8
        )
        self.tagname_combo.pack(side=tk.LEFT)
        self.tagname_combo.bind("<<ComboboxSelected>>", self.on_tagname_option_changed)

        self.custom_tagname_var = tk.StringVar()
        self.custom_tagname_var.trace_add("write", self.on_custom_tagname_changed)
        self.custom_tagname_entry = ttk.Entry(left_controls, textvariable=self.custom_tagname_var, width=20)
        self.custom_tagname_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.custom_tagname_entry.pack_forget()  # Hidden by default

        # Right panel - Converted CSV
        right_label = ttk.Label(main_frame, text="Converted Preview (DD-Mon-YYYY Format)", font=("", 12, "bold"))
        right_label.grid(row=0, column=1, sticky="w", pady=(0, 5))

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

        # Converted data treeview with scrollbars
        self.converted_tree = self.create_treeview(right_frame)

        # Download button
        download_btn = ttk.Button(main_frame, text="Download Converted CSV", command=self.download_csv)
        download_btn.grid(row=2, column=1, sticky="w", pady=10)

        # Status bar
        self.status_var = tk.StringVar(value="Ready - Upload a CSV file to begin")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))

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
        if self.tagname_option_var.get() == "Custom":
            # Pre-fill with filename if available
            if self.current_filename:
                self.custom_tagname_var.set(self.current_filename)
            self.custom_tagname_entry.pack(side=tk.LEFT, padx=(5, 0))
        else:
            self.custom_tagname_entry.pack_forget()
        # Refresh display when option changes
        self.schedule_refresh()

    def on_custom_tagname_changed(self, *args):
        """Handle changes to custom tagname with debounce."""
        self.schedule_refresh()

    def schedule_refresh(self):
        """Schedule a debounced refresh of the converted display."""
        # Cancel any pending update
        if self.pending_update:
            self.root.after_cancel(self.pending_update)
        # Schedule new update after 500ms
        if self.original_df is not None:
            self.pending_update = self.root.after(500, self.refresh_converted_display)

    def refresh_converted_display(self):
        """Refresh the converted data display with current settings."""
        self.pending_update = None
        if self.original_df is None:
            return

        try:
            hour_offset = int(self.offset_var.get())
        except ValueError:
            hour_offset = 0

        # Determine tagname
        tagname_option = self.tagname_option_var.get()
        tagname = None
        if tagname_option == "Filename":
            tagname = self.current_filename
        elif tagname_option == "Custom":
            tagname = self.custom_tagname_var.get().strip() or None

        # Convert timestamps
        converted_timestamps = self.original_df["Timestamp"].apply(
            lambda ts: self.convert_timestamp(ts, hour_offset)
        )

        # Build output dataframe
        if tagname:
            self.converted_df = pd.DataFrame({
                "Tagname": tagname,
                "Timestamp": converted_timestamps,
                "Value": self.original_df["Value"]
            })
        else:
            self.converted_df = pd.DataFrame({
                "Timestamp": converted_timestamps,
                "Value": self.original_df["Value"]
            })

        # Update display
        self.populate_treeview(self.converted_tree, self.converted_df)

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

    def upload_csv(self):
        """Handle file upload (space-delimited OPC data or CSV)."""
        file_path = filedialog.askopenfilename(
            title="Select Data File",
            filetypes=[("All supported", "*.csv *.txt"), ("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Validate and parse hour offset
            try:
                hour_offset = int(self.offset_var.get())
            except ValueError:
                messagebox.showerror("Error", "Hour offset must be a valid integer (e.g., -5, 0, +3)")
                return

            # Read comma-delimited file without headers (OPC format)
            # Format: 12/3/2025 5:28:11 AM.7480000,651.261902,0x400c0
            self.original_df = pd.read_csv(
                file_path,
                header=None,
                names=["Timestamp", "Value", "Quality"]
            )

            # Store filename (without extension) for tagname option
            self.current_filename = os.path.splitext(os.path.basename(file_path))[0]

            # Display original data
            self.populate_treeview(self.original_tree, self.original_df)

            # Determine tagname
            tagname_option = self.tagname_option_var.get()
            tagname = None
            if tagname_option == "Filename":
                tagname = self.current_filename
            elif tagname_option == "Custom":
                # Pre-fill with filename if empty
                if not self.custom_tagname_var.get().strip():
                    self.custom_tagname_var.set(self.current_filename)
                tagname = self.custom_tagname_var.get().strip() or None

            # Convert timestamps with hour offset
            converted_timestamps = self.original_df["Timestamp"].apply(
                lambda ts: self.convert_timestamp(ts, hour_offset)
            )

            # Build output dataframe: tagname (optional), timestamp, value
            if tagname:
                self.converted_df = pd.DataFrame({
                    "Tagname": tagname,
                    "Timestamp": converted_timestamps,
                    "Value": self.original_df["Value"]
                })
            else:
                self.converted_df = pd.DataFrame({
                    "Timestamp": converted_timestamps,
                    "Value": self.original_df["Value"]
                })

            # Display converted data
            self.populate_treeview(self.converted_tree, self.converted_df)

            # Update status
            row_count = len(self.original_df)
            filename = os.path.basename(file_path)
            offset_msg = f" (offset: {hour_offset:+d}h)" if hour_offset != 0 else ""
            self.status_var.set(f"Loaded: {filename} - {row_count} rows converted{offset_msg}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
            self.status_var.set("Error loading file")

    def download_csv(self):
        """Handle converted CSV download."""
        if self.converted_df is None:
            messagebox.showwarning("Warning", "No data to download. Please upload a CSV file first.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Converted CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            self.converted_df.to_csv(file_path, index=False, header=False)
            self.status_var.set(f"Saved: {os.path.basename(file_path)}")
            messagebox.showinfo("Success", f"File saved successfully:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")


def main():
    root = tk.Tk()
    app = TimestampConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
