from typing import List, Dict, Optional, Tuple
from novel_writer.client_setup import GroqClient
from novel_writer.writer_config import WriterConfig, NovelSetup
from novel_writer.chapter_manager import ChapterManager
from novel_writer.utils import retry_on_error, safe_json_parse

# ============================================================================
# Memory Manager
# ============================================================================

class NovelMemoryManager:
    """장기 메모리 관리"""

    def __init__(self, characters: List[Dict]):
        self.characters = characters
        self.memory = []

        # 💡 필수 속성 초기화
        self.character_development = {}  # 캐릭터별 발전 사항
        self.plot_threads = {}  # 플롯 스레드
        self.world_events = []  # 세계 사건

        # 캐릭터별 초기화
        for char in characters:
            char_name = char.get('name', '')
            if char_name:
                self.character_development[char_name] = []

    def to_dict(self) -> Dict:
        """메모리를 딕셔너리로 변환"""
        return {
            'memory': self.memory,
            'character_development': self.character_development,
            'plot_threads': self.plot_threads,
            'world_events': self.world_events
        }

    def from_dict(self, data: Dict):
        """딕셔너리에서 메모리 복원"""
        self.memory = data.get('memory', [])

        # 💡 안전하게 복원 (키가 없으면 빈 dict/list로 초기화)
        self.character_development = data.get('character_development', {})
        self.plot_threads = data.get('plot_threads', {})
        self.world_events = data.get('world_events', [])

        # 💡 타입 검증
        if not isinstance(self.character_development, dict):
            self.character_development = {}
        if not isinstance(self.plot_threads, (dict, list)):
            self.plot_threads = {}
        if not isinstance(self.world_events, list):
            self.world_events = []

    def update_from_summary(self, summary_data: Dict):
        """요약 데이터로 메모리 업데이트"""
        try:
            # 메모리에 요약 추가
            summary_text = summary_data.get('summary', '')
            if summary_text:
                self.memory.append(summary_text)

            # 캐릭터 변화 업데이트
            char_changes = summary_data.get('character_changes', {})
            for char_name, change in char_changes.items():
                if char_name not in self.character_development:
                    self.character_development[char_name] = []

                if isinstance(self.character_development[char_name], list):
                    self.character_development[char_name].append(change)
                else:
                    self.character_development[char_name] = [change]

            # 플롯 스레드 업데이트
            new_info = summary_data.get('new_info', [])
            key_events = summary_data.get('key_events', [])

            # plot_threads를 dict로 통일
            if not isinstance(self.plot_threads, dict):
                self.plot_threads = {}

            for info in new_info:
                if info and info not in self.plot_threads:
                    self.plot_threads[info] = "진행 중"

            for event in key_events:
                if event and event not in self.plot_threads:
                    self.plot_threads[event] = "발생함"

        except Exception as e:
            print(f"  ⚠️ update_from_summary 내부 오류: {e}")
            import traceback
            traceback.print_exc()

    def get_summary(self, max_length: int = 2000) -> str:
        """메모리 요약 반환"""
        try:
            # 💡 self.memory가 list인지 확인
            if not hasattr(self, 'memory'):
                return ""

            if not isinstance(self.memory, list):
                print(f"  ⚠️ memory가 list가 아닙니다: {type(self.memory)}")
                # dict인 경우 리스트로 변환 시도
                if isinstance(self.memory, dict):
                    memory_list = list(self.memory.values())
                else:
                    return ""
            else:
                memory_list = self.memory

            if not memory_list:
                return ""

            # 최근 메모리부터 역순으로
            recent_memories = memory_list[-5:] if len(memory_list) > 5 else memory_list

            # 문자열로 변환 (리스트 항목이 dict일 수도 있음)
            summary_parts = []
            for mem in recent_memories:
                if isinstance(mem, str):
                    summary_parts.append(mem)
                elif isinstance(mem, dict):
                    # dict인 경우 summary 키 찾기
                    summary_parts.append(mem.get('summary', str(mem)))
                else:
                    summary_parts.append(str(mem))

            summary = "\n".join(summary_parts)

            if len(summary) > max_length:
                summary = summary[-max_length:]

            return summary

        except Exception as e:
            print(f"  ⚠️ get_summary 오류: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def to_dict(self) -> Dict:
        """메모리를 딕셔너리로 변환"""
        # 💡 올바른 구현
        return {
            'memory': self.memory if hasattr(self, 'memory') else [],
            'character_development': self.character_development if hasattr(self, 'character_development') else {},
            'plot_threads': self.plot_threads if hasattr(self, 'plot_threads') else {},
            'world_events': self.world_events if hasattr(self, 'world_events') else []
        }

    def from_dict(self, data: Dict):
        """딕셔너리에서 메모리 복원"""
        # 💡 안전하게 복원
        self.memory = data.get('memory', [])
        if not isinstance(self.memory, list):
            print(f"  ⚠️ 복원된 memory가 list가 아닙니다. 빈 리스트로 초기화합니다.")
            self.memory = []

        self.character_development = data.get('character_development', {})
        if not isinstance(self.character_development, dict):
            self.character_development = {}

        self.plot_threads = data.get('plot_threads', {})
        if not isinstance(self.plot_threads, (dict, list)):
            self.plot_threads = {}

        self.world_events = data.get('world_events', [])
        if not isinstance(self.world_events, list):
            self.world_events = []

# ============================================================================
# Long Term Memory Optimizer
# ============================================================================

class LongTermMemoryOptimizer:
    """
    장기 메모리를 최적화하여 토큰 사용량을 관리합니다.
    - 완결된 플롯 스레드 제거
    - 일시적 캐릭터 변화 통합
    - 향후 전개와 무관한 내용 제거
    """

    def __init__(self, client: GroqClient, config: WriterConfig, setup: NovelSetup):
        self.client = client
        self.config = config
        self.setup = setup

    def optimize_memory(self,
                        memory_manager: NovelMemoryManager,
                        chapter_manager: ChapterManager,
                        current_chapter_number: int) -> Dict:
        """
        장기 메모리를 최적화합니다.

        Args:
            memory_manager: 메모리 관리 객체
            chapter_manager: 챕터 관리 객체
            current_chapter_number: 현재까지 작성된 챕터 번호

        Returns:
            최적화 결과 통계
        """
        print(f"\n{'=' * 60}")
        print(f"🧠 장기 메모리 최적화 시작 (챕터 {current_chapter_number} 완료 시점)")
        print(f"{'=' * 60}")

        # 현재 메모리 상태 추출
        memory_dict = memory_manager.to_dict()
        original_char_dev = memory_dict.get('character_development', {})
        original_plot_threads = memory_dict.get('plot_threads', {})

        # 통계
        original_char_count = sum(len(events) for events in original_char_dev.values())
        original_plot_count = len(original_plot_threads) if isinstance(original_plot_threads, dict) else len(
            original_plot_threads)

        print(f"📊 현재 상태:")
        print(f"  - 캐릭터 발전 이벤트: {original_char_count}개")
        print(f"  - 플롯 스레드: {original_plot_count}개")

        # 남은 챕터 정보 수집
        remaining_chapters = self._get_remaining_chapters(chapter_manager, current_chapter_number)

        # LLM을 통한 최적화
        optimized_data = self._optimize_with_llm(
            original_char_dev,
            original_plot_threads,
            remaining_chapters,
            current_chapter_number
        )

        # 메모리 업데이트
        if optimized_data:
            memory_dict['character_development'] = optimized_data.get('character_development', original_char_dev)
            memory_dict['plot_threads'] = optimized_data.get('plot_threads', original_plot_threads)
            memory_manager.from_dict(memory_dict)

            # 최적화 후 통계
            new_char_count = sum(len(events) for events in optimized_data.get('character_development', {}).values())
            new_plot_count = len(optimized_data.get('plot_threads', {}))

            reduction_char = original_char_count - new_char_count
            reduction_plot = original_plot_count - new_plot_count

            print(f"\n✅ 최적화 완료:")
            print(f"  - 캐릭터 이벤트: {original_char_count} → {new_char_count} (△{reduction_char})")
            print(f"  - 플롯 스레드: {original_plot_count} → {new_plot_count} (△{reduction_plot})")

            return {
                'success': True,
                'character_events_removed': reduction_char,
                'plot_threads_removed': reduction_plot,
                'original_char_count': original_char_count,
                'new_char_count': new_char_count,
                'original_plot_count': original_plot_count,
                'new_plot_count': new_plot_count
            }
        else:
            print("⚠️ 최적화 실패. 원본 메모리 유지")
            return {'success': False}

    def _get_remaining_chapters(self, chapter_manager: ChapterManager, current_number: int) -> str:
        """남은 챕터들의 개요를 텍스트로 반환"""
        remaining = []
        for ch in chapter_manager.chapters:
            if ch.number > current_number:
                remaining.append(f"챕터 {ch.number}: {ch.title} - {ch.outline}")

        if not remaining:
            return "남은 챕터 없음 (마지막 챕터 완료)"

        return "\n".join(remaining)

    def _optimize_with_llm(self,
                           char_dev: Dict,
                           plot_threads: any,
                           remaining_chapters: str,
                           current_chapter: int) -> Dict:
        """LLM을 사용하여 메모리 최적화"""

        @retry_on_error(self.config)
        def _optimize():
            system_prompt = """당신은 소설의 장기 메모리를 효율적으로 관리하는 전문가입니다.
향후 플롯 전개에 영향을 주지 않으면서 불필요한 정보를 제거하거나 통합하세요.
반드시 JSON 형식으로 응답하세요."""

            # 캐릭터 발전 포맷팅
            char_dev_text = ""
            if char_dev:
                char_dev_text = "\n".join([
                    f"- {char}: {', '.join(events)}"
                    for char, events in char_dev.items()
                ])

            # 플롯 스레드 포맷팅
            plot_text = ""
            if isinstance(plot_threads, dict):
                plot_text = "\n".join([
                    f"- {thread}: {status}"
                    for thread, status in plot_threads.items()
                ])
            elif isinstance(plot_threads, list):
                plot_text = "\n".join([f"- {item}" for item in plot_threads])

            prompt = f"""현재 챕터 {current_chapter}까지 작성 완료. 장기 메모리를 최적화하세요.

=== 전체 소설 설정 ===
시놉시스: {self.setup.synopsis}
총 챕터 수: {self.setup.target_chapters}

=== 남은 챕터 개요 ===
{remaining_chapters}

=== 현재 장기 메모리 ===

[캐릭터 발전]
{char_dev_text}

[플롯 스레드]
{plot_text}

=== 최적화 지침 ===
1. **완결된 플롯 제거**: 이미 해결되어 향후 전개에 영향 없는 플롯 스레드 삭제
2. **일시적 변화 통합**: 캐릭터의 일시적 감정/상태 변화는 중요한 것만 남기고 통합
3. **중요 정보 보존**: 향후 챕터에서 참조될 가능성이 있는 내용은 반드시 유지
4. **간결화**: 비슷한 내용은 하나로 통합, 중복 제거

⚠️ 주의사항:
- 남은 챕터 개요를 반드시 참고하여 향후 필요한 정보는 삭제하지 마세요
- 캐릭터당 최대 {self.config.ltm_max_character_events}개 이벤트로 제한
- 플롯 스레드는 최대 {self.config.ltm_max_plot_threads}개로 제한
- 완전히 해결되지 않은 플롯은 유지

JSON 형식으로 응답:
{{
  "character_development": {{
    "캐릭터명": ["중요 발전1", "중요 발전2", ...]
  }},
  "plot_threads": {{
    "플롯명": "현재 상태"
  }},
  "removed_items": {{
    "removed_character_events": ["제거된 이벤트1", ...],
    "removed_plot_threads": ["제거된 플롯1", ...],
    "reason": "제거/통합 이유 설명"
  }}
}}"""

            response = self.client.generate(
                model=self.config.editor_model,  # editor 모델 사용
                prompt=prompt,
                system=system_prompt,
                temperature=self.config.ltm_optimizer_temperature,
                format_json=True,
                max_tokens=6000
            )

            data = safe_json_parse(response)

            # 결과 검증
            if not data or not isinstance(data, dict):
                print("  ⚠️ 최적화 결과가 올바르지 않습니다.")
                return None

            # 제거된 항목 로깅
            removed = data.get('removed_items', {})
            if removed:
                removed_char = removed.get('removed_character_events', [])
                removed_plot = removed.get('removed_plot_threads', [])
                reason = removed.get('reason', '')

                if removed_char or removed_plot:
                    print(f"\n📝 최적화 상세:")
                    if removed_char:
                        print(f"  제거된 캐릭터 이벤트: {len(removed_char)}개")
                        for item in removed_char[:3]:  # 처음 3개만 출력
                            print(f"    - {item}")
                    if removed_plot:
                        print(f"  제거된 플롯: {len(removed_plot)}개")
                        for item in removed_plot[:3]:
                            print(f"    - {item}")
                    if reason:
                        print(f"  이유: {reason[:150]}...")

            return data

        return _optimize()

    def should_optimize(self, current_chapter_number: int) -> bool:
        """현재 챕터에서 최적화를 수행해야 하는지 판단"""
        if not self.setup.enable_ltm_optimization:
            return False

        # 설정된 간격마다 최적화
        if current_chapter_number % self.config.ltm_optimization_interval == 0:
            return True

        return False