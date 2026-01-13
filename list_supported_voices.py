import os
import sys
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

SPEECH_KEY   = os.getenv("SPEECH_KEY", "")
SPEECH_REGION= os.getenv("SPEECH_REGION", "")

VOICE_NAME   = os.getenv("VOICE_NAME", "en-US-JennyNeural")
TEXT         = os.getenv("TTS_TEXT", "Hello, welcome to Azure AI Foundry!")

OUT_WAV      = os.path.join(os.getcwd(), "tts_output.wav")

def ensure_config():
    if not SPEECH_KEY or not SPEECH_REGION:
        print("Set SPEECH_KEY and SPEECH_REGION environment variables.")
        sys.exit(1)

def list_voices():
    """List voices available in your region using the Speech SDK."""
    cfg = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
    result = synth.get_voices_async().get()  # lists voices for this region
    if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
        print(f"Voices in region '{SPEECH_REGION}': {len(result.voices)}")
        for v in result.voices:  # print all supported voices
            print(f" - {v.name} | locale={v.locale} | gender={v.gender}")
    else:
        print("Could not retrieve voices; check key/region/network.")
        if hasattr(result, "cancellation_details"):
            print("Details:", result.cancellation_details.error_details)

def synth_to_wav():
    """Synthesize TEXT with VOICE_NAME into a dataset-friendly WAV file."""
    cfg = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    cfg.speech_synthesis_voice_name = VOICE_NAME

    cfg.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
    )

    audio_out = speechsdk.audio.AudioOutputConfig(filename=OUT_WAV)
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=audio_out)

    print(f"Synthesizing with voice '{VOICE_NAME}' to '{OUT_WAV}'...")
    result = synth.speak_text_async(TEXT).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"✅ Saved: {OUT_WAV}")
    else:
        print(f"❌ Synthesis failed: {result.reason}")
        if hasattr(result, "cancellation_details"):
            print("Error details:", result.cancellation_details.error_details)
            print("Hint: Choose a voice that exists in your region (see list above).")

if __name__ == "__main__":
    ensure_config()
    print("=== Listing voices in your region (use one of these) ===")
    list_voices()
    print("\n=== Synthesizing to WAV ===")
    synth_to_wav()
