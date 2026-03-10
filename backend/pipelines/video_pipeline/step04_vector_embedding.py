import os
import logging
import json
from dotenv import load_dotenv
from typing import List, Dict, Any

# 로깅 설정
logger = logging.getLogger(__name__)

# 1. .env 로드 (진모님의 경로 로직 유지)
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.normpath(os.path.join(current_dir, "../../../.env"))
load_dotenv(dotenv_path)

class VectorEmbeddingProcessor:
    """
    외부 라이브러리(Chroma 등) 설치 없이 
    회의 텍스트 데이터를 관리하기 쉽게 저장하는 클래스.
    """
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        
        # 프로젝트 루트 경로 기준 데이터 저장 위치 설정
        base_dir = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        self.storage_directory = os.path.join(base_dir, "database", "processed_text")
        
        if not os.path.exists(self.storage_directory):
            os.makedirs(self.storage_directory)

    def run(self, meeting_id: str, chunks: list) -> bool:
        """
        Step 03에서 생성된 청크 리스트를 JSON 파일로 깔끔하게 저장합니다.
        추가 라이브러리 설치가 필요 없어 배포에 유리합니다.
        """
        if self.use_mock:
            logger.info("Mock 모드: 저장을 건너뜁니다.")
            return True

        try:
            # 1. 저장 경로 설정 (회의별 ID 사용)
            file_path = os.path.join(self.storage_directory, f"{meeting_id}_chunks.json")
            
            # 2. 413 에러 및 용량 방지: 순수 텍스트와 필수 메타데이터만 추출
            clean_data = []
            for chunk in chunks:
                if isinstance(chunk, dict):
                    content = chunk.get("page_content", chunk.get("text", ""))
                    # 이미지 base64 등 무거운 데이터는 여기서 컷!
                    metadata = {
                        k: v for k, v in chunk.get("metadata", {}).items() 
                        if k not in ["image_base64", "frame_data"]
                    }
                    clean_data.append({"content": content, "metadata": metadata})
                else:
                    clean_data.append({"content": str(chunk), "metadata": {}})

            # 3. JSON으로 저장 (다른 사람들도 바로 읽을 수 있음)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ [Step 4] 텍스트 데이터 저장 완료: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [Step 4] 데이터 저장 중 오류: {e}")
            return False