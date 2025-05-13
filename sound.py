import sounddevice as sd
import numpy as np
from queue import Queue
from threading import Thread
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import torch
import datetime

def update_korean_script_html(translated_text):
    now = datetime.datetime.now().strftime("[%H:%M:%S]")
    line = f"{now} {translated_text}"

    # 로그 누적
    with open("korean_only_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")

    # 전체 HTML 재생성
    with open("korean_only_log.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    html = "<html><head><meta charset='utf-8'><meta http-equiv='refresh' content='2'>"
    html += """<style>
        body { font-family: 'Pretendard','Noto Sans KR',sans-serif; padding: 40px; background: #fff; color: #111; }
        .line { font-size: 18px; margin-bottom: 12px; }
    </style></head><body><h2>🗣 실시간 번역 스크립트</h2>
    """
    for l in lines:
        html += f"<div class='line'>{l.strip()}</div>\n"
    html += "</body></html>"

    with open("translated_output.html", "w", encoding="utf-8") as f:
        f.write(html)

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

                    segments, _ = self.model.transcribe(segment, language="en")
                    text = " ".join([s.text for s in segments]).strip()
                    print(f"[DEBUG] Whisper recognized: '{text}'")
                    if text:
                        try:
                            translated = self.translator.translate(text)
                            print(f"[DEBUG] Translated: '{translated}'")
                            update_korean_script_html(translated)  # 자막 업데이트
                            return translated
                        except Exception as e:
                            print(f"[DEBUG] Translation error: {e}")
                    else:
                        print("[DEBUG] No speech detected in this chunk.")
            except Exception as e:
                print(f"[DEBUG] Audio processing error: {e}")
        return None



