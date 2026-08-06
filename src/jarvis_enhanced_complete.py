#!/usr/bin/env python3
"""
J.A.R.V.I.S. Enhanced with Dual OLED Eyes & Motion Tracking
Features:
- PIR motion detection triggers face recognition
- Auto-trains on known_faces folder if no pkl file exists
- After authentication: camera remains active for future features
- Dual OLED displays (0x3C, 0x3D) with contextual eye animations
- KITT chaser lights for listening
- Sound-reactive lights for speaking
"""

import sys
import os
from dotenv import load_dotenv
import signal
import time
import subprocess
import wave
import numpy as np
from pathlib import Path
from datetime import datetime
import serial
import threading
from faster_whisper import WhisperModel
import openwakeword
from openwakeword.model import Model
import pickle
import hashlib
import queue

# Face Recognition imports
import face_recognition
import cv2
from picamera2 import Picamera2
from collections import defaultdict

# Groq API import
from groq import Groq

# GPIO for PIR sensor
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available - PIR sensor disabled")

# OLED Display imports
try:
    from board import SCL, SDA
    import busio
    from PIL import Image, ImageDraw
    import adafruit_ssd1306
    OLED_AVAILABLE = True
except:
    OLED_AVAILABLE = False
    print("⚠️  OLED libraries not available")

# ===== Configuration =====
PIPER_MODEL = "jarvis-medium.onnx"
WHISPER_MODEL_NAME = "tiny.en"

load_dotenv()
# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

TEMP_WAV = Path("/tmp/recording.wav")
TEMP_SPEECH_WAV = Path("/tmp/speech_output.wav")
ARDUINO_PORT = "/dev/ttyACM0"
ARDUINO_BAUD = 9600

# Audio Settings
WAKE_WORD_NAME = "hey_jarvis"
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280

# Face Recognition Settings
KNOWN_FACES_DIR = "known_faces"
FACE_ENCODINGS_CACHE = "face_encodings.pkl"
FACE_AUTH_TIMEOUT = 30
FACE_CONFIDENCE_THRESHOLD = 0.5

# PIR Sensor Settings
PIR_PIN = 17  # GPIO pin for PIR sensor (BCM)
PIR_ENABLED = True

# OLED Settings
OLED_LEFT_ADDR = 0x3C  # Left eye
OLED_RIGHT_ADDR = 0x3D  # Right eye
OLED_WIDTH = 128
OLED_HEIGHT = 64

# ===== Global Variables =====
current_user = None
arduino = None
pir_motion_detected = False
groq_client = None
conversation_history = []
camera_for_tracking = None
tracking_active = False

# OLED displays
oled_left = None
oled_right = None
i2c = None

# Eye animation state
current_eye_expression = "normal"
current_eye_direction = "center"
target_eye_direction = "center"
last_blink_time = 0
BLINK_INTERVAL = 3.0  # seconds between blinks
eye_position_x = 0  # Current eye position (-15 to 15)
eye_position_y = 0  # Current eye position (-10 to 10)
target_position_x = 0
target_position_y = 0
EYE_MOVEMENT_SPEED = 0.3  # Higher = faster (0.1 to 1.0)

# State management for smooth transitions
led_mode_queue = queue.Queue(maxsize=10)
eye_state_queue = queue.Queue(maxsize=10)
system_state = "initializing"  # initializing, waiting, authenticated, listening, processing, speaking
state_lock = threading.Lock()

# ===== OLED Eye Functions =====

def init_oled_displays():
    """Initialize dual OLED displays for eyes"""
    global oled_left, oled_right, i2c
    
    if not OLED_AVAILABLE:
        print("⚠️  OLED displays disabled (libraries not available)")
        return False
    
    try:
        i2c = busio.I2C(SCL, SDA)
        
        # Initialize left eye (0x3C)
        oled_left = adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_LEFT_ADDR)
        oled_left.fill(0)
        oled_left.show()
        
        # Initialize right eye (0x3D)
        oled_right = adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_RIGHT_ADDR)
        oled_right.fill(0)
        oled_right.show()
        
        print("✅ Dual OLED displays initialized (0x3C, 0x3D)")
        return True
    except Exception as e:
        print(f"⚠️  OLED initialization failed: {e}")
        return False

