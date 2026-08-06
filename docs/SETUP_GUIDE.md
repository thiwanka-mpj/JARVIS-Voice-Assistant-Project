# JARVIS Complete Hardware & Software Setup Guide

This guide details the complete process of building, wiring, and configuring the JARVIS Voice Assistant.

---

## 1. Hardware Requirements

| Hardware Component | Description / Recommended Spec |
| :--- | :--- |
| **Host Computer** | Raspberry Pi 4 / Pi 5 or x86 PC (Linux/Windows/macOS) |
| **Micro-controller** | Arduino Uno / Nano / Mega |
| **Visual Display** | 8x8 MAX7219 LED Matrix / WS2812B NeoPixel Strip |
| **Microphone** | USB Condenser Microphone or Conference Mic |
| **Speaker** | Powered 3.5mm AUX or USB Speaker |
| **Camera** | USB Web Camera (720p or 1080p) |

---

## 2. Hardware Wiring & Pinout

### Arduino to MAX7219 LED Matrix (SPI Pinout)
* **VCC** ➔ Arduino 5V
* **GND** ➔ Arduino GND
* **DIN (Data In)** ➔ Arduino Pin 11 (MOSI)
* **CS (Chip Select)** ➔ Arduino Pin 10
* **CLK (Clock)** ➔ Arduino Pin 13 (SCK)

---

## 3. Environment & Dependency Setup

1. **Install System Packages (Ubuntu/Debian/Raspberry Pi OS):**
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv portaudio19-dev libatlas-base-dev ffmpeg
   ```

2. **Clone Project and Setup Virtual Environment:**
   ```bash
   git clone https://github.com/your-username/jarvis-voice-assistant.git
   cd jarvis-voice-assistant
   python3 -m venv jarvis_env
   source jarvis_env/bin/activate
   ```

3. **Install Python Packages:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 4. Downloading Voice Models

Download the neural TTS Piper model into the `models/` directory:

```bash
mkdir -p models
wget -O models/jarvis-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx"
wget -O models/jarvis-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json"
```

---

## 5. Adding Known Faces for Recognition

1. Place image files (`.jpg` or `.png`) of authorized users inside the `known_faces/` folder.
2. File naming convention: `FirstName_LastName.jpg` (e.g., `Tony_Stark.jpg`).
3. JARVIS will automatically scan and generate facial encodings on startup.

---

## 6. Running Diagnostic Test

Verify all components are working correctly:
```bash
python src/test_components.py
```
