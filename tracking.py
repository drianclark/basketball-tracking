from datetime import datetime
from fileinput import filename
from time import perf_counter
import cv2
import os
import ffmpeg

FOLDER = "to_process"

def convertToHHMMSS(seconds):
    hours = int(seconds // 3600)
    minutes =  int(seconds // 60)
    seconds = int(seconds % 60)
                
    padded_hours = str(hours).zfill(2)
    padded_minutes = str(minutes).zfill(2)
    padded_seconds = str(seconds).zfill(2)
            
    return f"{padded_hours}:{padded_minutes}:{padded_seconds}"

def frameToTimestamp(fps, frame_number):
    return frame_number/fps
    
def groupCloseValues(array, threshold):
    res = []
    current_group = [array[0]]
    for index in range(len(array)+1):
        try:
            if array[index+1]-array[index] <= threshold:
                current_group.append(array[index+1])
            else:
                res.append(current_group)
                current_group = [array[index+1]]
        except IndexError:
            res.append(current_group)   
            break
                    
    return res 

def getInOutTimestamps(array, threshold, predelay, release, source_duration):
    # group timestamps that are <= threshold apart, e.g for threshold=1:
    # [1,1.2,2,3,4,6,7,9] => [[1,1.2,2,3,4],[6,7],[9]]
    grouped_timestamps = groupCloseValues(array, threshold)
    
    # [[1,2,2,3], [7,8,8]] => [[1,3],[7,8]]
    in_out_timestamps = [[min(x), max(x)] for x in grouped_timestamps]
    
    # add predelay p (include p seconds before start) and release r (include r seconds after end) 
    # but ensure we don't go past the beginning (0s) and end (duration) of the video
    add_predelay_and_release = lambda in_out, predelay, release: [int(max(0, in_out[0]-predelay)), int(min(in_out[1]+release, source_duration))]
    in_out_timestamps_with_predelay_and_release = list(map(lambda x: add_predelay_and_release(x, predelay, release), in_out_timestamps))
    
    return in_out_timestamps_with_predelay_and_release

def getROI(filename):
    cap = cv2.VideoCapture(filename)
    TOTAL_FRAMES = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    median_frame = TOTAL_FRAMES // 2
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, median_frame)
    success, frame = cap.read()
    
    if success:
        x, y, w, h = cv2.selectROI("Select area around net", frame)
        cv2.destroyAllWindows()
    
    else:
        raise Exception("Error selecting ROI")
            
    return x, y, w, h

def saveTimeStampsToFile(outfile_prefix, time_stamps):
    outfile_suffix = datetime.now().strftime("%d%m%Y%H%M%S")
    outfile = f"{outfile_prefix}_{outfile_suffix}.txt"
    
    with open(outfile, 'w+') as f:
        for time_stamp in time_stamps:
            f.write(f"{time_stamp}\n")
            
def extractClips(folder, in_file, in_out_timestamps, fps):
    filename_without_extension = in_file.split(".")[0]
    
    if not os.path.exists(f"{folder}/{filename_without_extension}"):
        os.mkdir(f"{folder}/{filename_without_extension}")
    
    for (index, (in_time, out_time)) in enumerate(in_out_timestamps):
        print(f"Trimming clip {index + 1} of {len(in_out_timestamps)}")
        
        in_time_hours, in_time_minutes, in_time_seconds = list(map(int, in_time.split(":")))
        in_seconds = in_time_hours * 3600 + in_time_minutes * 60 + in_time_seconds
        
        out_time_hours, out_time_minutes, out_time_seconds = list(map(int, out_time.split(":")))
        out_seconds = out_time_hours * 3600 + out_time_minutes * 60 + out_time_seconds
        
        out_file = f"{folder}/{filename_without_extension}/{filename_without_extension}_{in_seconds}-{out_seconds}.mp4"
        
        if os.path.exists(out_file):
            os.remove(out_file)
            
        input_stream = ffmpeg.input(f"{folder}/{in_file}", ss=in_time, to=out_time)
        output = ffmpeg.output(input_stream, out_file, vcodec='copy', acodec='copy')
        output.run()

def process_video(folder, filename, roi):
    roi_x, roi_y, roi_w, roi_h = roi
    
    filename_without_extension = filename.split(".")[0]
    file_path = f"{folder}/{filename}"
    
    time_stamps = []

    cap = cv2.VideoCapture(file_path)
    FPS = cap.get(cv2.CAP_PROP_FPS)
    TOTAL_FRAMES = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    TOTAL_TIME_IN_SECONDS = frameToTimestamp(FPS, TOTAL_FRAMES)

    object_detector = cv2.createBackgroundSubtractorMOG2()

    frame_number = 0

    success, frame = cap.read()

    while True:
        frame_number += 1
        current_time = frameToTimestamp(FPS, frame_number)
        
        if (frame_number % FPS == 0):
            print(f"{convertToHHMMSS(current_time)} of {convertToHHMMSS(TOTAL_TIME_IN_SECONDS)}")
                    
        # Get next frame
        success, frame = cap.read()
        if not success:
            break
        
        # HACK FOR NOW: skip every other frame to (source video is 50fps, 25fps should be more than enough
        # to-do: figure out how to implement frame skipping to emulate a lower source video fps
        if frame_number % 2 == 0:
            continue
        
        # Extract region of interest
        roi = frame[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]
        mask = object_detector.apply(roi)
        
        _, mask = cv2.threshold(mask, 254, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        for c in contours:
            area = cv2.contourArea(c)
            
            if area > 100:
                cv2.drawContours(roi, [c], -1, (0, 255, 0), 2)
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(roi, (x, y), (x + w, y + h), (0, 255, 0), 2)
                print("Shot detected at", f"{convertToHHMMSS(current_time)}")
                time_stamps.append(current_time)

        cv2.namedWindow("ROI", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("ROI", roi_w * 2, roi_h * 2)
        cv2.imshow("ROI", roi)
        

        key = cv2.waitKey(30)
        if key == 27:
            break
        
    cap.release()
    cv2.destroyAllWindows()

    in_out_timestamps = getInOutTimestamps(time_stamps, 1, 4, 2, TOTAL_TIME_IN_SECONDS)
    hh_mm_ss_time_stamps = [list(map(convertToHHMMSS, t)) for t in in_out_timestamps]
    
    saveTimeStampsToFile(filename_without_extension, hh_mm_ss_time_stamps)
    extractClips(folder, filename, hh_mm_ss_time_stamps, FPS)
    
    os.rename(file_path, f"{folder}/{filename_without_extension}/{filename}")

    return hh_mm_ss_time_stamps

def main(folder):
    files = [item for item in os.listdir(folder) if item.lower().endswith(".mp4")]
        
    rois = dict()
        
    for file in files:
        roi_x, roi_y, roi_w, roi_h = getROI(f"{folder}/{file}")
        rois[file] = (roi_x, roi_y, roi_w, roi_h)
            
    for file in files:
        process_video(folder, file, rois[file])
    
if __name__ == "__main__":
    start = perf_counter()
    main(FOLDER)
    end = perf_counter()
    print(f"Elapsed time: {end-start}")
    