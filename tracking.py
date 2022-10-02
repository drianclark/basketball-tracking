import cv2
import os 

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
    current_group = []
    for index, element in enumerate(array):
        if array(index+1)-element < threshold:
            current_group.append(array(index+1))
        else:
            res.append(current_group)
            current_group = []
            
time_stamps = []

cap = cv2.VideoCapture("clip.mp4")
FPS = cap.get(cv2.CAP_PROP_FPS)
TOTAL_FRAMES = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
TOTAL_TIME = frameToTimestamp(FPS, TOTAL_FRAMES)

object_detector = cv2.createBackgroundSubtractorMOG2()

frame_number = 0

success, frame = cap.read()
frame_height, frame_width, _ = frame.shape
roi = frame[285:335, 1392:1460]

while success:
    frame_number += 1
    current_time = frameToTimestamp(FPS, frame_number)
    
    if (frame_number % FPS == 0):
        print(f"{convertToMMSS(current_time)} of {convertToMMSS(TOTAL_TIME)}")
        
    success, frame = cap.read()
    mask = object_detector.apply(roi)
    _, mask = cv2.threshold(mask, 254, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    for c in contours:
        area = cv2.contourArea(c)
        
        if area > 100:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(roi, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            if x >= 0 and x + w <= frame_width:
                if y >= 0 and (y + h) <= frame_height:
                    time_stamps.append(current_time)
                    

    key = cv2.waitKey(30)
    if key == 27:
        break
    
cap.release()
cv2.destroyAllWindows()

human_readable_time_stamps = list(map(convertToMMSS, time_stamps))

print(human_readable_time_stamps)