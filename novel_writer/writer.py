from novel_writer.utils import retry_on_error, strip_reasoning, remove_duplicate_sentences, validate_content, count_words, safe_json_parse
from novel_writer.writer_config import Chapter

# ============================================================================
# Writer
# ============================================================================

class Writer:
    """실제 컨텐츠 작성"""

    def __init__(self, client, config, setup):
        self.client = client
        self.config = config
        self.setup = setup

    def _format_setup(self):
        chars = "\n".join([f"- {c['name']}: {c.get('description', '')}"
                           for c in self.setup.characters])
        return f"""시놉시스: {self.setup.synopsis}
문체: {self.setup.writing_style}
문체 예시: {self.setup.style_example}
캐릭터: {chars}
세계: {self.setup.world_setting}"""

    def write_chapter(self, chapter, context, target_words,
                      short_term_memory="",
                      long_term_memory="",
                      next_chapter_outline=None,
                      retry_count=0):
        """챕터 내용 작성 (단기+장기기억 포함)"""
        print(f"\n=== 챕터 {chapter.number} 작성 중 ===")

        min_words, max_words = target_words

        def _write():
            system_prompt = f"당신은 {self.setup.writing_style} 문체로 글을 쓰는 소설가입니다."

            if retry_count > 0:
                print(f"  📝 재작성 시도 {retry_count + 1}회차")

            next_chapter_prompt = "이 챕터가 마지막 챕터입니다."
            if next_chapter_outline:
                next_chapter_prompt = f"다음 챕터({chapter.number + 1}) 개요: {next_chapter_outline}"

            # 💡 단기기억이 있으면 맥락에 추가
            stm_section = ""
            if short_term_memory:
                stm_section = f"\n{short_term_memory}\n"

            # 💡 장기기억이 있으면 맥락에 추가
            ltm_section = ""
            if long_term_memory:
                ltm_section = f"\n{long_term_memory}\n"

            # 프롬프트 구성
            prompt = f"""{self._format_setup()}

        --- 맥락 정보 ---
        {context}
        ---
        {stm_section}{ltm_section}
        --- 현재 챕터 작성 임무 ---
        - 번호: {chapter.number}/{self.setup.target_chapters}
        - 제목: {chapter.title}
        - 개요: {chapter.outline}
        - {next_chapter_prompt}

         ⚠️ 필수 요구사항:
        1. 분량: {min_words}~{max_words}단어
        2. 문체: {self.setup.writing_style}(문체)와 {self.setup.style_example}(문체 예시)를 참고하세요.
        3. 현재 챕터 개요를 충실히 따르면서, 다음 챕터 개요로 자연스럽게 이어지도록 단서를 남기며 마무리하세요.
        4. 설정 및 캐릭터의 일관성을 유지하고 플롯 진행사항을 반영하세요.
        5. 완전한 장면과 대화를 포함한 실제 소설 내용 작성
        6. {short_term_memory}가 존재할 경우, 이의 문체와 어미, 존칭 일관성 유지 및 문장 반복 방지
        7. {self.setup.world_setting}의 세계관을 참고하세요.

        ⚠️ 출력 형식:
        - JSON 형식을 사용하지 마세요.
        - 서문이나 사족 없이 챕터 본문만 바로 작성하세요.
        - "여기 챕터입니다" 같은 메타 설명을 포함하지 마세요.
        - 사용자의 요청에 대한 최종 답변만을 텍스트로 제공합니다. '생각하는 과정', '추론', '단계' 등의 내용은 출력하지 마세요.

        챕터 {chapter.number} 전체 내용:"""

            estimated_tokens = int(max_words * 1.5)

            @retry_on_error(self.config)
            def _api_call():
                response = self.client.generate(
                    model=self.config.writer_model,
                    prompt=prompt,
                    system=system_prompt,
                    temperature=self.config.writer_temperature,
                    max_tokens=min(estimated_tokens, self.config.max_generation_tokens),
                )

                # 응답에서 텍스트 추출
                if hasattr(response, 'content'):
                    # API 응답이 객체 형태인 경우
                    content_raw = ""
                    for block in response.content:
                        if hasattr(block, 'type') and block.type == 'text':
                            content_raw += block.text
                    if not content_raw:
                        content_raw = str(response)
                else:
                    # API 응답이 문자열 형태인 경우
                    content_raw = str(response)

                # <think> 태그 제거
                content_stripped = strip_reasoning(content_raw)

                # 💡 JSON 형태 응답 파싱 추가
                content_parsed = self._parse_json_response(content_stripped)

                # 중복 문장 제거
                return remove_duplicate_sentences(content_parsed)

            return _api_call()

        content = _write()

        # 빈 내용 검증
        if not validate_content(content, min_words):
            print(f"⚠️ 생성된 내용이 부족합니다. (단어수: {count_words(content)})")
            if retry_count < 2:  # 최대 2회 재시도
                print(f"   재작성을 시도합니다...")
                import time
                time.sleep(2)
                return self.write_chapter(chapter, context, target_words,
                                          short_term_memory, long_term_memory,
                                          next_chapter_outline, retry_count + 1)
            else:
                print(f"   ⚠️ 재시도 횟수 초과. 현재 내용으로 진행합니다.")

        word_count = count_words(content)
        print(f"✓ 초안 완성: {word_count}단어 (목표: {min_words}~{max_words})")

        chapter.word_count = word_count
        return content

    def refine_chapter(self, chapter, feedback, target_words):
        """챕터 내용 수정"""
        print(f"\n=== 챕터 {chapter.number} 수정 중 ===")

        min_words, max_words = target_words

        @retry_on_error(self.config)
        def _refine():
            needs_full_rewrite = (
                    chapter.word_count < min_words * 0.8 or
                    chapter.word_count > max_words * 1.2
            )

            system_prompt = f"당신은 {self.setup.writing_style} 문체로 글을 쓰는 소설가입니다."

            # 💡 feedback이 dict인지 string인지 확인
            if isinstance(feedback, dict):
                feedback_text = feedback.get('feedback_text', str(feedback))
            else:
                feedback_text = str(feedback)

            if needs_full_rewrite:
                print(f"  분량 문제로 전체 재작성 ({chapter.word_count} → {min_words}~{max_words})")

                max_chars = 2000
                review_content = chapter.content
                if len(review_content) > max_chars:
                    half = max_chars // 2
                    review_content = review_content[:half] + "\n[생략]\n" + review_content[-half:]

                prompt = f"""다음 챕터를 분량 조절하여 재작성하세요.

    원본 (요약):
    {review_content}

    피드백: {feedback_text}

    ⚠️ 필수: 
    1. {min_words}~{max_words}단어
    2. 중복 금지, 완전한 서사 작성
    3. 문체: {self.setup.writing_style}

    ⚠️ 출력 형식:
     - 서문, 사족, "여기 챕터입니다" 같은 말을 모두 생략하세요.
     - JSON 형식을 사용하지 마세요.
     - 사용자의 요청에 대한 최종 답변만을 텍스트로 제공합니다. '생각하는 과정', '추론', '단계' 등의 내용은 출력하지 마세요.
     - 오직 챕터 {chapter.number}의 본문 내용만 처음부터 끝까지 작성하세요.

    수정된 전체 내용:"""

                refined_raw = self.client.generate(
                    model=self.config.writer_model,
                    prompt=prompt,
                    system=system_prompt,
                    temperature=self.config.writer_temperature,
                    max_tokens=min(int(max_words * 1.5), self.config.max_generation_tokens),
                )
            else:
                print(f"  피드백 반영 수정")

                max_chars = 3000
                review_content = chapter.content
                if len(review_content) > max_chars:
                    half = max_chars // 2
                    review_content = review_content[:half] + "\n[생략]\n" + review_content[-half:]

                prompt = f"""다음 챕터를 피드백에 따라 수정하세요.

    원본:
    {review_content}

    피드백: {feedback_text}

    ⚠️ 필수:
    1. 현재 분량 유지, 품질 개선
    2. 문체: {self.setup.writing_style}

    ⚠️ 출력 형식: 
     - 서문, 사족 생략
     - JSON 형식 사용 금지
     - 본문만 바로 작성

    수정된 내용:"""

                refined_raw = self.client.generate(
                    model=self.config.writer_model,
                    prompt=prompt,
                    system=system_prompt,
                    temperature=self.config.writer_temperature,
                    max_tokens=min(int(chapter.word_count * 1.5), self.config.max_generation_tokens),
                )

            refined_stripped = strip_reasoning(refined_raw)

            # 💡 JSON 형태 응답 파싱 추가
            refined_parsed = self._parse_json_response(refined_stripped)

            return remove_duplicate_sentences(refined_parsed)

        refined = _refine()
        new_word_count = count_words(refined)
        print(f"✓ 수정 완료: {chapter.word_count} → {new_word_count}단어")
        chapter.word_count = new_word_count

        return refined

    def _parse_json_response(self, content):
        """
        💡 JSON 형태로 반환된 응답을 파싱하여 본문만 추출
        """
        import json
        import re

        content_trimmed = content.strip()

        # JSON 형태인지 확인
        if content_trimmed.startswith('{'):
            try:
                # 완전한 JSON 객체 찾기 시도
                json_match = re.search(r'\{[\s\S]*"content"[\s\S]*:\s*"([\s\S]*?)"\s*\}', content_trimmed)
                if json_match:
                    # 정규식으로 content 값 추출
                    extracted_content = json_match.group(1)
                    # 이스케이프 문자 복원
                    extracted_content = extracted_content.replace('\\"', '"').replace('\\n', '\n')
                    print("  ℹ️ JSON 형태 응답을 본문으로 변환했습니다.")
                    return extracted_content

                # 정규식 실패 시 JSON 파싱 시도
                # 불완전한 JSON도 처리하기 위해 마지막 } 이전까지만 파싱
                last_brace = content_trimmed.rfind('}')
                if last_brace != -1:
                    json_str = content_trimmed[:last_brace + 1]
                    parsed = json.loads(json_str)

                    if isinstance(parsed, dict) and 'content' in parsed:
                        print("  ℹ️ JSON 형태 응답을 본문으로 변환했습니다.")
                        return parsed['content']

            except (json.JSONDecodeError, AttributeError) as e:
                print(f"  ⚠️ JSON 파싱 실패, 원본 반환: {str(e)[:100]}")

                # JSON 형태지만 파싱 실패한 경우, content 필드만 수동 추출 시도
                content_match = re.search(r'"content"\s*:\s*"([^"]*(?:"[^"]*)*)"', content_trimmed, re.DOTALL)
                if content_match:
                    print("  ℹ️ 정규식으로 content 추출 성공")
                    return content_match.group(1).replace('\\"', '"').replace('\\n', '\n')

        # JSON이 아니거나 모든 파싱 실패 시 원본 반환
        return content_trimmed

    def refine_structure(self, chapters, feedback):
        """챕터 구조 수정"""
        print("\n=== 챕터 구조 수정 중 ===")

        if feedback['status'] == '승인':
            return chapters

        import json
        @retry_on_error(self.config)
        def _refine():
            system_prompt = "당신은 창의적인 소설 작가입니다. JSON 형식으로 응답하세요."

            chapters_data = [{"number": ch.number, "title": ch.title, "outline": ch.outline}
                             for ch in chapters]

            prompt = f"""다음 챕터 구조를 피드백에 따라 수정하세요.

현재 구조:
{json.dumps(chapters_data, ensure_ascii=False, indent=2)}

피드백: {feedback['feedback_text']}

개선 제안:
{chr(10).join(feedback['suggestions'])}

JSON 형식:
{{
  "chapters": [
    {{"number": 1, "title": "제목", "outline": "개요"}},
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
            refined = []

            for ch_data in data.get("chapters", []):
                refined.append(Chapter(
                    number=ch_data["number"],
                    title=ch_data["title"],
                    outline=ch_data["outline"]
                ))

            return refined

        refined = _refine()
        print(f"✓ 구조 수정 완료")
        return refined