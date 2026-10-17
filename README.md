# JARVIS Voice Assistant & HCI System

A multi-modal, hardware-integrated AI voice assistant featuring real-time speech-to-text, fast neural text-to-speech, local face recognition, and interactive Arduino LED matrix visual feedback.

---

## 🛠 Project Structure

```text
jarvis-voice-assistant/
├── README.md                   # Main project overview & quick setup
├── LICENSE                     # MIT License
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
│
├── src/                        # Python application source code
│   ├── jarvis_enhanced_complete.py  # Main entry script
│   └── hardware_diagnostics.py           # Diagnostic suite for hardware & software
│
├── arduino/                    # Embedded controller code
│   └── jarvis_kitt_enhanced/
│       └── jarvis_kitt_enhanced.ino # Arduino LED controller firmware
│
├── docs/                       # Comprehensive documentation
│   ├── SETUP_GUIDE.md          # Hardware assembly & installation guide
│   └── QUICK_REFERENCE.md      # Command cheatsheet & pin references
│
├── models/                     # Storage directory for TTS models
│   └── README.md               # Model download instructions
│
└── known_faces/                # Face recognition training images
    └── .gitkeep                # Git tracking placeholder
```

---

##  Downloading the Voice Model (`jarvis-medium.onnx`)

Due to GitHub repository size limits and performance best practices, large binary machine learning models are **not** committed to the repository directly.

### Automatic Download
Run the provided setup script or execute the following commands in your terminal:

```bash
# Navigate to the root directory of the project
cd jarvis-voice-assistant

# Create models directory if it doesn't exist
mkdir -p models

# Download the Piper ONNX voice model and configuration
# (Replace the URLs below with your specific hosting link or Piper HuggingFace URL)
wget -O models/jarvis-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx"
wget -O models/jarvis-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json"
```

### Manual Download
1. Download `jarvis-medium.onnx` and `jarvis-medium.onnx.json`.
2. Place both files directly into the `models/` directory or the root directory of your project (matching your configured path in `jarvis_enhanced_complete.py`).

---

## 🚀 Quick Start Guide

### 1. Hardware Connections
* **Arduino:** Connect via USB (defaults to `/dev/ttyACM0` or `COM3`).
* **Microphone & Speaker:** Connect via USB / 3.5mm Audio Jack.
* **Camera:** Connect USB Web Camera.

### 2. Software Setup
```bash
# Clone the repository
git clone https://github.com/thiwanka-mpj/JARVIS-Voice-Assistant-Project.git
cd jarvis-voice-assistant

# Create and activate a Python virtual environment
python3 -m venv jarvis_env
source jarvis_env/bin/activate  # On Windows: jarvis_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download voice model (see instructions above)

# Run component diagnostics to verify hardware
python3 src/hardware_diagnostics.py

# Launch JARVIS
python3 src/jarvis_enhanced_complete.py
```

---

## 📄 Documentation
* See [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md) for full step-by-step hardware wiring, driver setup, and troubleshooting.
* See [`docs/QUICK_REFERENCE.md`](docs/QUICK_REFERENCE.md) for voice commands, pinouts, and LED state mappings.

---

## 👥 Collaboration & Credits
This project was co-developed and engineered in a shared local environment by myself and **[@Thisaru-Sach](https://github.com/Thisaru-Sach)**. 
This repository serves as my personal portfolio host to demonstrate my architectural contributions to the voice assistant system.

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
