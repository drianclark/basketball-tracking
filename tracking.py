from calendar import c
from datetime import datetime
import cv2
import os
import ffmpeg

VIDEO_FILE = "clip_trimmed_test.mp4"

def convertToMMSS(seconds):
    minutes =  int(seconds // 60)
    seconds = int(seconds % 60)
                
    padded_minutes = str(minutes).zfill(2)
    padded_seconds = str(seconds).zfill(2)
            
    return f"{padded_minutes}:{padded_seconds}"

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
    
    
    # add predelay p (include p seconds before start) and release r (include r seconds) after end 
    # but ensure we don't go past the beginning (0s) and end of the video (duration)
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
            
def trim_video(in_file, out_file, start, end, fps):
    if os.path.exists(out_file):
        os.remove(out_file)

    input_stream = ffmpeg.input(in_file)

    pts = "PTS-STARTPTS"
    video = input_stream.filter('fps', fps=fps, round='up').trim(start=start, end=end).setpts(pts)
    audio = (input_stream
            .filter_("atrim", start, end)
            .filter_("asetpts", pts))
    
    video_and_audio = ffmpeg.concat(video, audio, v=1, a=1)
    output = ffmpeg.output(video_and_audio, out_file)
    output.run()


def main(filename):
    roi_x, roi_y, roi_w, roi_h = getROI(filename)
    
    time_stamps = []

    cap = cv2.VideoCapture(filename)
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
            print(f"{convertToMMSS(current_time)} of {convertToMMSS(TOTAL_TIME_IN_SECONDS)}")
                    
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
                print("Shot detected at", f"{convertToMMSS(current_time)}")
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
    human_readable_time_stamps = [list(map(convertToMMSS, t)) for t in in_out_timestamps]
    
    saveTimeStampsToFile(filename.split(".")[0], human_readable_time_stamps)
    
    filename_without_extension = filename.split(".")[0]
    
    for (index, (in_time, out_time)) in enumerate(in_out_timestamps):
        print(f"Trimming clip {index + 1} of {len(in_out_timestamps)}")
        trim_video(filename, f"{filename_without_extension}_{in_time}-{out_time}.mp4", in_time, out_time, FPS)

    return(human_readable_time_stamps)

if __name__ == "__main__":
    main(VIDEO_FILE)