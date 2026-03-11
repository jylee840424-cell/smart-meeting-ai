import os
import logging
import json
import shutil
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

logger = logging.getLogger(__name__)

# [기존 방어로직] 경로 및 .env 로드 유지
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.normpath(os.path.join(current_dir, "../../../.env"))
load_dotenv(dotenv_path)

# 텔레메트리 에러 방지 (선택 사항)
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

class VectorEmbeddingProcessor:
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        
        # 프로젝트 루트 경로 계산
        self.base_dir = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        
        # 1. 벡터 DB 최상위 경로 (이 하부에 meeting_id 폴더가 생깁니다)
        self.vector_base_path = os.path.join(self.base_dir, "database", "vector")
        
        # 2. 사람이 읽을 수 있는 텍스트 백업 경로
        self.backup_directory = os.path.join(self.base_dir, "database", "processed_text")
        os.makedirs(self.backup_directory, exist_ok=True)
        
        if not self.use_mock:
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    def run(self, meeting_id: str, chunks: list) -> bool:
        if self.use_mock:
            logger.info("Mock 모드: DB 적재 스킵")
            return True

        if not chunks:
            logger.error("[Step 4] 적재할 청크가 없습니다.")
            return False

        try:
            # [핵심 수정] meeting_id별 개별 폴더 경로 설정
            # 예: database/vector/mtg_0f3c57a4/
            specific_vector_path = os.path.join(self.vector_base_path, meeting_id)
            
            # 기존에 동일한 ID의 폴더가 있다면 초기화 (덮어쓰기 방어로직)
            if os.path.exists(specific_vector_path):
                shutil.rmtree(specific_vector_path)
            os.makedirs(specific_vector_path, exist_ok=True)

            print(f"\n✨ [Step 4] [{meeting_id}] 개별 폴더 기반 저장 시작")
            print(f"📂 저장 경로: {specific_vector_path}")
            
            # 메타데이터 정제 및 백업 데이터 준비
            backup_data = []
            for chunk in chunks:
                chunk.metadata["meeting_id"] = meeting_id
                clean_metadata = {
                    k: v for k, v in chunk.metadata.items() 
                    if k not in ["image_base64", "frame_data"]
                }
                chunk.metadata = clean_metadata
                backup_data.append({
                    "page_content": chunk.page_content,
                    "metadata": chunk.metadata
                })

            # --- 1. JSON 파일 저장 (processed_text 폴더) ---
            json_file_path = os.path.join(self.backup_directory, f"{meeting_id}_chunks.json")
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=4)
            print(f"📄 [Step 4] JSON 백업 완료: {json_file_path}")

            # --- 2. 개별 폴더에 Chroma 벡터 DB 적재 ---
            # persist_directory를 specific_vector_path로 지정하여 폴더 격리
            vectordb = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=specific_vector_path,
                collection_name="meeting_collection" # 개별 폴더이므로 이름은 고정해도 무관
            )
            
            vectordb.persist()
            
            print(f"✅ [Step 4] DB 적재 성공 (경로: {specific_vector_path})")
            logger.info(f"✅ [Step 4] [{meeting_id}] 개별 저장 성공")
            
            return True

        except Exception as e:
            print(f"❌ [Step 4] 저장 중 치명적 오류: {e}")
            logger.error(f"❌ [Step 4] 벡터 DB 적재 실패: {e}")
            return False