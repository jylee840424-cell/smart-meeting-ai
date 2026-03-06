import os
import logging
import yt_dlp
from openai import OpenAI

logger = logging.getLogger(__name__)

class AudioToTextProcessor:
    def __init__(self, use_mock=False):
        self.use_mock = use_mock
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def run(self, video_url: str) -> str:
        logger.info(f"[Step 1] 유튜브 영상({video_url}) 오디오 추출 및 텍스트 변환 시작...")
        
        if self.use_mock:
            return "이것은 가짜 대본입니다."

        temp_filename = "temp_audio"
        audio_path = f"{temp_filename}.mp3"

        try:
            # 1. 유튜브 다운로드 옵션 최적화
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
                'outtmpl': f'{temp_filename}.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # 방어 로직 1: 파일이 실제로 생성되었는지 확인
            if not os.path.exists(audio_path):
                raise Exception("유튜브 오디오 추출에 실패했습니다. (영상이 제한되었거나 지원되지 않는 URL입니다)")

            # 2. Whisper API 호출
            logger.info("OpenAI Whisper API에 음성 인식 요청 중...")
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    response_format="text"
                )
            
            # 방어 로직 2: 텍스트가 너무 짧거나 비어있는 경우
            if not transcription or len(transcription.strip()) < 5:
                raise Exception("추출된 음성에 유효한 대화 내용이 없습니다.")

            return transcription
            
        except Exception as e:
            logger.error(f"오디오 변환 중 오류 발생: {e}")
            raise e
        finally:
            # 안전한 임시 파일 청소
            if os.path.exists(audio_path):
                os.remove(audio_path)