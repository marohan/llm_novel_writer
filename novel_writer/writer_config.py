from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

# ============================================================================
# 설정 클래스들
# ============================================================================

@dataclass
class NovelSetup:
    """소설 기본 설정"""
    synopsis: str
    writing_style: str
    style_example: str
    characters: List[Dict[str, str]]
    world_setting: str
    target_chapters: int
    target_words_per_chapter: int = 2000
    words_tolerance: float = 0.4

    # 💡 단기기억 설정 추가
    short_term_memory_chapters: int = 3  # 기억할 챕터 수
    short_term_memory_max_chars: int = 8000  # 단기기억 최대 문자 수 (토큰 제한 대응)

    # 💡 장기 메모리 최적화 활성화 여부
    enable_ltm_optimization: bool = True


@dataclass
class WriterConfig:
    """작가 설정 - API 호출 및 동작 관련"""
    # API 설정
    api_key: str
    writer_model: str = "llama3-8b-8192"
    editor_model: str = "llama3-70b-8192"
    embedding_model: str = "nomic-embed-text"

    # 토큰 설정
    max_generation_tokens: int = 6000
    max_review_tokens: int = 7000

    # 재시도 설정
    max_retries: int = 5
    retry_delay: float = 30.0
    rate_limit_max_retries: int = 10
    rate_limit_delay: float = 60.0

    # 자동 저장 설정
    auto_save_interval: int = 1

    # 컨텍스트 설정
    recent_context_chapters: int = 2
    memory_max_length: int = 10000

    # 수정 설정
    max_refinement_rounds: int = 2
    approval_score_threshold: float = 7.5

    # Temperature 설정
    writer_temperature: float = 0.8
    editor_temperature: float = 0.5
    summarizer_temperature: float = 0.3

    # 💡 장기 메모리 최적화 관련 설정
    ltm_optimization_interval: int = 10  # n개 챕터마다 장기 메모리 최적화
    ltm_max_character_events: int = 10  # 캐릭터당 최대 이벤트 수
    ltm_max_plot_threads: int = 15  # 최대 플롯 스레드 수
    ltm_optimizer_temperature: float = 0.3  # 최적화 시 LLM 온도


@dataclass
class Chapter:
    """챕터 정보"""
    number: int
    title: str
    outline: str
    content: str = ""
    summary: str = ""
    key_events: List[str] = field(default_factory=list)
    word_count: int = 0