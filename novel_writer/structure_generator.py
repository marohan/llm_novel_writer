from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod
from novel_writer.writer_config import Chapter, NovelSetup, WriterConfig
from novel_writer.client_setup import GroqClient
from novel_writer.utils import retry_on_error, safe_json_parse

# ============================================================================
# 컨텐츠 생성기 (추상 클래스)
# ============================================================================

class ContentGenerator(ABC):
    """컨텐츠 생성 추상 클래스"""

    def __init__(self, client: GroqClient, config: WriterConfig, setup: NovelSetup):
        self.client = client
        self.config = config
        self.setup = setup

    @abstractmethod
    def generate(self, *args, **kwargs):
        pass

    def _format_characters(self) -> str:
        return "\n".join([f"- {c['name']}: {c.get('description', '')}"
                          for c in self.setup.characters])

    def _format_setup(self) -> str:
        return f"""시놉시스: {self.setup.synopsis}
문체: {self.setup.writing_style}
문체 예시: {self.setup.style_example}
캐릭터: {self._format_characters()}
세계: {self.setup.world_setting}"""

# ============================================================================
# 구조 생성기
# ============================================================================

class StructureGenerator(ContentGenerator):
    """챕터 구조 생성"""

    def generate(self) -> List[Chapter]:
        print("\n=== 챕터 구조 생성 중 ===")

        @retry_on_error(self.config)
        def _generate():
            system_prompt = "당신은 창의적인 소설 작가입니다. 반드시 JSON 형식으로 응답하세요."

            prompt = f"""다음 소설 설정으로 {self.setup.target_chapters}개 챕터 구조를 만드세요.

{self._format_setup()}

각 챕터는 비슷한 분량(약 {self.setup.target_words_per_chapter}단어)으로 균형있게 배분하세요.

JSON 형식:
{{
  "chapters": [
    {{"number": 1, "title": "제목", "outline": "2-3문장 개요"}},
    ...
  ]
}}"""

            response = self.client.generate(
                model=self.config.writer_model,
                prompt=prompt,
                system=system_prompt,
                temperature=self.config.writer_temperature,
                format_json=True
            )

            data = safe_json_parse(response)
            chapters = []

            for ch_data in data.get("chapters", []):
                chapters.append(Chapter(
                    number=ch_data["number"],
                    title=ch_data["title"],
                    outline=ch_data["outline"]
                ))

            return chapters

        chapters = _generate()
        print(f"✓ 챕터 구조 생성 완료: {len(chapters)}개")
        return chapters