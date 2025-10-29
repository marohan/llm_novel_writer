import json
from typing import List, Dict, Optional, Tuple
import numpy as np

# Google Generative AI SDK import
from google import genai
from google.genai import types
from google.genai.errors import APIError

from novel_writer.client_setup import GroqClient
from novel_writer.writer_config import WriterConfig, NovelSetup, Chapter
from novel_writer.utils import retry_on_error, safe_json_parse

# ============================================================================
# 에디터
# ============================================================================

class Editor:
    """내용 검토 및 수정 제안"""

    def __init__(self, client: GroqClient, config: WriterConfig, setup: NovelSetup):
        self.client = client
        self.config = config
        self.setup = setup

    def _format_setup(self) -> str:
        chars = "\n".join([f"- {c['name']}: {c.get('description', '')}"
                           for c in self.setup.characters])
        return f"""시놉시스: {self.setup.synopsis}
문체: {self.setup.writing_style}
문체 예시: {self.setup.style_example}
캐릭터: {chars}
세계: {self.setup.world_setting}"""

    def review_structure(self, chapters: List[Chapter]) -> Dict:
        print("\n=== 챕터 구조 검토 중 ===")

        @retry_on_error(self.config)
        def _review():
            system_prompt = "당신은 경험 많은 편집자입니다. 반드시 JSON 형식으로 응답하세요."

            chapters_text = "\n".join([
                f"챕터 {ch.number}: {ch.title} - {ch.outline}"
                for ch in chapters
            ])

            prompt = f"""다음 챕터 구조를 검토하세요.

원래 설정:
{self._format_setup()}

제안된 구조:
{chapters_text}

JSON 형식:
{{
  "scores": {{"story_flow": 8, "pacing": 7, "character_development": 9, "consistency": 8}},
  "suggestions": ["제안1", "제안2"],
  "status": "승인" or "수정필요",
  "feedback": "전체 피드백 요약 (문자열)"
}}"""

            response = self.client.generate(
                model=self.config.editor_model,
                prompt=prompt,
                system=system_prompt,
                temperature=self.config.editor_temperature,
                format_json=True,
            )

            data = safe_json_parse(response)
            scores = data.get("scores", {})
            avg_score = np.mean(list(scores.values())) if scores else 0

            return {
                'scores': list(scores.values()),
                'average_score': float(avg_score),
                'suggestions': data.get("suggestions", []),
                'status': data.get("status", "수정필요"),
                'feedback_text': data.get("feedback", "")
            }

        review = _review()
        print(f"✓ 검토 완료 - 평균: {review['average_score']:.1f}/10, 상태: {review['status']}")
        return review

    def review_content(self, chapter: Chapter, context: str,
                       target_words: Tuple[int, int],
                       short_term_memory: str = "",  # 💡 추가
                       long_term_memory: str = "") -> Dict:
        print(f"\n=== 챕터 {chapter.number} 검토 중 ===")

        min_words, max_words = target_words

        @retry_on_error(self.config)
        def _review():
            try:
                system_prompt = "당신은 소설 편집자입니다. JSON 형식으로 응답하세요."

                # 💡 타입 검증
                if not isinstance(chapter.content, str):
                    print(f"  ⚠️ chapter.content가 string이 아닙니다: {type(chapter.content)}")
                    chapter.content = str(chapter.content)

                max_chars = self.config.max_review_tokens
                review_content = chapter.content
                if len(review_content) > max_chars:
                    half = max_chars // 2
                    review_content = review_content[:half] + "\n\n[... 중간 생략 ...]\n\n" + review_content[-half:]

                # 💡 단기 메모리 섹션 추가
                stm_section = ""
                if short_term_memory:
                    stm_section = f"\n--- 단기 메모리 (최근 챕터 내용) ---\n{short_term_memory}\n"

                # 💡 장기 메모리 섹션 추가
                ltm_section = ""
                if long_term_memory:
                    ltm_section = f"\n{long_term_memory}\n"

                prompt = f"""{self._format_setup()}

    {context}
    {stm_section}{ltm_section}
    챕터 {chapter.number}: {chapter.title} (분량: {chapter.word_count}단어, 목표: {min_words}~{max_words})

    내용 (샘플):
    {review_content}

    검토 주안점: 

    {short_term_memory}를 참조하여 다음을 평가하세요.

    1. **중복 방지** 
       - 같은 문장 구조나 표현이 과도하게 반복되지 않았는지
       - 같은 장면이나 상황이 재현되지 않았는지

    2. **문체 일관성**
       - 기술 방식 이외에도 서술체, 어미, 존칭 여부)가 작성된 내용 내에서, 그리고 이전 챕터들과 비교해 일관되는지 평가하세요.

    3. **플롯 일관성**: {long_term_memory}에 저장된 캐릭터 발전 상황 및 플롯 진행과 모순되는 점이 없는지 확인하세요.
       - 캐릭터의 기존 변화와 충돌하지 않는지
       - 이미 해결된 플롯을 다시 제기하지 않았는지

    4. **분량 밸런스**: 목표 단어 수 대비 적절한 분량인지, 내용이 너무 빈약하거나 과도하지 않은지 확인하세요.

    JSON 형식:
    {{
      "scores": {{"style": 8, "continuity": 7, "characters": 9, "plot": 8, "length_balance": 7}},
      "feedback": "문제점과 개선사항 (문자열)",
      "status": "승인" or "수정필요"
    }}"""

                response = self.client.generate(
                    model=self.config.editor_model,
                    prompt=prompt,
                    system=system_prompt,
                    temperature=self.config.editor_temperature,
                    format_json=True,
                    max_tokens=6000,
                )

                data = safe_json_parse(response)

                # 💡 안전한 데이터 추출
                scores = data.get("scores", {}) if isinstance(data, dict) else {}
                avg_score = np.mean(list(scores.values())) if scores else 0

                length_issue = ""
                if chapter.word_count < min_words:
                    length_issue = f" [⚠️ 분량 부족: {chapter.word_count}/{min_words}]"
                elif chapter.word_count > max_words:
                    length_issue = f" [⚠️ 분량 초과: {chapter.word_count}/{max_words}]"

                # --- 💡 오류 수정 지점 ---
                feedback_raw = data.get("feedback", "") if isinstance(data, dict) else ""
                feedback_text = ""

                if isinstance(feedback_raw, dict):
                    # feedback이 dict로 반환된 경우, JSON 문자열로 변환
                    print("  ⚠️ 편집자 피드백이 dict 형태로 반환되어 문자열로 변환합니다.")
                    feedback_text = json.dumps(feedback_raw, ensure_ascii=False)
                elif feedback_raw:
                    feedback_text = str(feedback_raw)  # 안전하게 str로 캐스팅
                else:
                    feedback_text = "피드백 없음."
                # --- 수정 완료 ---

                return {
                    'scores': list(scores.values()),
                    'average_score': float(avg_score),
                    'suggestions': [],
                    'status': data.get("status", "수정필요") if isinstance(data, dict) else "수정필요",
                    'feedback_text': feedback_text + length_issue  # 💡 이제 안전함
                }

            except AttributeError as e:
                print(f"  ⚠️ AttributeError 발생: {e}")
                import traceback
                traceback.print_exc()
                # 기본값 반환
                return {
                    'scores': [7.0],
                    'average_score': 7.0,
                    'suggestions': [],
                    'status': '수정필요',
                    'feedback_text': f'검토 중 오류 발생: {str(e)}'
                }

        review = _review()
        print(f"✓ 검토 완료 - 평균: {review['average_score']:.1f}/10")
        return review