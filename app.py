from flask import Flask, render_template, Response, jsonify
import cv2
import mediapipe as mp

app = Flask(__name__)

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.8, min_tracking_confidence=0.8)

camera = cv2.VideoCapture(0)
current_status = "SCANNING"

def gen_frames():
    global current_status
    while True:
        success, frame = camera.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        # LOCAL STATUS RESET
        temp_status = "SCANNING"

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                # Gojo Logic: Middle (12) higher than Index (8)
                if hand_lms.landmark[12].y < hand_lms.landmark[8].y - 0.05:
                    temp_status = "UNLIMITED_VOID"
                # Sukuna Logic: Index (8) curled lower than knuckle (6)
                elif hand_lms.landmark[8].y > hand_lms.landmark[6].y:
                    temp_status = "MALEVOLENT_SHRINE"
        
        current_status = temp_status

        # Encode frame for browser
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_status')
def get_status():
    return jsonify(status=current_status)

if __name__ == '__main__':
    app.run(debug=True)