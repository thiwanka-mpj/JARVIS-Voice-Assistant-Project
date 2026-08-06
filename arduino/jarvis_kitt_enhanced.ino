/*
 * Enhanced Knight Rider KITT LED Controller for JARVIS
 * Features:
 * - KITT chaser effect for listening mode
 * - Sound-reactive center-out pattern for speaking
 * - PIR motion detection support
 * 
 * LED connections: Digital pins 2-9 (8 LEDs)
 * PIR sensor: Digital pin 10
 */

const int ledPins[] = {2, 3, 4, 5, 6, 7, 8, 9};
const int numLeds = 8;
const int pirPin = 10;

// Mode variables
int currentMode = 0; // 0=off, 1=listening (KITT chase), 2=talking (sound reactive)
int targetMode = 0;  // Target mode for smooth transitions
int audioLevel = 0;
int targetAudioLevel = 0;  // For smooth transitions
bool motionDetected = false;

// Mode transition smoothing
unsigned long lastModeChange = 0;
const int modeTransitionTime = 150; // ms for mode transitions

// KITT chaser variables
int chasePosition = 0;
int chaseDirection = 1;
unsigned long lastChaseUpdate = 0;
const int chaseDelay = 30; // Faster, smoother chase (optimized)
const int trailLength = 3; // Longer fade trail for smoothness
float chaseBrightness = 255.0; // For smooth brightness transitions

// Audio reactive variables
float currentLitLedsFloat = 0.0;  // For sub-LED precision and smooth transitions
int currentLitLeds = 0;
const float ledSmoothingFactor = 0.22;  // Optimized for smoothest transitions
unsigned long lastLedUpdate = 0;
const int ledUpdateInterval = 6;  // Faster updates for maximum responsiveness (ms)

// Brightness smoothing for LEDs
float ledBrightness[8] = {0, 0, 0, 0, 0, 0, 0, 0};
const float brightnessSmoothFactor = 0.3; // Smooth brightness changes

void setup() {
  Serial.begin(9600);
  pinMode(pirPin, INPUT);
  
  // Initialize all LED pins
  for (int i = 0; i < numLeds; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }
  
  // Startup animation - quick sweep
  startupAnimation();
}

void smoothSetLED(int ledIndex, int targetBrightness) {
  /*
   * Set LED with smooth brightness transition
   */
  if (ledIndex < 0 || ledIndex >= numLeds) return;
  
  // Smooth interpolation
  ledBrightness[ledIndex] += (targetBrightness - ledBrightness[ledIndex]) * brightnessSmoothFactor;
  
  // Apply brightness
  int finalBrightness = constrain((int)ledBrightness[ledIndex], 0, 255);
  
  if (finalBrightness == 0) {
    digitalWrite(ledPins[ledIndex], LOW);
  } else if (finalBrightness == 255) {
    digitalWrite(ledPins[ledIndex], HIGH);
  } else {
    analogWrite(ledPins[ledIndex], finalBrightness);
  }
}

void loop() {
  // Check for PIR motion detection
  checkMotion();
  
  // Check for serial commands from Raspberry Pi
  checkSerialCommands();
  
  // Smooth mode transition
  if (currentMode != targetMode) {
    unsigned long currentMillis = millis();
    if (currentMillis - lastModeChange > modeTransitionTime) {
      currentMode = targetMode;
      lastModeChange = currentMillis;
    }
  }
  
  // Execute current mode (non-blocking, controlled by internal timers)
  switch(currentMode) {
    case 0: // Off
      // Smooth fade out LEDs
      for (int i = 0; i < numLeds; i++) {
        smoothSetLED(i, 0);
      }
      break;
      
    case 1: // Listening - KITT chaser effect
      knightRiderChaseSmooth();
      break;
      
    case 2: // Talking - Sound reactive pattern
      audioReactivePatternSmooth();
      break;
  }
  
  // Minimal delay for stability
  delayMicroseconds(100);
}

void checkMotion() {
  int val = digitalRead(pirPin);
  if (val == HIGH && !motionDetected) {
    Serial.println("MOTION_DETECTED");
    motionDetected = true;
  } else if (val == LOW) {
    motionDetected = false;
  }
}

void checkSerialCommands() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input.startsWith("L")) {
      // Listening mode - KITT chaser
      targetMode = 1;
      audioLevel = 0;
      
    } else if (input.startsWith("T")) {
      // Talking mode - Sound reactive
      targetMode = 2;
      int colonIndex = input.indexOf(':');
      if (colonIndex > 0) {
        targetAudioLevel = input.substring(colonIndex + 1).toInt();
        targetAudioLevel = constrain(targetAudioLevel, 0, 8);
        // Smooth transition to target audio level
        audioLevel = targetAudioLevel;
      }
      
    } else if (input.startsWith("O")) {
      // Off mode
      targetMode = 0;
    }
  }
}

