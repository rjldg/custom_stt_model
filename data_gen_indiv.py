import os
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

speech_key = os.getenv("SPEECH_KEY", "<PUT_YOUR_KEY_HERE>")
endpoint_url = os.getenv("SPEECH_ENDPOINT", "https://japaneast.tts.speech.microsoft.com")

# Voice (adjust to a valid voice in your region)
voice_name = "en-US-AvaMultilingualNeural"

# Text to synthesize
text = "Good morning, have you eaten lunch yet?"

# --- Speech config ---
speech_config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=endpoint_url)
speech_config.speech_synthesis_voice_name = voice_name

# Set a dataset-friendly WAV format (16 kHz, 16-bit, mono PCM)
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
)

# --- Output file path (same directory) ---
out_wav = os.path.join(os.getcwd(), "tts_output.wav")
audio_config = speechsdk.audio.AudioOutputConfig(filename=out_wav)

# --- Synthesizer that writes to file ---
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config,
                                                 audio_config=audio_config)

# --- Synthesize ---
result = speech_synthesizer.speak_text_async(text).get()

# --- Check result ---
if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
    print(f"✅ Synthesized and saved: {out_wav}")
elif result.reason == speechsdk.ResultReason.Canceled:
    cancellation_details = result.cancellation_details
    print(f"❌ Speech synthesis canceled: {cancellation_details.reason}")
    if cancellation_details.reason == speechsdk.CancellationReason.Error:
        print(f"Error details: {cancellation_details.error_details}")
        print("Make sure your key/endpoint/voice are valid and your network allows access.")