def draw_eye(display, expression="normal", direction="center"):
    """
    Draw eye on OLED display with smooth interpolated movement
    expression: normal, happy, angry, surprised, sleepy, thinking
    direction: center, left, right, up, down
    """
    global eye_position_x, eye_position_y, target_position_x, target_position_y, EYE_MOVEMENT_SPEED
    
    image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT))
    draw = ImageDraw.Draw(image)
    
    # Eye center position
    center_x = OLED_WIDTH // 2
    center_y = OLED_HEIGHT // 2
    
    # Set target position based on direction
    direction_map = {
        "center": (0, 0),
        "left": (-15, 0),
        "right": (15, 0),
        "up": (0, -10),
        "down": (0, 10),
        "up_left": (-12, -8),
        "up_right": (12, -8),
        "down_left": (-12, 8),
        "down_right": (12, 8)
    }
    target_position_x, target_position_y = direction_map.get(direction, (0, 0))
    
    # Smooth interpolation to target position
    eye_position_x += (target_position_x - eye_position_x) * EYE_MOVEMENT_SPEED
    eye_position_y += (target_position_y - eye_position_y) * EYE_MOVEMENT_SPEED
    
    # Round to integer for drawing
    eye_x = center_x + int(eye_position_x)
    eye_y = center_y + int(eye_position_y)
    
    # Draw based on expression
    if expression == "normal":
        # Large circular eye with smooth pupil
        draw.ellipse([eye_x-25, eye_y-20, eye_x+25, eye_y+20], outline=255, fill=0, width=2)
        # Pupil with highlight
        draw.ellipse([eye_x-10, eye_y-10, eye_x+10, eye_y+10], outline=255, fill=255)
        # Small highlight for depth
        draw.ellipse([eye_x-4, eye_y-6, eye_x-1, eye_y-3], outline=0, fill=0)
        
    elif expression == "happy":
        # Curved line (smile eye) with thickness
        draw.arc([eye_x-30, eye_y-15, eye_x+30, eye_y+25], 0, 180, fill=255, width=4)
        # Add small curves at ends for smoothness
        draw.arc([eye_x-32, eye_y-17, eye_x-28, eye_y-13], 0, 90, fill=255, width=2)
        draw.arc([eye_x+28, eye_y-17, eye_x+32, eye_y-13], 90, 180, fill=255, width=2)
        
    elif expression == "angry":
        # Narrowed eye with sharp angle
        draw.line([eye_x-28, eye_y-12, eye_x+28, eye_y+8], fill=255, width=4)
        draw.line([eye_x-28, eye_y+8, eye_x+28, eye_y-12], fill=255, width=4)
        # Add intensity with additional lines
        draw.line([eye_x-25, eye_y-8, eye_x+25, eye_y+4], fill=255, width=2)
        
    elif expression == "surprised":
        # Wide open circular eye with emphasis
        draw.ellipse([eye_x-32, eye_y-32, eye_x+32, eye_y+32], outline=255, width=3)
        draw.ellipse([eye_x-28, eye_y-28, eye_x+28, eye_y+28], outline=255, width=1)
        draw.ellipse([eye_x-16, eye_y-16, eye_x+16, eye_y+16], outline=255, fill=255)
        # Highlight
        draw.ellipse([eye_x-6, eye_y-10, eye_x-2, eye_y-6], outline=0, fill=0)
        
    elif expression == "sleepy":
        # Half-closed eye with droop
        draw.arc([eye_x-25, eye_y-5, eye_x+25, eye_y+35], 180, 360, fill=255, width=3)
        # Add eyelash effect
        for i in range(-20, 21, 8):
            draw.line([eye_x+i, eye_y+15, eye_x+i, eye_y+20], fill=255, width=1)
        
    elif expression == "thinking":
        # Slightly narrowed with offset pupil
        draw.ellipse([eye_x-22, eye_y-16, eye_x+22, eye_y+16], outline=255, fill=0, width=2)
        # Offset pupil (thinking look)
        draw.ellipse([eye_x-8+6, eye_y-8-2, eye_x+8+6, eye_y+8-2], outline=255, fill=255)
        # Highlight
        draw.ellipse([eye_x-2+6, eye_y-6-2, eye_x+1+6, eye_y-3-2], outline=0, fill=0)
    
    elif expression == "blink":
        # Horizontal line (closed eye) with thickness
        draw.line([eye_x-28, eye_y, eye_x+28, eye_y], fill=255, width=4)
        # Slight curve for natural look
        draw.arc([eye_x-30, eye_y-3, eye_x+30, eye_y+3], 180, 360, fill=255, width=2)
    
    display.image(image)
    display.show()

def update_eyes(expression="normal", direction="center"):
    """Update both eyes with same expression and direction (smooth transition)"""
    global oled_left, oled_right, current_eye_expression, current_eye_direction
    
    if oled_left and oled_right:
        current_eye_expression = expression
        current_eye_direction = direction
        draw_eye(oled_left, expression, direction)
        draw_eye(oled_right, expression, direction)

