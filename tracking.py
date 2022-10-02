from datetime import datetime
import cv2

VIDEO_FILE = "trimmed.mp4"

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
            if array[index+1]-array[index] < threshold:
                current_group.append(array[index+1])
            else:
                res.append(current_group)
                current_group = []
        except IndexError:
            res.append(current_group)   
            
    return res 

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
    
def main(filename):
    roi_x, roi_y, roi_w, roi_h = getROI(filename)
    
    time_stamps = []

    cap = cv2.VideoCapture(filename)
    FPS = cap.get(cv2.CAP_PROP_FPS)
    TOTAL_FRAMES = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    TOTAL_TIME = frameToTimestamp(FPS, TOTAL_FRAMES)

    object_detector = cv2.createBackgroundSubtractorMOG2()

    frame_number = 0

    success, frame = cap.read()

    while True:
        frame_number += 1
        current_time = frameToTimestamp(FPS, frame_number)
        
        if (frame_number % FPS == 0):
            print(f"{convertToMMSS(current_time)} of {convertToMMSS(TOTAL_TIME)}")
                    
        # Get next frame
        success, frame = cap.read()
        if not success:
            break
        
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

    grouped_timestamps = groupCloseValues(time_stamps, 1)
    human_readable_time_stamps = [list(map(convertToMMSS, t)) for t in grouped_timestamps]
    
    saveTimeStampsToFile(filename.split(".")[0], human_readable_time_stamps)

    return(human_readable_time_stamps)

if __name__ == "__main__":
    main(VIDEO_FILE)