#audio_to_text.py

import whisper
def transcribe_audio(audio_file):
    # Load the Whisper model
    model = whisper.load_model("tiny")
    
    # Transcribe and translate the audio file to English
    result = model.transcribe(audio_file, task="translate")
    
    # Extract the transcribed and translated text
    text = result['text']
    return text