def blink_eyes():
    """Quick blink animation"""
    global oled_left, oled_right
    if oled_left and oled_right:
        draw_eye(oled_left, "blink", "center")
        draw_eye(oled_right, "blink", "center")
        time.sleep(0.1)
        draw_eye(oled_left, current_eye_expression, "center")
        draw_eye(oled_right, current_eye_expression, "center")

def eye_animation_thread():
    """Background thread for smooth eye animations, blinking, and micro-movements"""
    global last_blink_time, current_eye_direction, current_eye_expression
    
    BLINK_INTERVAL_VAR = 3.0
    micro_movement_timer = 0
    
    while True:
        current_time = time.time()
        
        # Random blinks
        if current_time - last_blink_time > BLINK_INTERVAL_VAR:
            blink_eyes()
            last_blink_time = current_time
            # Random interval for next blink (2-5 seconds)
            BLINK_INTERVAL_VAR = np.random.uniform(2.0, 5.0)
        
        # Micro-movements for lifelike behavior (subtle shifts every few seconds)
        micro_movement_timer += 0.1
        if micro_movement_timer > 4.0 and current_eye_direction == "center":
            # Subtle random movements
            if np.random.random() > 0.7:
                micro_directions = ["center", "up_left", "up_right", "left", "right"]
                micro_dir = np.random.choice(micro_directions)
                if oled_left and oled_right:
                    draw_eye(oled_left, current_eye_expression, micro_dir)
                    draw_eye(oled_right, current_eye_expression, micro_dir)
                time.sleep(0.3)
                # Return to center
                if oled_left and oled_right:
                    draw_eye(oled_left, current_eye_expression, "center")
                    draw_eye(oled_right, current_eye_expression, "center")
            micro_movement_timer = 0
        
        # Continuous smooth updates for interpolation
        if oled_left and oled_right:
            draw_eye(oled_left, current_eye_expression, current_eye_direction)
            draw_eye(oled_right, current_eye_expression, current_eye_direction)
        
        time.sleep(0.1)  # Faster updates for smoother animation

def contextual_eye_movement(text):
    """
    Analyze text and provide contextual eye expression
    Called when JARVIS speaks
    """
    text_lower = text.lower()
    
    # Detect emotions in response
    if any(word in text_lower for word in ["happy", "excellent", "wonderful", "delighted"]):
        update_eyes("happy", "center")
    elif any(word in text_lower for word in ["apologies", "sorry", "unfortunately", "cannot"]):
        update_eyes("sleepy", "center")
    elif any(word in text_lower for word in ["analyzing", "processing", "calculating", "thinking"]):
        update_eyes("thinking", "left")
    elif any(word in text_lower for word in ["alert", "warning", "critical", "urgent"]):
        update_eyes("surprised", "center")
    elif any(word in text_lower for word in ["error", "problem", "issue"]):
        update_eyes("angry", "center")
    else:
        update_eyes("normal", "center")
    
    # Return to normal after speaking
    threading.Timer(3.0, lambda: update_eyes("normal", "center")).start()

# ===== Servo Control Functions ===== [REMOVED]
# Servo motor functionality has been removed from this version

# ===== PIR Sensor Functions =====

def setup_pir_sensor():
    """Setup PIR motion sensor"""
    if not GPIO_AVAILABLE or not PIR_ENABLED:
        print("ℹ️  PIR sensor disabled")
        return False
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PIR_PIN, GPIO.IN)
        print(f"✅ PIR sensor configured on GPIO {PIR_PIN}")
        return True
    except Exception as e:
        print(f"⚠️  PIR sensor setup failed: {e}")
        return False

def wait_for_motion(timeout=60):
    """Wait for PIR motion detection"""
    if not GPIO_AVAILABLE or not PIR_ENABLED:
        return True
    
    print(f"🔍 Waiting for motion detection (timeout: {timeout}s)...")
    start_time = time.time()
    
    # Animate eyes looking around while waiting
    if oled_left and oled_right:
        update_eyes("normal", "left")
    
    while True:
        if GPIO.input(PIR_PIN):
            print("✅ Motion detected!")
            if oled_left and oled_right:
                update_eyes("surprised", "center")
            return True
        
        if time.time() - start_time > timeout:
            print("⏱️  Motion detection timeout")
            return False
        
        # Animate eyes looking around
        if oled_left and oled_right:
            if int(time.time() - start_time) % 4 == 0:
                update_eyes("normal", "left")
            elif int(time.time() - start_time) % 4 == 2:
                update_eyes("normal", "right")
        
        time.sleep(0.1)

def cleanup_gpio():
    """Cleanup GPIO on exit"""
    if GPIO_AVAILABLE:
        GPIO.cleanup()

