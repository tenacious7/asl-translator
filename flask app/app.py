from flask import Flask, render_template, Response, jsonify
import cv2
import numpy as np
import mediapipe as mp
import pyttsx3
from spellchecker import SpellChecker
from tensorflow.keras.models import load_model
import pickle
from flask_socketio import SocketIO, emit
from word_prediction import WordPredictor, ASLWordSuggester, SentenceGenerator
from time import time
from sentence_generator import HuggingFaceSentenceGenerator

# Load the saved model and label encoder
model = load_model('hope.keras')
with open('label_encoder.pkl', 'rb') as f:
    label_encoder = pickle.load(f)

# Initialize MediaPipe Hands and Text-to-Speech
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# Initialize text-to-speech engine and spell checker
engine = pyttsx3.init()
spell = SpellChecker()

# Initialize Flask app with SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Initialize variables
current_gesture = ""
current_word = ""
current_sentence = ""
recent_predictions = []
processing_active = False
hand_in_region = False

# Define ROI
roi_x = 100
roi_y = 100
roi_width = 400
roi_height = 400

# Add these global variables
fps_count = 0
model_status = "Loading..."

# Add a global variable for camera selection
current_camera = 0  # 0 for front camera, 1 for back camera

# Initialize WordPredictor
word_predictor = WordPredictor()

# Initialize ASL Word Suggester
word_suggester = ASLWordSuggester('asl_words.json')

# Add to global variables
current_gesture_time = None

# Initialize Sentence Generator
sentence_generator = SentenceGenerator()

# Initialize sentence generator
sentence_generator = HuggingFaceSentenceGenerator()

def process_landmarks(hand_landmarks):
    """Process hand landmarks for prediction."""
    try:
        landmarks = []
        for landmark in hand_landmarks.landmark:
            landmarks.append([landmark.x, landmark.y, landmark.z])
        return np.array(landmarks).reshape(1, 21, 3)
    except Exception as e:
        print(f"Error processing landmarks: {e}")
    return None

def check_hand_in_region(hand_landmarks, frame_width, frame_height):
    """Check if hand is in the defined region."""
    for landmark in hand_landmarks.landmark:
        x, y = int(landmark.x * frame_width), int(landmark.y * frame_height)
        if not (roi_x < x < roi_x + roi_width and roi_y < y < roi_y + roi_height):
            return False
    return True

