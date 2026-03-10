import os
import logging
import whisper  # 로컬 위스퍼 소환!
from yt_dlp import YoutubeDL
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AudioToTextProcessor:
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        # 모델 사이즈: base(빠름), small(적당), medium(정확하지만 느림)
        # 일단 가장 가성비 좋은 'base'로 설정해둘게요.
        if not self.use_mock:
            logger.info("🎬 로컬 Whisper 모델(base) 로딩 중... 잠시만 기다려주세요.")
            self.model = whisper.load_model("base")

    def run(self, video_url: str, meeting_id: str) -> Dict[str, Any]:
        """로컬 Whisper를 사용하여 음성을 텍스트로 변환합니다."""
        if self.use_mock:
            return {"transcript_with_time": [{"start": 0.0, "text": "테스트 데이터"}]}

        # 1. 영상 다운로드 및 오디오 추출 (진모님의 기존 yt-dlp 로직)
        audio_path = self._download_audio(video_url, meeting_id)
        
        try:
            logger.info(f"🎙️ 로컬 Whisper 분석 시작 (용량 제한 없음): {audio_path}")
            
            # 2. 로컬에서 직접 받아쓰기 (서버 전송 없음!)
            # task="transcribe", language="ko" 설정으로 한국어 고정 가능
            result = self.model.transcribe(audio_path, verbose=False, language="ko")
            
            # 3. 데이터 규격 맞추기 (Step 2에서 쓰기 편하게)
            transcript_data = []
            for segment in result.get("segments", []):
                transcript_data.append({
                    "start": round(segment["start"], 2),
                    "text": segment["text"].strip()
                })

            logger.info(f"✅ 로컬 Whisper 분석 완료! ({len(transcript_data)} 문장 추출)")
            
            # 사용 후 임시 오디오 파일 삭제 (용량 관리)
            if os.path.exists(audio_path):
                os.remove(audio_path)

            return {"transcript_with_time": transcript_data}

        except Exception as e:
            logger.error(f"❌ 로컬 Whisper 실행 오류: {e}")
            raise e

    def _download_audio(self, video_url: str, meeting_id: str) -> str:
        """yt-dlp를 이용한 오디오 추출 로직"""
        output_dir = "temp_audio"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        output_path = os.path.join(output_dir, f"{meeting_id}.mp3")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(output_dir, f"{meeting_id}.%(ext)s"),
            'quiet': True
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        return output_path