#video_to_text.py

import whisper
def transcribe_and_translate_video(video_path):
    # Load the Whisper model
    model = whisper.load_model("tiny")

    # Transcribe and translate the video file to English
    result = model.transcribe(video_path, task="translate")
    
    # Extract the transcribed and translated text
    text = result['text']
    return text