def generate_frames():
    """Capture frames from the webcam and process them for gesture recognition."""
    global current_camera, current_gesture_time
    cap = cv2.VideoCapture(current_camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    global current_gesture, current_word, current_sentence, recent_predictions, processing_active, hand_in_region, fps_count

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Only flip if using front camera
            if current_camera == 0:
                frame = cv2.flip(frame, 1)
            
            # Get the frame dimensions
            height, width = frame.shape[:2]
            
            # Calculate ROI coordinates to center it
            roi_x = (width - roi_width) // 2
            roi_y = (height - roi_height) // 2
            
            # Draw ROI rectangle
            cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_width, roi_y + roi_height), (0, 255, 0), 2)
            
            if processing_active:
                # Extract ROI for processing
                roi_frame = frame[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width]
                
                # Process only the ROI
                rgb_frame = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb_frame)

                if results.multi_hand_landmarks:
                    # Adjust landmark coordinates to ROI space
                    hand_landmarks = results.multi_hand_landmarks[0]
                    for landmark in hand_landmarks.landmark:
                        # Convert coordinates from ROI space to full frame space
                        landmark.x = (landmark.x * roi_width + roi_x) / width
                        landmark.y = (landmark.y * roi_height + roi_y) / height
                    
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    landmarks = process_landmarks(hand_landmarks)

                    if landmarks is not None:
                        predictions = model.predict(landmarks, verbose=0)
                        predicted_class = np.argmax(predictions, axis=1)
                        predicted_label = label_encoder.inverse_transform(predicted_class)[0]
                        confidence = float(np.max(predictions))
                        
                        # Update gesture buffer and get suggestions
                        current_time = time()
                        suggestions = word_suggester.add_gesture(predicted_label, current_time, hand_in_region)
                        
                        # Emit prediction and suggestions via Socket.IO
                        socketio.emit('prediction', {
                            'gesture': predicted_label,
                            'gesture_sequence': word_suggester.get_current_sequence(),
                            'confidence': confidence * 100,
                            'suggestions': suggestions,
                            'waiting_for_hand': word_suggester.hand_out_required
                        })

            # Add overlay text to show processing status
            status_text = "Processing Active" if processing_active else "Click Start to Begin"
            cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Add ROI guide text
            guide_text = "Keep hand in green box"
            cv2.putText(frame, guide_text, (roi_x, roi_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    except Exception as e:
        print(f"Error in generate_frames: {e}")
    finally:
        cap.release()

def get_word_suggestions(current_input):
    """Get word suggestions based on current input"""
    if not current_input:
        return []
    return word_suggester.get_suggestions(current_input)

@app.route('/')
def index():
    # Set initial processing state to False
    global processing_active
    processing_active = False
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('connect')
def handle_connect():
    emit('status', {'message': 'Connected', 'status': True})

@socketio.on('start')
def handle_start():
    """Handle start button click."""
    global processing_active
    processing_active = True
    emit('status', {'message': 'Processing Started', 'status': True})
    # Update button text
    emit('update_button', {'text': 'Stop'})

@socketio.on('stop')
def handle_stop():
    """Handle stop button click."""
    global processing_active
    processing_active = False
    emit('status', {'message': 'Processing Stopped', 'status': False})
    # Update button text
    emit('update_button', {'text': 'Start'})

@socketio.on('clear')
def handle_clear():
    global current_gesture, current_word, current_sentence, recent_predictions
    current_gesture = ""
    current_word = ""
    current_sentence = ""
    recent_predictions.clear()
    emit('cleared')

@socketio.on('generate_sentence')
def handle_generate_sentence(data):
    """Handle sentence generation with Hugging Face API"""
    try:
        collected_words = data.get('words', [])
        if not collected_words:
            emit('sentence', {'sentence': '', 'error': 'No words collected'})
            return
            
        # Generate sentence using Hugging Face API
        generated_sentence = sentence_generator.generate_sentence(collected_words)
        
        emit('sentence', {
            'sentence': generated_sentence,
            'success': True
        })
        
    except Exception as e:
        print(f"Error generating sentence: {e}")
        emit('sentence', {
            'sentence': ' '.join(collected_words).capitalize() + '.',
            'error': 'Using basic sentence generation'
        })

@socketio.on('read')
def handle_read():
    """Read the current sentence"""
    global current_sentence
    if current_sentence:
        engine.say(current_sentence)
        engine.runAndWait()
        emit('reading_complete')

@socketio.on('next_suggestion')
def handle_next_suggestion():
    """Handle request for next word suggestion"""
    suggestion = word_suggester.get_next_suggestion()
    emit('suggestion', {'word': suggestion})

@socketio.on('previous_suggestion')
def handle_previous_suggestion():
    """Handle request for previous word suggestion"""
    suggestion = word_suggester.get_previous_suggestion()
    emit('suggestion', {'word': suggestion})

@socketio.on('switch_camera')
def handle_switch_camera():
    """Handle camera switch button click."""
    global current_camera
    current_camera = 1 if current_camera == 0 else 0
    emit('camera_switched', {'camera_id': current_camera})

@socketio.on('select_word')
def handle_select_word(data):
    """Handle word selection and clear gesture buffer"""
    word = data.get('word')
    if word:
        word_suggester.clear_gesture_buffer()
        emit('gesture_buffer_cleared')

@socketio.on('clear_suggestions')
def handle_clear_suggestions():
    """Handle clearing suggestions and gesture sequence"""
    global current_gesture
    current_gesture = ""
    word_suggester.clear_gesture_buffer()
    emit('suggestions_cleared')

@socketio.on('clear_all')
def handle_clear_all():
    """Handle clearing everything"""
    global current_gesture, current_word, current_sentence, recent_predictions
    current_gesture = ""
    current_word = ""
    current_sentence = ""
    recent_predictions.clear()
    word_suggester.clear_gesture_buffer()
    emit('all_cleared')

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
