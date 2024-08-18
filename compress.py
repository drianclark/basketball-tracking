import os
import ffmpeg
import tkinter as tk
from tkinter import filedialog, messagebox

def compress_video(input_file, crf_value=28, codec="libx265"):
    # Get the file name without the extension
    file_name, _ = os.path.splitext(input_file)
    output_file = f"{file_name}_compressed.mp4"

    # Run the ffmpeg command using the ffmpeg-python library
    try:
        (
            ffmpeg
            .input(input_file)
            .output(output_file, vcodec=codec, crf=crf_value)
            .run()
        )
        messagebox.showinfo("Success", f"Compression complete.\nOutput file: {output_file}")
    except ffmpeg.Error as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        sys.exit(1)

def main():
    # Create a Tkinter root window (hidden)
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Ask the user to select a video file
    input_file = filedialog.askopenfilename(
        title="Select a video file",
        filetypes=[("MP4 files", "*.mp4;*.MP4")]
    )

    if not input_file:
        messagebox.showwarning("No file selected", "You didn't select a file.")
        return

    # Create a new top-level window for CRF and Instagram options
    top = tk.Toplevel(root)
    top.title("Compression Options")

    # Create and place the CRF value label and entry
    crf_label = tk.Label(top, text="Enter the CRF value (default is 28):")
    crf_label.pack(pady=5)

    crf_entry = tk.Entry(top)
    crf_entry.insert(0, "28")  # Default value is 28
    crf_entry.pack(pady=5)

    # Create a boolean variable to store the checkbox state
    instagram_var = tk.BooleanVar()

    # Create and place the checkbox
    instagram_checkbox = tk.Checkbutton(
        top, 
        text="Compress for Instagram?", 
        variable=instagram_var
    )
    instagram_checkbox.pack(pady=10)

    # Add a button to confirm selection
    def on_confirm():
        try:
            crf_value = int(crf_entry.get())
            codec = "libx264" if instagram_var.get() else "libx265"
            top.destroy()
            compress_video(input_file, crf_value, codec)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid integer for the CRF value.")

    confirm_button = tk.Button(top, text="Confirm", command=on_confirm)
    confirm_button.pack(pady=10)

    top.mainloop()

if __name__ == "__main__":
    main()