# ===== Face Encodings Cache Functions =====

def get_directory_hash(directory):
    """Calculate hash of all image files in directory to detect changes"""
    hash_md5 = hashlib.md5()
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    
    for root, dirs, files in os.walk(directory):
        for filename in sorted(files):
            if os.path.splitext(filename)[1].lower() in image_extensions:
                filepath = os.path.join(root, filename)
                hash_md5.update(filepath.encode())
                hash_md5.update(str(os.path.getmtime(filepath)).encode())
    
    return hash_md5.hexdigest()

def save_face_encodings(known_encodings, known_names, person_encodings, directory_hash):
    """Save face encodings to cache file"""
    cache_data = {
        'known_encodings': known_encodings,
        'known_names': known_names,
        'person_encodings': dict(person_encodings),
        'directory_hash': directory_hash,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        with open(FACE_ENCODINGS_CACHE, 'wb') as f:
            pickle.dump(cache_data, f)
        print(f"💾 Face encodings saved to {FACE_ENCODINGS_CACHE}")
    except Exception as e:
        print(f"⚠️  Could not save cache: {e}")

def load_face_encodings_from_cache(directory_hash):
    """Load face encodings from cache if valid"""
    if not os.path.exists(FACE_ENCODINGS_CACHE):
        return None
    
    try:
        with open(FACE_ENCODINGS_CACHE, 'rb') as f:
            cache_data = pickle.load(f)
        
        if cache_data['directory_hash'] != directory_hash:
            print("ℹ️  Face images changed, cache invalid")
            return None
        
        print(f"✅ Loaded cached face encodings from {cache_data['timestamp']}")
        return (
            cache_data['known_encodings'],
            cache_data['known_names'],
            defaultdict(list, cache_data['person_encodings'])
        )
    except Exception as e:
        print(f"⚠️  Could not load cache: {e}")
        return None

# ===== Face Recognition Functions =====

def train_faces_from_directory():
    """Train face encodings from known_faces directory"""
    print("📸 Training face recognition model...")
    print()
    
    known_encodings = []
    known_names = []
    person_encodings = defaultdict(list)
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    person_images = defaultdict(list)
    
    # Scan directory structure
    for item in os.listdir(KNOWN_FACES_DIR):
        item_path = os.path.join(KNOWN_FACES_DIR, item)
        
        if os.path.isdir(item_path):
            person_name = item.replace('_', ' ').replace('-', ' ').title()
            for filename in os.listdir(item_path):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in image_extensions:
                    image_path = os.path.join(item_path, filename)
                    person_images[person_name].append(image_path)
    
    if not person_images:
        print(f"❌ No training images found in '{KNOWN_FACES_DIR}'!")
        print(f"   Please create folders with at least 10 images each")
        print(f"   Example: {KNOWN_FACES_DIR}/john_doe/image1.jpg")
        sys.exit(1)
    
    # Process each person
    total_encodings = 0
    
    for person_name, image_paths in sorted(person_images.items()):
        print(f"👤 {person_name}:")
        
        if len(image_paths) < 10:
            print(f"   ⚠️  Warning: Only {len(image_paths)} images (recommended: 10+)")
        
        encodings_for_person = []
        
        for idx, image_path in enumerate(image_paths, 1):
            try:
                filename = os.path.basename(image_path)
                print(f"   [{idx}/{len(image_paths)}] {filename}...", end=" ")
                
                image = face_recognition.load_image_file(image_path)
                face_encodings = face_recognition.face_encodings(image)
                
                if len(face_encodings) > 0:
                    encoding = face_encodings[0]
                    encodings_for_person.append(encoding)
                    known_encodings.append(encoding)
                    known_names.append(person_name)
                    total_encodings += 1
                    print("✅")
                else:
                    print("⚠️  No face")
            except Exception as e:
                print(f"❌ {str(e)}")
        
        if encodings_for_person:
            person_encodings[person_name] = encodings_for_person
            print(f"   ✓ Loaded {len(encodings_for_person)} images")
        print()
    
    return known_encodings, known_names, person_encodings

def load_known_faces():
    """Load authorized users from known_faces directory (with auto-training)"""
    print("🔐 Loading authorized user profiles...")
    
    if not os.path.exists(KNOWN_FACES_DIR):
        print(f"❌ Directory '{KNOWN_FACES_DIR}' not found!")
        os.makedirs(KNOWN_FACES_DIR)
        print(f"   Created directory. Add user face images:")
        print(f"   Structure: {KNOWN_FACES_DIR}/person_name/image1.jpg (10+ images per person)")
        sys.exit(1)
    
    # Calculate directory hash
    directory_hash = get_directory_hash(KNOWN_FACES_DIR)
    
    # Try to load from cache first
    cached_data = load_face_encodings_from_cache(directory_hash)
    
    if cached_data is not None:
        known_encodings, known_names, person_encodings = cached_data
    else:
        # No cache or cache invalid - train from images
        known_encodings, known_names, person_encodings = train_faces_from_directory()
        
        # Save new cache
        save_face_encodings(known_encodings, known_names, person_encodings, directory_hash)
    
    print()
    print("=" * 70)
    print(f"👥 Authorized Users: {len(person_encodings)}")
    for person, encodings in sorted(person_encodings.items()):
        print(f"   • {person} ({len(encodings)} images)")
    print("=" * 70)
    print()
    
    return known_encodings, known_names, person_encodings

def authenticate_user():
    """Authenticate user via face recognition"""
    global current_user
    
    print("\n" + "=" * 70)
    print("🔐 JARVIS FACE RECOGNITION AUTHENTICATION")
    print("=" * 70)
    
    # Animate eyes - looking for user
    if oled_left and oled_right:
        update_eyes("normal", "center")
    
    # Wait for PIR motion if enabled
    if PIR_ENABLED and GPIO_AVAILABLE:
        print("   Waiting for motion detection...")
        if not wait_for_motion(timeout=60):
            print("❌ No motion detected - authentication timeout")
            if oled_left and oled_right:
                update_eyes("sleepy", "center")
            return False
        print()
    
    print("   Please position yourself in front of the camera")
    print("   Scanning for authorized users...")
    print("=" * 70)
    print()
    
    # Eyes alert
    if oled_left and oled_right:
        update_eyes("surprised", "center")
    
    # Load known faces
    known_encodings, known_names, person_encodings = load_known_faces()
    
    # Initialize camera
    print("📷 Initializing camera...")
    try:
        camera = Picamera2()
        config = camera.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        camera.configure(config)
        camera.start()
        time.sleep(1.5)
        print("   ✅ Camera ready")
        print()
    except Exception as e:
        print(f"   ❌ Camera error: {e}")
        sys.exit(1)
    
    # Authentication loop
    start_time = time.time()
    recognized_users = defaultdict(int)
    frames_processed = 0
    
    print("🔍 Authentication in progress...")
    if oled_left and oled_right:
        update_eyes("thinking", "center")
    print()
    
    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed > FACE_AUTH_TIMEOUT:
                print(f"\n⏱️  Authentication timeout ({FACE_AUTH_TIMEOUT}s)")
                print("❌ AUTHENTICATION FAILED")
                if oled_left and oled_right:
                    update_eyes("angry", "center")
                camera.stop()
                cv2.destroyAllWindows()
                return False
            
            frame = camera.capture_array()
            frames_processed += 1
            
            if frames_processed % 3 == 0:
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                face_locations = face_recognition.face_locations(small_frame, model="hog")
                face_encodings = face_recognition.face_encodings(small_frame, face_locations)
                
                for face_encoding in face_encodings:
                    person_votes = defaultdict(list)
                    
                    for known_encoding, known_name in zip(known_encodings, known_names):
                        distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
                        
                        if distance < FACE_CONFIDENCE_THRESHOLD:
                            confidence = 1 - distance
                            person_votes[known_name].append(confidence)
                    
                    if person_votes:
                        best_person = max(person_votes.items(), key=lambda x: np.mean(x[1]))[0]
                        best_confidence = np.mean(person_votes[best_person])
                        
                        recognized_users[best_person] += 1
                        
                        if recognized_users[best_person] >= 2:
                            current_user = best_person
                            
                            print(f"\n✅ USER AUTHENTICATED: {best_person}")
                            print(f"   Confidence: {best_confidence*100:.1f}%")
                            print("=" * 70)
                            
                            if oled_left and oled_right:
                                update_eyes("happy", "center")
                            
                            # Keep camera for tracking
                            return camera
    
    except KeyboardInterrupt:
        print("\n❌ Authentication interrupted")
        camera.stop()
        cv2.destroyAllWindows()
        return False

def get_personalized_greeting():
    """Get personalized greeting for authenticated user"""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        time_greeting = "Good morning"
    elif 12 <= hour < 17:
        time_greeting = "Good afternoon"
    elif 17 <= hour < 21:
        time_greeting = "Good evening"
    else:
        time_greeting = "Good night"
    
    greetings = [
        f"{time_greeting}, {current_user}. Welcome back, sir. All systems online.",
        f"Hello {current_user}. {time_greeting}. JARVIS is ready to assist.",
        f"{time_greeting}, {current_user}. I am at your service, sir.",
        f"Welcome back, {current_user}. {time_greeting}. How may I help you today?",
    ]
    
    import random
    return random.choice(greetings)

# ===== Groq API Functions =====

def init_groq_client():
    """Initialize Groq API client"""
    global groq_client
    
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not set!")
        return False
    
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("✅ Groq API client initialized")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize Groq client: {e}")
        return False

def call_groq_api(user_message):
    """Call Groq API with conversation context"""
    global conversation_history, groq_client
    
    if not groq_client:
        return "I apologize, sir, but my connection to the knowledge base is not configured."
    
    system_prompt = f"You are Jarvis, the AI assistant from Iron Man. You are sophisticated, polite, and address {current_user} as 'sir'. Be helpful, concise (1-2 sentences unless asked for more detail), and maintain a professional British butler-like demeanor. You are witty but respectful."
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history[-10:])
    messages.append({"role": "user", "content": user_message})
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model=GROQ_MODEL,
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False
        )
        
        assistant_message = chat_completion.choices[0].message.content.strip()
        
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": assistant_message})
        
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        return assistant_message
        
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return "My apologies, sir. I seem to be experiencing technical difficulties."

