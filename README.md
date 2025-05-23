# ASL Prediction App

![ASL Prediction Banner](https://github.com/username/asl-prediction/raw/main/static/banner.png)

## Overview

ASL Prediction App is a real-time American Sign Language translator that converts hand gestures into text and sentences. Using computer vision and machine learning, the app recognizes ASL gestures through your webcam and provides word suggestions and sentence generation.

## Features

- ✅ **Real-time ASL Recognition**: Detects hand gestures in real-time
- ✅ **Word Suggestions**: Suggests possible words based on gesture sequences
- ✅ **Sentence Generation**: Creates natural sentences from detected words
- ✅ **Text-to-Speech**: Reads generated sentences aloud
- ✅ **User-friendly Interface**: Clear visual feedback with gesture region
- ✅ **Camera Controls**: Switch between front and back cameras
- ✅ **Spell Checking**: Corrects potential errors in detected words

## Demo

[Watch the demo video](https://youtube.com/shorts/QK3Et0U-6zo)

## Technologies Used

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Flask, Flask-SocketIO
- **Computer Vision**: OpenCV, MediaPipe
- **Machine Learning**: TensorFlow, Keras
- **NLP**: Hugging Face transformers, SentencePiece
- **Other**: pyttsx3 (Text-to-Speech), pyspellchecker

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/username/asl-prediction.git
   cd asl-prediction
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

1. Click "Start" to begin ASL recognition
2. Position your hand within the green box
3. Perform ASL gestures to see predictions
4. Use suggestion controls to select predicted words
5. Click "Generate Sentence" to create a natural sentence
6. Use "Read" to hear the sentence spoken aloud

## Deployment

This application can be deployed to Hugging Face Spaces:

1. Fork this repository
2. Create a new Space on Hugging Face
3. Connect your GitHub repository to the Space
4. Configure as a Flask app
5. Your ASL Prediction App will be live!

## File Structure

```
asl-prediction/
├── flask app/
│   ├── app.py               # Main application file
│   ├── word_prediction.py   # Word prediction logic
│   └── sentence_generator.py # Sentence generation logic
├── templates/
│   └── index.html           # Web interface
├── static/
│   ├── css/
│   └── js/
├── hope.keras               # Trained ASL prediction model
├── label_encoder.pkl        # Label encoder for gestures
├── asl_words.json           # ASL word definitions
└── requirements.txt         # Dependencies
```

## Future Improvements

- Support for two-handed signs
- Finger spelling recognition
- Mobile app version
- Expanded ASL vocabulary
- Custom gesture training

## Contributors

- Brijesh Kumar Ghadei

## License

This project is licensed under the MIT License - see the LICENSE file for details.
