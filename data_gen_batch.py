import os
import sys
import random
import re
from pathlib import Path
from typing import List
from xml.sax.saxutils import escape as xml_escape

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

# ---------------------------
# Config (set via environment)
# ---------------------------
SPEECH_KEY = os.getenv("SPEECH_KEY", "")
SPEECH_REGION = os.getenv("SPEECH_REGION", "")         # recommended
SPEECH_ENDPOINT = os.getenv("SPEECH_ENDPOINT", "")     # alternative
PHRASES_FILE = os.getenv("PHRASES_FILE", "./CSI_Interfusion_STT_testing_dataset_20.txt")

OUT_DIR = Path(os.getenv("OUT_DIR", "./tts_dataset"))
TRANS_PATH = OUT_DIR / "trans.txt"

# Dataset-friendly WAV format
OUTPUT_FORMAT = speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm

# ---------------------------
# Voices (from your list)
# ---------------------------
VOICE_CHOICES = [
    "en-US-AvaMultilingualNeural",
    "en-US-AndrewMultilingualNeural",
    "en-US-AmandaMultilingualNeural",
    "en-US-AdamMultilingualNeural",
    "en-US-EmmaMultilingualNeural",
    "en-US-PhoebeMultilingualNeural",
    "en-US-AlloyTurboMultilingualNeural",
    "en-US-EchoTurboMultilingualNeural",
    "en-US-FableTurboMultilingualNeural",
    "en-US-OnyxTurboMultilingualNeural",
    "en-US-NovaTurboMultilingualNeural",
    "en-US-ShimmerTurboMultilingualNeural",
    "en-US-BrianMultilingualNeural",
    "en-US-AvaNeural",
    "en-US-AndrewNeural",
    "en-US-EmmaNeural",
    "en-US-BrianNeural",
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "en-US-AriaNeural",
    "en-US-DavisNeural",
    "en-US-JaneNeural",
    "en-US-JasonNeural",
    "en-US-KaiNeural",
    "en-US-LunaNeural",
    "en-US-SaraNeural",
    "en-US-TonyNeural",
    "en-US-NancyNeural",
    "en-US-CoraMultilingualNeural",
    "en-US-ChristopherMultilingualNeural",
    "en-US-BrandonMultilingualNeural",
    "en-US-AmberNeural",
    "en-US-AnaNeural",
    "en-US-AshleyNeural",
    "en-US-BrandonNeural",
    "en-US-ChristopherNeural",
    "en-US-CoraNeural",
    "en-US-DavisMultilingualNeural",
    "en-US-DerekMultilingualNeural",
    "en-US-DustinMultilingualNeural",
    "en-US-ElizabethNeural",
    "en-US-EricNeural",
    "en-US-JacobNeural",
]

# ---------------------------
# Helpers
# ---------------------------

def ensure_config():
    if not SPEECH_KEY:
        print("Set SPEECH_KEY (env var).")
        sys.exit(1)
    if not SPEECH_REGION and not SPEECH_ENDPOINT:
        print("Set SPEECH_REGION or SPEECH_ENDPOINT (env var).")
        sys.exit(1)

def load_phrases(path: str, sample_n: int = 50) -> List[str]:
    """Load lines, clean, de-duplicate, and sample N distinct phrases."""
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(f"Dataset not found: {src}")
    lines = [ln.strip() for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]
    # Remove any numeric prefixes like '01. '
    lines = [re.sub(r"^\d+\\.?\\s*", "", ln) for ln in lines]
    uniq = list(dict.fromkeys(lines))
    if len(uniq) < sample_n:
        raise RuntimeError(f"Need at least {sample_n} distinct phrases; only {len(uniq)} after cleaning.")
    random.shuffle(uniq)
    return uniq[:sample_n]

def build_speech_config() -> speechsdk.SpeechConfig:
    if SPEECH_REGION:
        cfg = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    else:
        cfg = speechsdk.SpeechConfig(subscription=SPEECH_KEY, endpoint=SPEECH_ENDPOINT)
    cfg.set_speech_synthesis_output_format(OUTPUT_FORMAT)
    return cfg

def build_ssml_with_pauses(text: str, voice: str) -> str:
    """
    Build SSML with the required <voice> tag and random natural pauses:
    - Breaks after common punctuation.
    - Optional mid-sentence break.
    """
    txt = xml_escape(text)

    def punct_breaks(s: str) -> str:
        s = re.sub(r",\\s*", lambda m: f", <break time=\\\"{random.choice([300,450,600,750,900,1200])}ms\\\"/> ", s)
        s = re.sub(r";\\s*", lambda m: f"; <break time=\\\"{random.choice([300,450,600,750,900,1200])}ms\\\"/> ", s)
        s = re.sub(r":\\s*", lambda m: f": <break time=\\\"{random.choice([300,450,600,750,900,1200])}ms\\\"/> ", s)
        s = re.sub(r"—\\s*", lambda m: f"— <break time=\\\"{random.choice([350,600,900,1200])}ms\\\"/> ", s)
        s = re.sub(r"-\\s*", lambda m: f"- <break time=\\\"{random.choice([350,600,900])}ms\\\"/> ", s)
        return s

    txt = punct_breaks(txt)

    if len(text.split()) > 8 and random.random() < 0.6:
        mid_break = f'<break time="{random.choice([350,500,650,1000])}ms"/>'
        txt = re.sub(r"(\\w+\\s+\\w+)", rf"\\1 {mid_break}", txt, count=1)

    ssml = (
        f'<speak version="1.0" xml:lang="en-US">'
        f'  <voice name="{voice}">'
        f'    {txt}'
        f'  </voice>'
        f'</speak>'
    )
    return ssml

def synth_one(cfg: speechsdk.SpeechConfig, ssml: str, out_wav: Path) -> bool:
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(out_wav))
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=audio_config)
    result = synth.speak_ssml_async(ssml).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    else:
        print(f"❌ Synthesis failed for {out_wav.name}: {result.reason}")
        if hasattr(result, "cancellation_details"):
            print("   Details:", result.cancellation_details.error_details)
        return False

def main():
    ensure_config()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    phrases = load_phrases(PHRASES_FILE, sample_n=20)
    cfg = build_speech_config()

    # Prepare transcript file
    with open(TRANS_PATH, "w", encoding="utf-8") as trans:
        for idx, text in enumerate(phrases, start=1):
            fname = f"{idx:03d}_.wav"
            out_wav = OUT_DIR / fname

            # Randomly select a voice from your list (no region filtering)
            voice = random.choice(VOICE_CHOICES)

            ssml = build_ssml_with_pauses(text, voice)
            ok = synth_one(cfg, ssml, out_wav)

            # Write transcript (ground truth)
            trans.write(f"{fname}\\t{text}\\n")

            if ok:
                print(f"✅ Saved {fname} | voice={voice}")
            else:
                print(f"⚠️ Failed: {fname} | voice={voice}")

    print(f"\\nDone. WAVs in: {OUT_DIR.resolve()}")
    print(f"Transcript: {TRANS_PATH.resolve()}")

if __name__ == "__main__":
    main()
