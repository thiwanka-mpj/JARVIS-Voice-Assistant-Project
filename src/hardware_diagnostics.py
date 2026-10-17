"""
JARVIS Component Diagnostic Suite
Runs standalone tests for Audio Output (TTS), Microphone (STT), Camera (Face Rec), and Serial (Arduino).
"""

import sys
import time

def test_audio_output():
    print("\n[1/4] Testing Audio Output & Pygame...")
    try:
        import pygame
        pygame.mixer.init()
        print("  ✓ Pygame audio mixer initialized successfully.")
        return True
    except Exception as e:
        print(f"  ✗ Audio Initialization Failed: {e}")
        return False

def test_microphone():
    print("\n[2/4] Testing Microphone / Speech Recognition...")
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        mics = sr.Microphone.list_microphone_names()
        print(f"  ✓ SpeechRecognition loaded. Found {len(mics)} audio input device(s).")
        return True
    except Exception as e:
        print(f"  ✗ Microphone Check Failed: {e}")
        return False

def test_camera():
    print("\n[3/4] Testing Camera / OpenCV...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("  ⚠ Camera index 0 could not be opened. Check USB connection.")
            return False
        ret, frame = cap.read()
        cap.release()
        if ret:
            print("  ✓ Camera captured test frame successfully.")
            return True
        else:
            print("  ✗ Camera opened but failed to capture frame.")
            return False
    except Exception as e:
        print(f"  ✗ OpenCV Camera Test Failed: {e}")
        return False

def test_arduino_serial(port="/dev/ttyACM0", baudrate=115200):
    print(f"\n[4/4] Testing Serial Connection to Arduino ({port})...")
    try:
        import serial
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)
        ser.write(b"PING\n")
        print("  ✓ Serial port opened and command sent.")
        ser.close()
        return True
    except Exception as e:
        print(f"  ⚠ Serial Connection Skipped/Failed on {port}: {e}")
        print("    (Ignore if Arduino is not connected during dry test)")
        return False

if __name__ == "__main__":
    print("==================================================")
    print("       JARVIS HARDWARE DIAGNOSTIC SUITE          ")
    print("==================================================")
    
    t1 = test_audio_output()
    t2 = test_microphone()
    t3 = test_camera()
    t4 = test_arduino_serial()
    
    print("\n==================================================")
    print("SUMMARY:")
    print(f" Audio Output  : {'PASS' if t1 else 'FAIL'}")
    print(f" Microphone    : {'PASS' if t2 else 'FAIL'}")
    print(f" Camera        : {'PASS' if t3 else 'FAIL'}")
    print(f" Arduino Serial: {'PASS' if t4 else 'WARNING/CHECK'}")
    print("==================================================")
