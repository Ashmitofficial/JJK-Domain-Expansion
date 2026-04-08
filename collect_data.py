import cv2
import mediapipe as mp
import csv
import time

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
DATA_FILE = 'domain_landmarks.csv'

recording = False
record_label = ""
samples_captured = 0
MAX_SAMPLES = 400 # How many frames to record per session

print("Press 'g', 's', or 'n' to start a 3-second countdown for recording.")

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    frame = cv2.flip(frame, 1)
    results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    all_landmarks = [0] * 126 

    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            if i < 2:
                mp_draw.draw_landmarks(frame, hand_lms, mp_hands.HAND_CONNECTIONS)
                start_idx = i * 63
                
                # Get the wrist coordinates to act as the origin (0,0,0) for this hand
                wrist_x = hand_lms.landmark[0].x
                wrist_y = hand_lms.landmark[0].y
                wrist_z = hand_lms.landmark[0].z
                
                for j, lm in enumerate(hand_lms.landmark):
                    all_landmarks[start_idx + (j * 3)] = lm.x - wrist_x
                    all_landmarks[start_idx + (j * 3) + 1] = lm.y - wrist_y
                    all_landmarks[start_idx + (j * 3) + 2] = lm.z - wrist_z

    # --- TIMER & RECORDING LOGIC ---
    if recording:
        samples_captured += 1
        with open(DATA_FILE, 'a', newline='') as f:
            csv.writer(f).writerow(all_landmarks + [record_label])
        
        cv2.putText(frame, f"RECORDING {record_label.upper()}: {samples_captured}/{MAX_SAMPLES}", 
                    (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        if samples_captured >= MAX_SAMPLES:
            recording = False
            print(f"Finished recording {record_label}!")

    cv2.imshow("Data Collection", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if not recording and key in [ord('g'), ord('s'), ord('n')]:
        record_label = "gojo" if key == ord('g') else "sukuna" if key == ord('s') else "none"
        
        # 3-Second Countdown
        for i in range(3, 0, -1):
            print(f"Starting in {i}...")
            time.sleep(1) 
        
        recording = True
        samples_captured = 0

    if key == ord('q'): break

cap.release()
cv2.destroyAllWindows()