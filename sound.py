import sounddevice as sd
import numpy as np
from queue import Queue
from threading import Thread
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import torch

class RealTimeTranslator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = WhisperModel("tiny", device=self.device, compute_type="int8")
        self.translator = GoogleTranslator(source='auto', target='ko')
        self.audio_queue = Queue()
        self.stream = None
        self.running = False

    def find_virtual_device(self):
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if any(name in dev['name'] for name in ['CABLE Output', 'VB-Audio', 'BlackHole']):
                return idx
        raise RuntimeError("가상 오디오 장치를 찾을 수 없습니다. VB-Cable 설치 필요")

    def audio_callback(self, indata, frames, time_info, status):
        if self.running:
            self.audio_queue.put(indata.copy().flatten())

    def process_audio(self):
        buffer_audio = np.array([], dtype=np.float32)
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=1)
                buffer_audio = np.concatenate((buffer_audio, chunk))
                if len(buffer_audio) >= 24000:
                    segment = buffer_audio[:24000]
                    buffer_audio = buffer_audio[8000:]
                    # STT 실행
                    segments, _ = self.model.transcribe(segment, language="en")
                    text = " ".join([s.text for s in segments]).strip()
                    print(f"[DEBUG] Whisper recognized: '{text}'")  # 음성 인식 결과 출력
                    if text:
                        try:
                            translated = self.translator.translate(text)
                            print(f"[DEBUG] Translated: '{translated}'")  # 번역 결과 출력
                            return translated
                        except Exception as e:
                            print(f"[DEBUG] Translation error: {e}")
                    else:
                        print("[DEBUG] No speech detected in this chunk.")
            except Exception as e:
                print(f"[DEBUG] Audio processing error: {e}")
        return None
