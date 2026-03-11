import logging
import os
from dotenv import load_dotenv
from typing import List, Dict, Any

# [기존 방어로직] 경로 설정 유지
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.normpath(os.path.join(current_dir, "../../../.env"))
load_dotenv(dotenv_path)

logger = logging.getLogger(__name__)

class TextSplitterProcessor:
    def __init__(self, chunk_size=800, chunk_overlap=100, use_mock=False):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_mock = use_mock

    def run(self, diarized_data: List[Dict[str, Any]]) -> List[Any]:
        # [해결] logger.info가 안 보일 수 있으므로 터미널 강제 출력용 print 추가
        print(f"\n🚀 [Step 3] 텍스트 분할 가동 (입력 데이터: {len(diarized_data)}건)")
        logger.info(f"[Step 3] 텍스트 분할 시작... 데이터 개수: {len(diarized_data)}")
        
        if not diarized_data:
            print("❌ [Step 3] 에러: 이전 단계(Step 2)로부터 넘어온 데이터가 없습니다.")
            return []

        # [표준화] Step 01, 02와 맞춘 'start' 키 중심의 텍스트 결합
        formatted_lines = []
        for d in diarized_data:
            # start가 없으면 time을 보고, 그것도 없으면 0.0 사용
            start_time = d.get('start') if d.get('start') is not None else d.get('time', '0.0')
            speaker = d.get('speaker', '미확인 화자')
            content = d.get('text', '').strip()
            
            if content:
                formatted_lines.append(f"[{start_time}s] {speaker}: {content}")

        full_document = "\n".join(formatted_lines)
        
        if not full_document:
            print("⚠️ [Step 3] 경고: 합쳐진 문서 내용이 비어있습니다.")
            return []

        if self.use_mock:
            print("⚠️ [Step 3] Mock 모드로 실행 중입니다.")
            return [{"page_content": full_document, "metadata": {"source": "meeting_mock"}}]

        try:
            # LangChain 스플리터 로드 및 실행
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""] 
            )
            
            # 문서를 청크로 분할
            chunks = text_splitter.create_documents(
                [full_document], 
                metadatas=[{"source": "meeting_transcript", "type": "speech_to_text"}]
            )
            
            # [결과 보고] 이 로그가 찍혀야 정상적으로 4번으로 넘어갑니다.
            print(f"✅ [Step 3] 분할 성공: {len(chunks)}개의 청크 생성 완료.")
            logger.info(f"✅ [Step 3] 분할 완료: {len(chunks)}개의 청크 생성.")
            
            return chunks

        except Exception as e:
            print(f"❌ [Step 3] 치명적 오류 발생: {e}")
            logger.error(f"❌ [Step 3] 오류: {e}")
            return []