# ===== Arduino & LED Functions =====

def init_arduino():
    """Initialize Arduino serial connection"""
    try:
        ard = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
        time.sleep(2)
        print("✅ Arduino connected")
        return ard
    except Exception as e:
        print(f"⚠️  Arduino not connected: {e}")
        return None

def set_led_mode(mode):
    """Send command to Arduino for LED mode with queue management"""
    global arduino
    
    # Add to queue for smooth transitions
    try:
        led_mode_queue.put_nowait(mode)
    except queue.Full:
        # If queue is full, clear old commands and add new one
        try:
            led_mode_queue.get_nowait()
        except queue.Empty:
            pass
        led_mode_queue.put_nowait(mode)
    
    if arduino:
        try:
            arduino.write(f"{mode}\n".encode())
            time.sleep(0.005)  # Small delay for serial stability
        except Exception as e:
            print(f"⚠️  Arduino communication error: {e}")

def led_state_manager_thread():
    """Background thread to manage LED state transitions smoothly"""
    global arduino
    current_mode = 'O'
    
    while True:
        try:
            # Check for new mode requests
            try:
                new_mode = led_mode_queue.get(timeout=0.1)
                if new_mode != current_mode:
                    current_mode = new_mode
            except queue.Empty:
                pass
            
            time.sleep(0.01)
        except Exception as e:
            print(f"⚠️  LED state manager error: {e}")
            time.sleep(0.1)