void knightRiderChaseSmooth() {
  /*
   * Enhanced KITT scanner with ultra-smooth brightness transitions
   * Uses smoothSetLED for fluid animation
   */
  unsigned long currentMillis = millis();
  
  if (currentMillis - lastChaseUpdate >= chaseDelay) {
    lastChaseUpdate = currentMillis;
    
    // Calculate target brightness for each LED
    int targetBrightness[8] = {0, 0, 0, 0, 0, 0, 0, 0};
    
    // Main bright LED
    targetBrightness[chasePosition] = 255;
    
    // Extended trailing fade effect
    for (int i = 1; i <= trailLength; i++) {
      int trailPos = chasePosition - (i * chaseDirection);
      if (trailPos >= 0 && trailPos < numLeds) {
        int brightness = 255 - (i * 65);  // Smoother gradient
        targetBrightness[trailPos] = constrain(brightness, 0, 255);
      }
    }
    
    // Leading fade effect
    for (int i = 1; i <= trailLength; i++) {
      int leadPos = chasePosition + (i * chaseDirection);
      if (leadPos >= 0 && leadPos < numLeds) {
        int brightness = 255 - (i * 65);  // Smoother gradient
        targetBrightness[leadPos] = constrain(brightness, 0, 255);
      }
    }
    
    // Apply smooth brightness transitions to all LEDs
    for (int i = 0; i < numLeds; i++) {
      smoothSetLED(i, targetBrightness[i]);
    }
    
    // Move position
    chasePosition += chaseDirection;
    
    // Bounce at ends with smooth reversal
    if (chasePosition >= numLeds - 1 || chasePosition <= 0) {
      chaseDirection *= -1;
      chasePosition = constrain(chasePosition, 0, numLeds - 1);
    }
  } else {
    // Continue smooth transitions even between position updates
    for (int i = 0; i < numLeds; i++) {
      smoothSetLED(i, (int)ledBrightness[i]);
    }
  }
}

void audioReactivePatternSmooth() {
  /*
   * Ultra-smooth sound-reactive pattern with continuous brightness interpolation
   * Uses smoothSetLED for fluid transitions
   */
  
  unsigned long currentMillis = millis();
  
  // Update LED state at controlled intervals
  if (currentMillis - lastLedUpdate >= ledUpdateInterval) {
    lastLedUpdate = currentMillis;
    
    // Smooth interpolation to target audio level using floating point
    float targetFloat = (float)audioLevel;
    currentLitLedsFloat += (targetFloat - currentLitLedsFloat) * ledSmoothingFactor;
    currentLitLeds = (int)currentLitLedsFloat;
    
    // Ensure within bounds
    currentLitLeds = constrain(currentLitLeds, 0, 8);
  }
  
  // Calculate target brightness for each LED
  int targetBrightness[8] = {0, 0, 0, 0, 0, 0, 0, 0};
  
  // Render based on intensity level
  if (currentLitLeds == 0) {
    // Silent - all LEDs off (target already 0)
  } 
  else if (currentLitLeds == 1) {
    // Very quiet - dim center pulse
    targetBrightness[3] = 80;
    targetBrightness[4] = 80;
  }
  else if (currentLitLeds == 2) {
    // Quiet - brighter center
    targetBrightness[3] = 180;
    targetBrightness[4] = 180;
  }
  else if (currentLitLeds >= 3) {
    // Normal to loud - expand outward
    // Center LEDs always brightest
    targetBrightness[3] = 255;
    targetBrightness[4] = 255;
    
    // Calculate how many pairs to light
    int pairsToLight = (currentLitLeds - 2) / 2;
    pairsToLight = constrain(pairsToLight, 0, 3);
    
    // Light pairs symmetrically with smooth brightness gradient
    for (int i = 1; i <= pairsToLight; i++) {
      // Exponential falloff for natural look
      float distanceFactor = 1.0 - ((float)i / 4.0);
      int brightness = (int)(255.0 * distanceFactor * distanceFactor);
      brightness = constrain(brightness, 60, 255);
      
      // Set target brightness for left and right
      int leftPos = 3 - i;
      int rightPos = 4 + i;
      
      if (leftPos >= 0) {
        targetBrightness[leftPos] = brightness;
      }
      if (rightPos < numLeds) {
        targetBrightness[rightPos] = brightness;
      }
    }
    
    // Handle partial lighting for ultra-smooth transitions
    float fractionalPart = currentLitLedsFloat - (float)currentLitLeds;
    if (fractionalPart > 0.1 && pairsToLight < 3) {
      int nextPair = pairsToLight + 1;
      int transitionBrightness = (int)(fractionalPart * 180.0);
      
      int leftPos = 3 - nextPair;
      int rightPos = 4 + nextPair;
      
      if (leftPos >= 0) {
        targetBrightness[leftPos] = max(targetBrightness[leftPos], transitionBrightness);
      }
      if (rightPos < numLeds) {
        targetBrightness[rightPos] = max(targetBrightness[rightPos], transitionBrightness);
      }
    }
  }
  
  // Apply smooth brightness transitions to all LEDs
  for (int i = 0; i < numLeds; i++) {
    smoothSetLED(i, targetBrightness[i]);
  }
}

void clearAllLeds() {
  for (int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], LOW);
  }
}

void startupAnimation() {
  /*
   * Quick startup animation - double sweep
   */
  // Sweep left to right
  for (int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], HIGH);
    delay(50);
    digitalWrite(ledPins[i], LOW);
  }
  
  // Sweep right to left
  for (int i = numLeds - 1; i >= 0; i--) {
    digitalWrite(ledPins[i], HIGH);
    delay(50);
    digitalWrite(ledPins[i], LOW);
  }
  
  // Center flash
  digitalWrite(ledPins[3], HIGH);
  digitalWrite(ledPins[4], HIGH);
  delay(200);
  digitalWrite(ledPins[3], LOW);
  digitalWrite(ledPins[4], LOW);
}
