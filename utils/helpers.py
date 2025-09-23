import os
import uuid
import time
import random
import hmac
import hashlib
import json
from base64 import b64encode
from deep_translator import GoogleTranslator
import speech_recognition as sr
from pydub import AudioSegment

# --- Important Setup Note ---
# These functions use free libraries. Install them using pip:
# pip install deep-translator SpeechRecognition pydub
#
# For audio conversion, you also need ffmpeg installed on your system.

def free_translate(text: str, target_lang: str = 'en') -> str:
    """
    Translates text using the more reliable deep-translator library.
    It automatically detects the source language.
    """
    try:
        # Automatically detects the source language ('auto')
        translated_text = GoogleTranslator(source='auto', target=target_lang).translate(text)
        # Return the translated text, or the original if translation returns None
        return translated_text if translated_text else text
    except Exception as e:
        print(f"Translation failed with deep-translator: {e}")
        # Fallback to returning the original text if any error occurs
        return text

def free_audio_to_text(audio_path: str, language_code: str) -> str:
    """
    Transcribes an audio file using the free SpeechRecognition library.
    This version is corrected to prevent file locking errors on Windows.
    """
    recognizer = sr.Recognizer()
    wav_path = None  # Initialize path for the temporary file

    try:
        # Convert the original audio to a compatible WAV format
        sound = AudioSegment.from_file(audio_path)
        wav_path = audio_path + ".wav"
        sound.export(wav_path, format="wav")

        # Open and process the temporary WAV file
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
        
        # Now that the file is closed, recognize the speech
        text = recognizer.recognize_google(audio_data, language=language_code)
        return text

    except sr.UnknownValueError:
        return "[Could not understand audio]"
    except sr.RequestError as e:
        print(f"Speech recognition service request failed; {e}")
        return "[Speech service error]"
    except Exception as e:
        print(f"An error occurred during audio processing: {e}")
        return "[Audio processing failed]"
    finally:
        # Clean up the temporary WAV file if it exists
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError as e:
                print(f"Error removing temporary file {wav_path}: {e}")

def save_file_and_get_name(upload_folder: str, file_storage) -> str:
    """
    Saves an uploaded file with a unique name and returns the filename.
    """
    ext = os.path.splitext(file_storage.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext.lower()}"
    path = os.path.join(upload_folder, filename)
    file_storage.save(path)
    return filename

def generate_zego_token(app_id: int, server_secret: str, user_id: str, effective_time_in_seconds: int = 3600):
    """Generates a secure token for ZegoCloud."""
    if not isinstance(app_id, int):
        raise TypeError("app_id must be an integer.")
    if not isinstance(server_secret, str):
        raise TypeError("server_secret must be a string.")
    if not isinstance(user_id, str):
        raise TypeError("user_id must be a string.")

    create_time = int(time.time())
    expire_time = create_time + effective_time_in_seconds
    nonce = random.randint(0, 0xFFFFFFFF)

    token_info = {
        "app_id": app_id,
        "user_id": user_id,
        "nonce": nonce,
        "ctime": create_time,
        "expire": expire_time,
    }

    # Token payload ko JSON format mein taiyaar karein
    payload = json.dumps(token_info)

    # HMAC-SHA256 se signature banayein
    digest = hmac.new(server_secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).digest()
    
    # Final token ko combine karein
    token_data = b'\x00\x04' + int(expire_time).to_bytes(4, 'big') + len(digest).to_bytes(2, 'big') + digest + len(payload).to_bytes(2, 'big') + payload.encode('utf-8')

    # Base64 encode karke final token return karein
    return b64encode(token_data).decode('utf-8')