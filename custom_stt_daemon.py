import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

# BASE STT DAEMON
SPEECH_KEY   = os.getenv("SPEECH_KEY", "")
SPEECH_REGION= os.getenv("SPEECH_REGION", "")

# CUSTOM STT DAEMON
CUSTOM_ENDPOINT_ID  = os.getenv("CUSTOM_ENDPOINT_ID", "")
CUSTOM_ENDPOINT_KEY = os.getenv("CUSTOM_ENDPOINT_KEY", "")

LOCALE       = os.getenv("LOCALE", "en-US")
INPUT_DIR    = os.getenv("INPUT_DIR", "./incoming_audio")
USE_MIC      = os.getenv("USE_MIC", "false").lower() == "true"

# Segmentation component vars
SEG_STRAT = os.getenv("SEGMENTATION_STRATEGY", "Semantic")  # Semantic/Coarse/Unknown
SEG_INIT_SILENCE_TIMEOUT = os.getenv("SEGMENTATION_INIT_SILENCE_TIMEOUT_MS", "800")
SEG_END_SILENCE_TIMEOUT = os.getenv("SEGMENTATION_END_SILENCE_TIMEOUT_MS", "800")

def build_speech_config() -> speechsdk.SpeechConfig:
    if not CUSTOM_ENDPOINT_KEY or not SPEECH_REGION:
        raise RuntimeError("Set CUSTOM_ENDPOINT_KEY and SPEECH_REGION in .env")

    cfg = speechsdk.SpeechConfig(subscription=CUSTOM_ENDPOINT_KEY, region=SPEECH_REGION)
    # source language
    cfg.speech_recognition_language = LOCALE

    # for the custom daemon's custom endpoint
    if CUSTOM_ENDPOINT_ID:
        cfg.endpoint_id = CUSTOM_ENDPOINT_ID 

    # optional tuning:
    cfg.set_profanity(speechsdk.ProfanityOption.Masked)
    cfg.enable_dictation()  # allows continuous-like punctuation

    # semantic segmentation
    cfg.set_property(speechsdk.PropertyId.Speech_SegmentationStrategy, SEG_STRAT)
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, SEG_INIT_SILENCE_TIMEOUT)
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, SEG_END_SILENCE_TIMEOUT)

    return cfg

def transcribe_microphone():
    """Continuous recognition to observe segmentation in action."""
    cfg = build_speech_config()
    audio_input = speechsdk.AudioConfig(use_default_microphone=True)
    recognizer = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio_input)

    print(f"[STT] Mic on (locale={LOCALE}) | Strategy={SEG_STRAT} | "
          f"SilenceTimeout=[Init: {SEG_INIT_SILENCE_TIMEOUT}ms, End: {SEG_END_SILENCE_TIMEOUT}ms")
    print("[STT] Speak; segments will appear as they are finalized. Press Ctrl+C to stop.\n")

    # hook into events to see both interim and final segment text
    def recognizing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        # partial (interim) text while a segment is still forming
        if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
            print(f"  [Interim] {evt.result.text}")

    def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        # final text for the segment that just closed
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print(f"[Segment] {evt.result.text}")
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print("[Segment] (no match)")

    def session_started_cb(evt: speechsdk.SessionEventArgs):
        print("[Session] Started")

    def session_stopped_cb(evt: speechsdk.SessionEventArgs):
        print("[Session] Stopped")

    def canceled_cb(evt: speechsdk.SpeechRecognitionCanceledEventArgs):
        print(f"[Canceled] {evt.reason} {evt.error_details}")

    recognizer.recognizing.connect(recognizing_cb)
    recognizer.recognized.connect(recognized_cb)
    recognizer.session_started.connect(session_started_cb)
    recognizer.session_stopped.connect(session_stopped_cb)
    recognizer.canceled.connect(canceled_cb)

    # start continuous recognition
    recognizer.start_continuous_recognition()
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n[STT] Stopping…")
    finally:
        recognizer.stop_continuous_recognition()

if __name__ == "__main__":
    transcribe_microphone()
