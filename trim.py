import ffmpeg
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename

def trim(input_file, output_file, start, end):
    input_stream = ffmpeg.input(input_file, ss=start, to=end)
        
    output = ffmpeg.output(input_stream, output_file, vcodec='copy', acodec='copy')
    print(f"Extracting to {output_file} from {input_file}")
    output.run(quiet=True)

def main():
    Tk().withdraw()
    filename = askopenfilename(title="Choose video file to trim")
    print(f"Trimming {filename}")
    in_time = input("Trim start in mm:ss ")
    out_time = input("Trim end in mm:ss ")
    
    in_minutes, in_seconds = in_time.split(":")
    in_time_seconds = int(in_minutes) * 60 + int(in_seconds)
    
    out_minutes, out_seconds = out_time.split(":")
    out_time_seconds = int(out_minutes) * 60 + int(out_seconds)
    
    head, tail = os.path.split(filename)
    filename_without_extension = tail.split(".")[0]
    output_file = head + f"/{filename_without_extension}_{in_time_seconds}-{out_time_seconds}.mp4"
    
    trim(filename, output_file, in_time, out_time)
    
if __name__ == "__main__":
    main()