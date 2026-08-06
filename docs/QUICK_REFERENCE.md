# JARVIS Quick Reference Cheat Sheet

---

## 🗣️ Supported Voice Commands

| Voice Trigger / Command | Function / Action |
| :--- | :--- |
| **"JARVIS"** | Wake word to activate listening mode |
| **"What time is it?"** | Announces current system time |
| **"Who am I?"** | Triggers camera face scan and reports recognized identity |
| **"Status report"** | Checks system memory, CPU usage, and hardware connection |
| **"Mute / Silence"** | Halts current audio playback immediately |
| **"Goodnight / Exit"** | Shuts down the JARVIS application safely |

---

## 🤖 Arduino LED Matrix State Indicators

| LED Animation / Pattern | System State | Description |
| :--- | :--- | :--- |
| **KITT Scanner Bounce** | Standby / Idle | Waiting for wake word activation |
| **Pulsing Inner Circle** | Listening | Microphones active, processing user audio |
| **Rapid Matrix Flash** | Thinking / Processing | Running LLM / Local inference engine |
| **Equalizer Waveform** | Speaking | Text-to-Speech active and playing |
| **Checkmark / Smile** | Recognized | Face or command successfully validated |
| **Cross / Error Blink** | Unrecognized / Error | Invalid command or unknown face |

---

## 📌 Serial Protocol Commands (Host ➔ Arduino)

When sending serial messages over USB (Baud Rate: `115200`):
* `STATE:IDLE` - Set LED matrix to KITT scanner mode
* `STATE:LISTEN` - Set LED matrix to listening pulses
* `STATE:THINK` - Set LED matrix to processing animation
* `STATE:SPEAK` - Set LED matrix to equalizer audio visualizer
