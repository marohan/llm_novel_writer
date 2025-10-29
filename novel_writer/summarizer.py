from novel_writer.utils import retry_on_error, safe_json_parse

# Google Generative AI SDK import
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
except ImportError:
    print("⚠️ 'google-genai' 패키지가 설치되지 않았습니다. 'pip install google-genai numpy'를 실행하세요.")
    exit()

# ============================================================================
# 요약 생성기 (Summarizer)
# ============================================================================

class Summarizer:
    """챕터 요약 생성"""

    def __init__(self, client, config):
        self.client = client
        self.config = config

    def summarize_chapter(self, chapter):
        """챕터 요약 추출"""
        print(f"\n=== 챕터 {chapter.number} 요약 중 ===")

        @retry_on_error(self.config)
        def _summarize():
            system_prompt = "당신은 텍스트 분석 전문가입니다. JSON 형식으로 응답하세요."

            max_chars = 3000
            summary_content = chapter.content
            if len(summary_content) > max_chars:
                half = max_chars // 2
                summary_content = summary_content[:half] + "\n[생략]\n" + summary_content[-half:]

            prompt = f"""다음 챕터의 핵심 정보를 추출하세요.

챕터 {chapter.number}: {chapter.title}
{summary_content}

JSON 형식:
{{
  "summary": "4-5문장 요약",
  "key_events": ["사건1", "사건2"],
  "character_changes": {{"캐릭터명": "변화"}},
  "new_info": ["새로운 설정"]
}}"""

            response = self.client.generate(
                model=self.config.editor_model,
                prompt=prompt,
                system=system_prompt,
                temperature=self.config.summarizer_temperature,
                format_json=True
            )

            data = safe_json_parse(response)
            return {
                'summary': data.get('summary', ''),
                'key_events': data.get('key_events', []),
                'character_changes': data.get('character_changes', {}),
                'new_info': data.get('new_info', [])
            }

        summary_data = _summarize()
        print(f"✓ 요약 완료")
        return summary_data