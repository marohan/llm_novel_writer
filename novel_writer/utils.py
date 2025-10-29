import requests
import json
from typing import List, Dict, Tuple
import time
import re
from functools import wraps
from novel_writer.writer_config import WriterConfig
from novel_writer.client_setup import GeminiClient
import numpy as np

# ============================================================================
# Utility Functions
# ============================================================================

def count_words(text: str) -> int:
    """단어 수 계산 (한글/영어 혼용)"""
    korean = re.findall(r'[가-힣]+', text)
    english = re.findall(r'[a-zA-Z]+', text)
    return len(''.join(korean)) + len(english)


def retry_on_error(config: WriterConfig):
    """개선된 재시도 데코레이터 - Rate Limit 별도 처리"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries):
                try:
                    return func(*args, **kwargs)

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        print(f"\n⚠️ Rate Limit 감지 (429)")

                        for rate_attempt in range(config.rate_limit_max_retries):
                            wait_time = config.rate_limit_delay * (rate_attempt + 1)
                            print(f"   {wait_time}초 대기 후 재시도 ({rate_attempt + 1}/{config.rate_limit_max_retries})...")
                            time.sleep(wait_time)

                            try:
                                return func(*args, **kwargs)
                            except requests.exceptions.HTTPError as retry_e:
                                if retry_e.response.status_code != 429:
                                    raise retry_e
                                if rate_attempt == config.rate_limit_max_retries - 1:
                                    print(f"   ❌ Rate Limit 재시도 횟수 초과")
                                    raise RuntimeError(
                                        f"Rate Limit 초과: 최대 {config.rate_limit_max_retries}회 재시도 실패") from retry_e
                            except Exception as retry_e:
                                raise retry_e

                    last_exception = e
                    if attempt < config.max_retries - 1:
                        wait_time = config.retry_delay * (attempt + 1)
                        print(
                            f"⚠️ HTTP 오류: {e.response.status_code}. {wait_time}초 후 재시도 ({attempt + 1}/{config.max_retries})...")
                        time.sleep(wait_time)

                except Exception as e:
                    last_exception = e
                    if attempt < config.max_retries - 1:
                        wait_time = config.retry_delay * (attempt + 1)
                        print(f"⚠️ 오류 발생: {e}. {wait_time}초 후 재시도 ({attempt + 1}/{config.max_retries})...")
                        time.sleep(wait_time)

            raise last_exception

        return wrapper

    return decorator


def safe_json_parse(text: str) -> Dict:
    """안전한 JSON 파싱"""
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group(0)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        text = text.replace("'", '"')
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        return json.loads(text)


def remove_duplicate_sentences(text: str) -> str:
    """중복된 연속 문장 제거"""
    lines = text.split('\n')
    cleaned_lines = []
    prev_line = None
    consecutive_count = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            prev_line = None
            consecutive_count = 0
            continue

        if prev_line and stripped == prev_line:
            consecutive_count += 1
            if consecutive_count >= 2:
                print(f"  ⚠️ 중복 문장 제거: {stripped[:50]}...")
                continue
        else:
            consecutive_count = 0

        cleaned_lines.append(line)
        prev_line = stripped

    return '\n'.join(cleaned_lines)


def validate_content(content: str, min_words: int) -> bool:
    """생성된 내용 검증"""
    if not content or not content.strip():
        return False

    word_count = count_words(content)
    if word_count < min_words * 0.3:
        return False

    return True


def strip_reasoning(text: str) -> str:
    """모델 응답에서 불필요한 서문(reasoning) 제거"""

    patterns = [
        r"^[^\n]*?:\s*\n",
        r"^물론이죠[^\n]*?\n",
        r"^요청하신[^\n]*?\n",
        r"^다음은[^\n]*?\n",
        r'<think>.*?</think>'
    ]

    cleaned_text = text.strip()

    for pattern in patterns:
        cleaned_text = re.sub(pattern, "", cleaned_text, count=1, flags=re.IGNORECASE)

    cleaned_text = re.sub(r"^```[a-z]*\n(.*?)\n```$", r"\1", cleaned_text, flags=re.DOTALL)

    return cleaned_text.strip()


# ============================================================================
# Embedding Verifier
# ============================================================================

class EmbeddingVerifier:
    """임베딩 기반 피드백 반영 검증"""

    def __init__(self, client: GeminiClient):
        self.client = client

    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        if len(v1) == 0 or len(v2) == 0:
            return 0.0
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    @staticmethod
    def extract_feedback_points(feedback_text: str) -> List[str]:
        lines = feedback_text.split('\n')
        points = []

        for line in lines:
            line = line.strip()
            if re.match(r'^\d+[\.\)]\s+', line) or line.startswith('- '):
                cleaned = re.sub(r'^\d+[\.\)]\s+|-\s+', '', line)
                if len(cleaned) > 10:
                    points.append(cleaned)

        if not points:
            sentences = re.split(r'[.!?]\s+', feedback_text)
            points = [s.strip() for s in sentences if len(s.strip()) > 20][:5]

        return points

    def verify_revision(self, old_content: str, new_content: str,
                        feedback_text: str, threshold: float = 0.6) -> Tuple[bool, float]:
        if not feedback_text:
            return True, 1.0

        feedback_points = self.extract_feedback_points(feedback_text)
        if not feedback_points:
            return True, 0.5

        old_lines = set(old_content.split('\n'))
        new_lines = set(new_content.split('\n'))
        changed_lines = new_lines - old_lines
        changed_text = '\n'.join(changed_lines)

        if not changed_text.strip():
            return False, 0.0

        similarities = []
        for point in feedback_points[:5]:
            try:
                feedback_emb = self.client.get_embedding(point)
                changed_emb = self.client.get_embedding(changed_text)
                sim = self.cosine_similarity(feedback_emb, changed_emb)
                similarities.append(sim)
            except Exception:
                continue

        if not similarities:
            return False, 0.0

        avg_similarity = float(np.mean(similarities))
        return avg_similarity >= threshold, avg_similarity