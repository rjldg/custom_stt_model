import os
import time
import json
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

# Phrase list for boosting relevant context of domain-specific terms
PHRASE_LIST = [
    "CSI Interfusion",
    "Hello, you’ve reached CSI Interfusion support",
    "Welcome to CSI Interfusion technical desk",
    "Thank you for calling CSI Interfusion",
    "Good afternoon, CSI Interfusion support here",
    "Hi, this is CSI Interfusion customer care",
    "OmniConnect setup",
    "Secure gateway",
    "Predictive analytics module",
    "Advanced interoperability features",
    "Compliance certifications",
    "Latency optimization settings",
    "Enterprise platform",
    "Multilingual transcription",
    "Confirm the status of my CSI Interfusion service request",
    "Send me documentation for CSI Interfusion’s AI module",
    "Upgrade my CSI Interfusion support plan to premium",
    "Resetting my password for CSI Interfusion portal",
    "Help me troubleshoot my CSI Interfusion integration issue",
]

def build_speech_config() -> speechsdk.SpeechConfig:
    if not CUSTOM_ENDPOINT_KEY or not SPEECH_REGION:
        raise RuntimeError("Set CUSTOM_ENDPOINT_KEY and SPEECH_REGION in .env")

    cfg = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    recognizer = speechsdk.SpeechRecognizer(speech_config=cfg)

    # source language
    cfg.speech_recognition_language = LOCALE

    # for the custom daemon's custom endpoint
    if CUSTOM_ENDPOINT_ID:
        #cfg.endpoint_id = CUSTOM_ENDPOINT_ID 
        pass

    # optional tuning:
    # semantic segmentation
    cfg.set_property(speechsdk.PropertyId.Speech_SegmentationStrategy, SEG_STRAT)
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, SEG_INIT_SILENCE_TIMEOUT)
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, SEG_END_SILENCE_TIMEOUT)

    # for punctuation dictation (WARNING: affects segmentation behavior)
    #cfg.enable_dictation()

    # for profanity/vulgar word masking
    cfg.set_profanity(speechsdk.ProfanityOption.Masked)

    cfg.output_format = speechsdk.OutputFormat.Detailed

    return cfg

# phrase list attachment for boosting domain-specific terms' context
def attach_phrase_list(recognizer: speechsdk.SpeechRecognizer):
    pl = speechsdk.PhraseListGrammar.from_recognizer(recognizer)
    
    for p in PHRASE_LIST:
        pl.addPhrase(p)

def transcribe_microphone():
    """Continuous recognition to observe segmentation in action."""
    cfg = build_speech_config()
    audio_input = speechsdk.AudioConfig(use_default_microphone=True)
    recognizer = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio_input)

    attach_phrase_list(recognizer)

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
            print(f"[Segment][Display]   {evt.result.text}")

            try:
                payload = json.loads(evt.result.json)
                # payload structure: { "NBest": [ { "Display": "...", "Lexical": "...", "ITN": "...", "MaskedITN": "...", ... } ], ... }
                best = payload.get("NBest", [{}])[0]
                #print(f"[Segment][Lexical]   {best.get('Lexical', '')}")
                #print(f"[Segment][ITN]       {best.get('ITN', '')}")
                #print(f"[Segment][MaskedITN] {best.get('MaskedITN', '')}")
                # Optional: confidence, words with timings, etc., if present:
                # print(f"[Segment][Confidence] {best.get('Confidence')}")
                # for w in best.get("Words", []): print(w)
            except Exception as ex:
                print(f"[Segment] (detailed JSON unavailable) {ex}")

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

# testing helper functions
def transcribe_file(wav_path: Path) -> Optional[str]:
    cfg = build_speech_config()
    audio_input = speechsdk.AudioConfig(filename=str(wav_path))
    recognizer = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio_input)

    attach_phrase_list(recognizer)
    
    print(f"[STT] Transcribing: {wav_path.name} (locale={LOCALE})")
    
    # hook into events to see both interim and final segment text
    def recognizing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        # partial (interim) text while a segment is still forming
        if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
            print(f"  [Interim] {evt.result.text}")

    def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        # final text for the segment that just closed
        
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print(f"[Segment][Display]   {evt.result.text}")

            try:
                payload = json.loads(evt.result.json)
                # payload structure: { "NBest": [ { "Display": "...", "Lexical": "...", "ITN": "...", "MaskedITN": "...", ... } ], ... }
                best = payload.get("NBest", [{}])[0]
                print(f"[Segment][Lexical]   {best.get('Lexical', '')}")
                print(f"[Segment][ITN]       {best.get('ITN', '')}")
                print(f"[Segment][MaskedITN] {best.get('MaskedITN', '')}")
                # Optional: confidence, words with timings, etc., if present:
                # print(f"[Segment][Confidence] {best.get('Confidence')}")
                # for w in best.get("Words", []): print(w)
            except Exception as ex:
                print(f"[Segment] (detailed JSON unavailable) {ex}")

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
        print("\n[STT] Pausing... Waiting on the next file")
    finally:
        recognizer.stop_continuous_recognition()

def watch_folder():
    input_dir = Path(INPUT_DIR)
    input_dir.mkdir(parents=True, exist_ok=True)
    print(f"[Daemon] Watching folder: {input_dir.resolve()} (drop .wav/.mp3/.mp4 etc.)")
    print(f"[Segmentation] Strategy={SEG_STRAT}, SilenceTimeout=[Init: {SEG_INIT_SILENCE_TIMEOUT}ms, End: {SEG_END_SILENCE_TIMEOUT}ms")

    seen = set()
    try:
        while True:
            # naive polling for scale, use watchdog/inotify, etc.
            for p in input_dir.iterdir():
                if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".mp4", ".m4a", ".flac"} and p not in seen:
                    seen.add(p)
                    transcribe_file(p)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n[Daemon] Stopped.")

if __name__ == "__main__":
    mic = str(input("Use microphone? (Y/N): ")).strip().lower()

    if mic == "y":
        transcribe_microphone()
    else:
        watch_folder() 
