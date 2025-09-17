import os
import uuid
# --- UPDATED IMPORT ---
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