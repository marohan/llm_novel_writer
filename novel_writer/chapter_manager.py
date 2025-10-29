from typing import List, Dict, Optional, Tuple
import re
import numpy as np
from novel_writer.writer_config import Chapter

# ============================================================================
# 챕터 관리자
# ============================================================================

class ChapterManager:
    """챕터 목록 및 요약 관리 클래스"""

    # def __init__(self, characters: List[Dict]):
    #     self.characters = characters
    #     self.memory = []  # 💡 반드시 list로 초기화
    #     self.character_development = {}
    #     self.plot_threads = {}
    #     self.world_events = []
    #
    #     # 캐릭터별 초기화
    #     for char in characters:
    #         char_name = char.get('name', '')
    #         if char_name:
    #             self.character_development[char_name] = []

    def __init__(self):
        self.chapters = []

    def add_chapter(self, chapter: Chapter):
        self.chapters.append(chapter)

    def get_chapter(self, number: int) -> Optional[Chapter]:
        for ch in self.chapters:
            if ch.number == number:
                return ch
        return None

    def get_recent_chapters(self, current_number: int, count: int) -> List[Chapter]:
        start_idx = max(0, current_number - 1 - count)
        return self.chapters[start_idx: current_number - 1]

    def get_completed_chapters(self) -> List[Chapter]:
        return [ch for ch in self.chapters if ch.content]

    def get_completion_rate(self) -> Tuple[int, int]:
        completed = len(self.get_completed_chapters())
        total = len(self.chapters)
        return completed, total

    def set_chapters(self, chapters: List[Chapter]):
        self.chapters = sorted(chapters, key=lambda c: c.number)

    def build_context(self, current_number: int, recent_count: int,
                      memory_summary: str, global_outline_context: str) -> str:
        """이전 챕터 맥락 구성 (스타일 프라이밍 및 개요 포함)"""
        if current_number == 1:
            return f"이 소설의 첫 번째 챕터입니다.\n\n장기 기억:\n{memory_summary}\n\n{global_outline_context}"

        context_parts = []
        recent = self.get_recent_chapters(current_number, recent_count)

        # 1. 스타일 프라이밍을 위한 직전 챕터 마지막 단락 추가
        if recent:
            last_chapter = recent[-1]
            if last_chapter.content:
                last_passage = re.sub(r'\n+', '\n', last_chapter.content.strip())[-500:]
                context_parts.append("--- 이전 챕터 마지막 단락 (문체 참고) ---")
                context_parts.append(f"[...{last_passage}]")

        # 2. 장기 기억
        context_parts.append("\n--- 장기 기억 (핵심 플롯/설정) ---")
        context_parts.append(memory_summary)

        # 3. 전체 개요
        context_parts.append(global_outline_context)

        return "\n".join(context_parts)

    def build_short_term_memory(self, current_number: int,
                                stm_chapter_count: int,
                                max_chars: int) -> str:
        """💡 단기기억 생성: 앞 n개 챕터의 전체 내용 (중복 방지용)"""
        # 💡 첫 번째 챕터거나 이전 챕터가 없으면 빈 문자열 반환
        if current_number <= 1:
            return ""

        # 앞 n개 챕터 가져오기
        start_idx = max(0, current_number - 1 - stm_chapter_count)
        end_idx = current_number - 1
        recent_chapters = self.chapters[start_idx:end_idx]

        if not recent_chapters:
            return ""

        # 챕터별 내용 결합 (내용이 있는 것만)
        stm_parts = ["=== 단기기억 (최근 챕터 내용 - 중복 방지용) ==="]
        content_found = False

        for ch in recent_chapters:
            if not ch.content or not ch.content.strip():
                continue

            content_found = True
            stm_parts.append(f"\n[챕터 {ch.number}: {ch.title}]")
            stm_parts.append(ch.content)

        # 💡 내용이 있는 챕터가 하나도 없으면 빈 문자열 반환
        if not content_found:
            return ""

        full_stm = "\n".join(stm_parts)

        # 💡 최대 문자 수 제한 (토큰 제한 대응)
        if len(full_stm) > max_chars:
            # 뒷부분 n자만 잘라서 사용
            truncated = full_stm[-max_chars:]
            print(f"  📝 단기기억이 {len(full_stm)}자로 너무 길어 뒷부분 {max_chars}자만 사용합니다.")
            return f"=== 단기기억 (최근 {max_chars}자) ===\n[...앞부분 생략...]\n{truncated}"

        return full_stm

    def get_global_outline_context(self, current_number: int) -> str:
        """전체 소설 개요 '지도' 생성"""
        parts = ["\n--- 전체 소설 개요 (현재 위치: ▶) ---"]
        for ch in self.chapters:
            marker = "▶" if ch.number == current_number else " "

            if ch.content:
                status = "(작성 완료)"
                details = ch.summary if ch.summary else ch.outline
                details = (details[:100] + '...') if len(details) > 100 else details
            else:
                status = "(작성 예정)"
                details = ch.outline

            parts.append(f" {marker} Ch{ch.number} '{ch.title}' {status}: {details}")

        return "\n".join(parts)

    def get_average_word_count(self, up_to_chapter: int) -> Optional[float]:
        completed = [ch for ch in self.chapters
                     if ch.number < up_to_chapter and ch.word_count > 0]
        if completed:
            return np.mean([ch.word_count for ch in completed])
        return None

    def print_length_report(self):
        """분량 균형 리포트 출력"""
        print("\n" + "=" * 60)
        print("챕터 분량 분석")
        print("=" * 60)

        word_counts = [ch.word_count for ch in self.chapters if ch.word_count > 0]
        if not word_counts:
            print("완성된 챕터가 없습니다.")
            return

        avg = np.mean(word_counts)
        std = np.std(word_counts)

        print(f"평균: {avg:.0f}단어")
        print(f"표준편차: {std:.0f}단어")
        print(f"범위: {min(word_counts)} ~ {max(word_counts)}단어")
        print("\n챕터별:")
        for ch in self.chapters:
            if ch.word_count > 0:
                diff = ch.word_count - avg
                status = "✓" if abs(diff) < avg * 0.2 else "⚠️"
                print(f"  {status} Ch{ch.number}: {ch.word_count}단어 ({diff:+.0f})")