def audio_monitor_thread(stop_event, wav_file):
    """Thread to monitor audio and update LEDs with smooth intensity tracking for 8 LEDs"""
    global arduino
    try:
        wf = wave.open(str(wav_file), 'rb')
        frame_rate = wf.getframerate()
        chunk_size = int(frame_rate * 0.02)  # Smaller chunks for more responsive updates
        
        previous_level = 0
        smoothing_factor = 0.35  # Optimized smoothing
        
        # Pre-buffer for lookahead smoothing
        level_buffer = []
        buffer_size = 3
        
        # Calibration values for better LED response
        MIN_LEVEL = 0
        MAX_LEVEL = 8
        RMS_THRESHOLD_LOW = 200
        RMS_THRESHOLD_HIGH = 2000
        
        while not stop_event.is_set():
            frames = wf.readframes(chunk_size)
            if len(frames) == 0:
                break
                
            audio_data = np.frombuffer(frames, dtype=np.int16)
            if len(audio_data) > 0:
                # Calculate RMS (Root Mean Square) for intensity
                rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
                
                # Advanced normalization with dynamic range compression
                if rms < RMS_THRESHOLD_LOW:
                    normalized = MIN_LEVEL
                elif rms > RMS_THRESHOLD_HIGH:
                    normalized = MAX_LEVEL
                else:
                    normalized = ((rms - RMS_THRESHOLD_LOW) / 
                                (RMS_THRESHOLD_HIGH - RMS_THRESHOLD_LOW)) * MAX_LEVEL
                
                target_level = min(max(int(normalized), MIN_LEVEL), MAX_LEVEL)
                
                # Add to buffer for lookahead smoothing
                level_buffer.append(target_level)
                if len(level_buffer) > buffer_size:
                    level_buffer.pop(0)
                
                # Use average of buffer for smoother transitions
                if len(level_buffer) > 0:
                    buffered_level = sum(level_buffer) / len(level_buffer)
                else:
                    buffered_level = target_level
                
                # Smooth interpolation for natural transitions
                smoothed_level = previous_level * (1 - smoothing_factor) + buffered_level * smoothing_factor
                smoothed_level = min(max(int(smoothed_level), MIN_LEVEL), MAX_LEVEL)
                
                # Send to Arduino
                set_led_mode(f'T:{smoothed_level}')
                previous_level = smoothed_level
            
            time.sleep(0.012)  # Optimized update rate
        
        wf.close()
        
    except Exception as e:
        # Fallback: gentle pulsing pattern
        print(f"⚠️  Audio monitoring fallback mode: {e}")
        pulse = 2.0
        direction = 0.35
        while not stop_event.is_set():
            set_led_mode(f'T:{int(pulse)}')
            pulse += direction
            if pulse >= 7.0 or pulse <= 2.0:
                direction *= -1
            time.sleep(0.035)

