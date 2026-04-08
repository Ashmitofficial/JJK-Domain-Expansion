from flask import Flask, render_template, Response, jsonify
import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf

app = Flask(__name__)

# 1. Load the "Brain" and the Labels
model = tf.keras.models.load_model('domain_model.h5')
classes = np.load('classes.npy', allow_pickle=True)

# 2. Setup MediaPipe (2-hand support)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.8)

# Lazy initialization to prevent camera lock when Flask's reloader restarts the app
camera = None
current_status = "SCANNING"

def gen_frames():
    global current_status, camera
    if camera is None:
        camera = cv2.VideoCapture(0)
        
    while True:
        success, frame = camera.read()
        if not success: 
            break
        
        frame = cv2.flip(frame, 1)
        results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        all_landmarks = [0] * 126 
        if results.multi_hand_landmarks:
            for i, hand_lms in enumerate(results.multi_hand_landmarks):
                if i < 2:
                    start_idx = i * 63
                    
                    # Get the wrist coordinates to act as the origin (0,0,0) for this hand
                    wrist_x = hand_lms.landmark[0].x
                    wrist_y = hand_lms.landmark[0].y
                    wrist_z = hand_lms.landmark[0].z
                    
                    for j, lm in enumerate(hand_lms.landmark):
                        all_landmarks[start_idx + (j * 3)] = lm.x - wrist_x
                        all_landmarks[start_idx + (j * 3) + 1] = lm.y - wrist_y
                        all_landmarks[start_idx + (j * 3) + 2] = lm.z - wrist_z

            # 3. AI PREDICTION
            # Replaced model.predict() with model() to fix massive TF memory leak inside real-time loops
            input_data = np.array([all_landmarks], dtype=np.float32)
            prediction = model(input_data, training=False)
            class_idx = np.argmax(prediction.numpy()[0])
            confidence = prediction.numpy()[0][class_idx]

            # Only trigger if the AI is more than 95% sure
            if confidence > 0.95:
                # Convert numbers back to 'gojo' or 'sukuna'
                detected_label = str(classes[class_idx]).lower()
                current_status = detected_label
            else:
                current_status = "SCANNING"
        else:
            current_status = "SCANNING"

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index(): return render_template('index.html')

@app.route('/video_feed')
def video_feed(): return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_status')
def get_status(): return jsonify(status=current_status)

if __name__ == '__main__':
    # Disable thread to prevent concurrent camera reads, keeping it robust for single sessions.
    app.run(debug=True, use_reloader=False)
