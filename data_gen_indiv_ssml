
# tts_ssml_en_us_with_events.py
import os
import json
import datetime
from pathlib import Path

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

SPEECH_KEY = os.getenv("SPEECH_KEY", "<PUT_YOUR_KEY_HERE>")
SPEECH_REGION = os.getenv("SPEECH_REGION") 
SPEECH_ENDPOINT = os.getenv("SPEECH_ENDPOINT")
VOICE_NAME = os.getenv("VOICE_NAME", "en-US-AvaMultilingualNeural")
OUT_DIR = Path(os.getenv("OUT_DIR", "tts_out"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

text_en = (
    "Good afternoon! This is a quick demo of SSML with pauses. "
    "We will insert a two-second pause right now, and then continue speaking."
)
pause_ms = 2000  # 2 seconds

# --- Build SSML (en-US) ---
# - <break time="…ms"/> adds an explicit pause mid-stream.
# - <mstts:silence type="Sentenceboundary" value="150ms"/> slightly increases pauses between sentences.
# - <bookmark> lets you observe precise positions via the BookmarkReached event.
ssml = f"""<?xml version="1.0" encoding="utf-8"?>
<speak version="1.0"
       xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:mstts="https://www.w3.org/2001/mstts"
       xml:lang="en-US">
  <voice name="{VOICE_NAME}">
    <mstts:silence type="Sentenceboundary" value="150ms"/>
    <mstts:viseme type="redlips_front"/>

    <p>
      <s>
        <bookmark mark="intro_begin"/>
        {text_en.split("right now")[0].strip()} right now.
        <bookmark mark="intro_end"/>
      </s>

      <break time="{pause_ms}ms"/>

      <s>
        Now we continue. Thanks for listening!
      </s>
    </p>
  </voice>
</speak>
"""

if SPEECH_ENDPOINT:
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, endpoint=SPEECH_ENDPOINT)
else:
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION or "eastus")

speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
)

# Request sentence boundary info so WordBoundary events contain sentence spans
speech_config.set_property(
    property_id=speechsdk.PropertyId.SpeechServiceResponse_RequestSentenceBoundary, value="true"
)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_wav = OUT_DIR / f"tts_en-US_{timestamp}.wav"
audio_config = speechsdk.audio.AudioOutputConfig(filename=str(out_wav))

synth = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

# ---------------------- Event handlers ----------------------
def on_bookmark(evt: speechsdk.SessionEventArgs):
    print(f"[BookmarkReached] t≈{(evt.audio_offset + 5000)/10000:.1f} ms | mark={evt.text}")

def on_synthesis_started(evt: speechsdk.SessionEventArgs):
    print("[SynthesisStarted]")

def on_synthesizing(evt: speechsdk.SessionEventArgs):
    print(f"[Synthesizing] chunk={len(evt.result.audio_data)} bytes")

def on_synthesis_completed(evt: speechsdk.SessionEventArgs):
    print("[SynthesisCompleted]")
    print(f"  audio bytes={len(evt.result.audio_data)}")
    print(f"  audio duration={evt.result.audio_duration}")

def on_canceled(evt: speechsdk.SessionEventArgs):
    print("[SynthesisCanceled]")
    try:
        print("  details:", evt.result.cancellation_details.error_details)
    except Exception:
        pass

def on_viseme(evt: speechsdk.SessionEventArgs):
    print(f"[Viseme] t≈{(evt.audio_offset + 5000)/10000:.1f} ms | visemeId={evt.viseme_id}")

def on_word_boundary(evt: speechsdk.SessionEventArgs):
    print(
        f"[WordBoundary] type={evt.boundary_type} "
        f"t≈{(evt.audio_offset + 5000)/10000:.1f} ms dur={evt.duration} "
        f"text='{evt.text}' textOffset={evt.text_offset} wordLen={evt.word_length}"
    )

synth.bookmark_reached.connect(on_bookmark)
synth.synthesis_started.connect(on_synthesis_started)
synth.synthesizing.connect(on_synthesizing)
synth.synthesis_completed.connect(on_synthesis_completed)
synth.synthesis_canceled.connect(on_canceled)
synth.viseme_received.connect(on_viseme)
synth.synthesis_word_boundary.connect(on_word_boundary)

print("SSML to synthesize:\n", ssml)
result = synth.speak_ssml_async(ssml).get()

if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
    print(f"✅ Synthesized and saved: {out_wav.resolve()}")
elif result.reason == speechsdk.ResultReason.Canceled:
    cd = result.cancellation_details
    print(f"❌ Canceled: {cd.reason}")
    if cd.error_details:
        print(f"   Error details: {cd.error_details}")
        print("   Check key/region/endpoint/voice and network connectivity.")