def speak(text, silent_log=False):
    """Convert text to speech and play with LED sync + eye animations"""
    global arduino, system_state
    
    # Update system state
    with state_lock:
        system_state = "speaking"
    
    if not silent_log:
        print(f"🤖 Jarvis: {text}")
    
    # Update eyes based on context (with smooth transition)
    contextual_eye_movement(text)
    
    piper_cmd = [
        "piper",
        "--model", PIPER_MODEL,
        "--output_file", str(TEMP_SPEECH_WAV)
    ]
    
    try:
        # Generate speech
        p1 = subprocess.Popen(["echo", text], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(piper_cmd, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p2.wait()
        
        # Start audio monitoring thread
        stop_event = threading.Event()
        monitor = threading.Thread(target=audio_monitor_thread, args=(stop_event, TEMP_SPEECH_WAV), daemon=True)
        monitor.start()
        
        # Small delay for smooth LED transition start
        time.sleep(0.08)
        
        # Play audio
        aplay_cmd = ["aplay", str(TEMP_SPEECH_WAV)]
        subprocess.run(aplay_cmd, stderr=subprocess.DEVNULL)
        
        # Stop monitoring with smooth transition
        stop_event.set()
        monitor.join(timeout=0.5)
        
        # Smooth transition back to listening mode
        time.sleep(0.1)
        
        if TEMP_SPEECH_WAV.exists():
            TEMP_SPEECH_WAV.unlink()
            
    except Exception as e:
        print(f"❌ TTS Error: {e}")
    
    # Update system state
    with state_lock:
        system_state = "listening"
    
    # Smooth LED transition to listening mode
    set_led_mode('L')

def record_fixed_10s():
    """Record 10 seconds of audio with smooth state transitions"""
    global system_state
    
    print("🎤 Listening...")
    
    # Update system state
    with state_lock:
        system_state = "listening"
    
    # Smooth transition to listening mode
    set_led_mode('L')
    
    # Eyes listening
    if oled_left and oled_right:
        update_eyes("normal", "center")
    
    try:
        cmd = [
            "arecord", "-D", "default", "-f", "S16_LE", 
            "-r", str(SAMPLE_RATE), "-d", "10", str(TEMP_WAV)
        ]
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
        
        # Update state to processing
        with state_lock:
            system_state = "processing"
        
        return True
    except Exception as e:
        print(f"❌ Recording Error: {e}")
        return False

def handle_conversation(user_text, whisper):
    """Handle conversation with continuous follow-up loop"""
    try:
        response = call_groq_api(user_text)
        speak(response)
        
        print("\n⏳ Listening for follow-up (10 seconds)...")
        if record_fixed_10s():
            segments, _ = whisper.transcribe(str(TEMP_WAV))
            followup_text = " ".join(s.text for s in segments).strip()
            
            if followup_text:
                print(f"🗣️ You: {followup_text}")
                
                if any(phrase in followup_text.lower() for phrase in ["that's all", "thats all", "thank you jarvis", "thanks jarvis", "goodbye"]):
                    speak("Very good, sir. I'll be standing by.")
                else:
                    handle_conversation(followup_text, whisper)
            else:
                print("⏱️  No follow-up detected.")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        speak("My apologies, sir. I seem to be experiencing technical difficulties.")

def main():
    global arduino, current_user, camera_for_tracking, tracking_active
    
    print("\n" + "=" * 70)
    print("J.A.R.V.I.S. Enhanced - Motion Detection + Dual OLED Eyes")
    print("=" * 70)
    print()
    
    # Initialize systems
    if not init_groq_client():
        print("\n⚠️  WARNING: Groq API not initialized!")
    
    # Initialize OLED displays
    init_oled_displays()
    
    # Start eye animation thread
    if oled_left and oled_right:
        eye_thread = threading.Thread(target=eye_animation_thread, daemon=True)
        eye_thread.start()
    
    # Setup PIR sensor
    setup_pir_sensor()
    
    # Step 1: Face Recognition Authentication
    print("STEP 1: Face Recognition Authentication")
    print("-" * 70)
    
    authenticated_camera = authenticate_user()
    
    if not authenticated_camera:
        print("\n❌ Access Denied. Shutting down.")
        cleanup_gpio()
        sys.exit(1)
    
    # Keep camera for motion tracking
    camera_for_tracking = authenticated_camera
    
    # Step 2: Initialize Jarvis Systems
    print("\n" + "=" * 70)
    print("STEP 2: Initializing JARVIS Systems")
    print("=" * 70)
    print()
    
    arduino = init_arduino()
    set_led_mode('O')
    
    # Start LED state manager thread for smooth transitions
    led_manager = threading.Thread(target=led_state_manager_thread, daemon=True)
    led_manager.start()
    
    if not Path(PIPER_MODEL).exists():
        print(f"❌ Piper model {PIPER_MODEL} not found!")
        sys.exit(1)
    
    print("  Loading Whisper STT...")
    whisper = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
    
    print(f"  Loading Wake Word Model ('{WAKE_WORD_NAME}')...")
    try:
        oww_model = Model(wakeword_models=[WAKE_WORD_NAME], inference_framework="onnx")
    except Exception as e:
        print(f"⚠️  Could not load wake word model: {e}")
        sys.exit(1)
    
    print("✅ All systems loaded")
    print()
    
    # Step 3: Personalized Greeting
    print("=" * 70)
    print("STEP 3: JARVIS Activation")
    print("=" * 70)
    print()
    
    greeting = get_personalized_greeting()
    speak(greeting)
    speak("How may I assist you today? Simply say 'Hey Jarvis' to begin.")
    
    # Step 4: Wake Word Detection
    mic_cmd = [
        "arecord", "-D", "default", "-f", "S16_LE", "-r", str(SAMPLE_RATE), "-t", "raw", "-"
    ]
    mic_proc = subprocess.Popen(mic_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    print(f"\n👂 Listening for wake word 'Hey Jarvis'...")
    print(f"   Authenticated user: {current_user}")
    print(f"   Press Ctrl+C to shutdown")
    print()
    set_led_mode('L')
    
    if oled_left and oled_right:
        update_eyes("normal", "center")
    
    try:
        while True:
            audio_chunk = mic_proc.stdout.read(CHUNK_SIZE * 2)
            if not audio_chunk:
                break
            
            audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
            prediction = oww_model.predict(audio_data)
            score = list(prediction.values())[0]
            
            if score > 0.5:
                print(f"\n📊 Wake word detected! (Score: {score:.2f})")
                
                if oled_left and oled_right:
                    update_eyes("surprised", "center")
                
                mic_proc.terminate()
                mic_proc.wait()
                
                speak("Yes sir, I'm listening.", silent_log=True)
                
                if record_fixed_10s():
                    print("🧠 Processing...")
                    
                    if oled_left and oled_right:
                        update_eyes("thinking", "left")
                    
                    segments, _ = whisper.transcribe(str(TEMP_WAV))
                    user_text = " ".join(s.text for s in segments).strip()
                    
                    if user_text:
                        print(f"🗣️ {current_user}: {user_text}")
                        
                        if any(phrase in user_text.lower() for phrase in ["that's all", "thank you jarvis", "goodbye"]):
                            speak("Very good, sir. I'll be standing by.")
                        else:
                            handle_conversation(user_text, whisper)
                
                oww_model.reset()
                print(f"\n👂 Listening for 'Hey Jarvis'...")
                set_led_mode('L')
                
                if oled_left and oled_right:
                    update_eyes("normal", "center")
                
                mic_proc = subprocess.Popen(mic_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    except KeyboardInterrupt:
        print(f"\n\n👋 Goodbye, {current_user}. Shutting down JARVIS.")
        tracking_active = False
        set_led_mode('O')
        
        if oled_left and oled_right:
            update_eyes("sleepy", "center")
            time.sleep(1)
            oled_left.fill(0)
            oled_left.show()
            oled_right.fill(0)
            oled_right.show()
    
    finally:
        tracking_active = False
        mic_proc.terminate()
        if arduino:
            set_led_mode('O')
            arduino.close()
        if camera_for_tracking:
            camera_for_tracking.stop()
        cleanup_gpio()
        print("\n" + "=" * 70)
        print("JARVIS SHUTDOWN COMPLETE")
        print("=" * 70)

if __name__ == "__main__":
    main()
