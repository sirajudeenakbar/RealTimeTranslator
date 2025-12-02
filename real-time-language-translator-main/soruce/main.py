import os
import time
import io
import tempfile
from gtts import gTTS
import streamlit as st
import speech_recognition as sr
from googletrans import LANGUAGES, Translator

# Streamlit-based speech-to-speech translator
translator = Translator()  # Initialize the translator module.

# Create a mapping between language names and language codes
language_mapping = {name: code for code, name in LANGUAGES.items()}

def get_language_code(language_name):
    return language_mapping.get(language_name, language_name)

def translator_function(spoken_text, from_language, to_language):
    return translator.translate(spoken_text, src='{}'.format(from_language), dest='{}'.format(to_language))

def synthesize_to_bytes(text_data, to_language):
    """Synthesize text to MP3 bytes using gTTS and return bytes."""
    try:
        tts = gTTS(text=text_data, lang=str(to_language), slow=False)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_name = tmp.name
        tmp.close()
        tts.save(tmp_name)
        with open(tmp_name, 'rb') as f:
            data = f.read()
        try:
            os.remove(tmp_name)
        except Exception:
            pass
        return data
    except Exception as e:
        st.error(f"TTS error: {e}")
        return None

def main_process_translate_and_play(recognized_text, from_language, to_language):
    """Translate recognized text and return translated text and mp3 bytes."""
    if not recognized_text:
        return None, None
    try:
        translated = translator.translate(recognized_text, src=str(from_language), dest=str(to_language))
        translated_text = getattr(translated, 'text', str(translated))
    except Exception as e:
        st.error(f"Translation error: {e}")
        return None, None

    audio_bytes = synthesize_to_bytes(translated_text, to_language)
    return translated_text, audio_bytes

# UI layout
st.title("Language Translator")

# Dropdowns for selecting languages
from_language_name = st.selectbox("Select Source Language:", list(LANGUAGES.values()))
to_language_name = st.selectbox("Select Target Language:", list(LANGUAGES.values()))

# Convert language names to language codes
from_language = get_language_code(from_language_name)
to_language = get_language_code(to_language_name)

st.markdown("---")

st.subheader("Speech-to-Speech Translator")

# Add enhanced UI styling
st.markdown(
    """
    <style>
    .app-header { text-align: center; margin-bottom: 12px }
    .big-mic { width:140px; height:140px; border-radius: 50%; font-size:48px; display:inline-flex; align-items:center; justify-content:center; color:white; background:linear-gradient(135deg,#6366f1,#8b5cf6); box-shadow:0 12px 30px rgba(99,102,241,0.18); border:none }
    .panel { background:#fff; padding:18px; border-radius:12px; box-shadow:0 6px 20px rgba(2,6,23,0.06) }
    .lang-pill { display:inline-block; padding:6px 10px; border-radius:999px; background:#f1f5f9; color:#0f172a; font-weight:600 }
    .status { font-weight:600; color:#6b7280 }
    </style>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    st.write("**Source language**")
    st.write(from_language_name)
with col2:
    st.write("**Target language**")
    st.write(to_language_name)

st.write("")

input_text = st.text_area("Or type text to translate (optional):", placeholder="Type text here to synthesize audio for the target language")

# Large visual mic and controls
left, right = st.columns([1,1])
with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center"><button id="recordBtn" class="big-mic">🎤</button></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    record_button = st.button("🎤 Record & Translate")
    tts_button = st.button("🔊 Translate Text to Speech")
    st.markdown('</div>', unsafe_allow_html=True)

recognized_placeholder = st.empty()
translated_placeholder = st.empty()

if record_button:
    # Try to record from server-side microphone (requires PyAudio).
    rec = sr.Recognizer()
    mic_ok = True
    mic = None
    try:
        # Check if any microphone devices are available on the system
        mic_list = sr.Microphone.list_microphone_names()
        if not mic_list:
            raise RuntimeError('No microphone devices found')

        # Attempt to create Microphone instance; this may still fail if PyAudio is broken
        mic = sr.Microphone()
    except Exception as e:
        mic_ok = False
        st.error("Microphone unavailable on server (PyAudio may be missing or incompatible).")
        st.info("Fallback: upload a recorded audio file (WAV/MP3). Or install/repair PyAudio in the environment.")

    if mic_ok and mic is not None:
        # Attempt to open the microphone and record; guard against initialization errors
        try:
            # Use the microphone as the source for recording
            with mic as source:
                recognized_placeholder.info("Listening... please speak now")
                rec.adjust_for_ambient_noise(source, duration=0.5)
                audio = rec.listen(source, phrase_time_limit=8)

            try:
                recognized_text = rec.recognize_google(audio, language=from_language)
                recognized_placeholder.success(f"Recognized: {recognized_text}")
            except sr.UnknownValueError:
                recognized_placeholder.error("Could not understand audio")
                recognized_text = None
            except Exception as e:
                recognized_placeholder.error(f"Recognition error: {e}")
                recognized_text = None

            if recognized_text:
                translated_text, audio_bytes = main_process_translate_and_play(recognized_text, from_language, to_language)
                if translated_text:
                    translated_placeholder.write(f"**Translated:** {translated_text}")
                if audio_bytes:
                    st.audio(audio_bytes, format='audio/mp3')

        except Exception as e:
            # Catch low-level microphone errors and switch to upload fallback
            st.error(f"Microphone error while recording: {e}")
            mic_ok = False

    # If microphone is not available, offer file upload fallback
    if not mic_ok:
        uploaded = st.file_uploader("Upload audio file (WAV/MP3) to translate", type=["wav", "mp3", "m4a", "ogg"])
        if uploaded is not None:
            # Save to temporary file and process with SpeechRecognition AudioFile
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix="." + (uploaded.type.split('/')[1] if '/' in uploaded.type else 'wav')) as tmpf:
                    tmpf.write(uploaded.read())
                    tmp_path = tmpf.name

                with sr.AudioFile(tmp_path) as source:
                    audio = rec.record(source)
                try:
                    recognized_text = rec.recognize_google(audio, language=from_language)
                    recognized_placeholder.success(f"Recognized: {recognized_text}")
                    translated_text, audio_bytes = main_process_translate_and_play(recognized_text, from_language, to_language)
                    if translated_text:
                        translated_placeholder.write(f"**Translated:** {translated_text}")
                    if audio_bytes:
                        st.audio(audio_bytes, format='audio/mp3')
                except sr.UnknownValueError:
                    recognized_placeholder.error("Could not understand uploaded audio")
                except Exception as e:
                    recognized_placeholder.error(f"Recognition error: {e}")
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

if tts_button:
    if not input_text or not input_text.strip():
        st.warning("Please enter text to synthesize")
    else:
        translated_text, audio_bytes = main_process_translate_and_play(input_text, from_language, to_language)
        if translated_text:
            translated_placeholder.write(f"**Translated:** {translated_text}")
        if audio_bytes:
            st.audio(audio_bytes, format='audio/mp3')

st.markdown("---")
st.caption("Notes: Recording uses your system microphone (if available). For production use, proxy translations and TTS via a server to protect API keys and avoid client-side rate limits.")
