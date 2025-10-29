import requests
from typing import List, Dict, Optional, Tuple
import numpy as np
from novel_writer.writer_config import WriterConfig

# Google Generative AI SDK import
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
except ImportError:
    print("⚠️ 'google-genai' 패키지가 설치되지 않았습니다. 'pip install google-genai numpy'를 실행하세요.")
    exit()


# ============================================================================
# API Clients
# ============================================================================

class GroqClient:
    """Groq API Client"""

    def __init__(self, config: WriterConfig):
        self.config = config
        self.base_url = "https://api.groq.com/openai/v1"

    def generate(self, model: str, prompt: str, system: str = "",
                 temperature: float = 0.7, format_json: bool = False,
                 max_tokens: Optional[int] = None, reasoning_format: str = "hidden") -> str:

        url = f"{self.base_url}/chat/completions"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.config.max_generation_tokens,
            "reasoning_format": reasoning_format
        }

        if format_json:
            data["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=data, headers=headers, timeout=300)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def get_embedding(self, text: str) -> np.ndarray:
        """임베딩 생성 (fallback 포함)"""
        try:
            url = f"{self.base_url}/embeddings"

            data = {
                "model": self.config.embedding_model,
                "input": text[:8000]
            }

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=data, headers=headers, timeout=60)
            response.raise_for_status()

            embedding = response.json()["data"][0]["embedding"]
            return np.array(embedding, dtype=np.float32)

        except Exception as e:
            print(f"  ⚠️ Embedding API 실패, fallback 사용: {e}")
            vector_dim = 768
            vector = np.zeros(vector_dim, dtype=np.float32)
            return vector


class GroqClient:
    """Groq API 클라이언트"""

    def __init__(self, config: WriterConfig):
        self.config = config
        self.base_url = "https://api.groq.com/openai/v1"

    def generate(self, model: str, prompt: str, system: str = "",
                 temperature: float = 0.7, format_json: bool = False,
                 max_tokens: Optional[int] = None, reasoning_format: str = "hidden") -> str:
        """텍스트 생성"""
        url = f"{self.base_url}/chat/completions"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.config.max_generation_tokens,
            "reasoning_format": reasoning_format
        }

        if format_json:
            data["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=data, headers=headers, timeout=300)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def get_embedding(self, text: str) -> np.ndarray:
        """임베딩 생성 (fallback 포함)"""
        try:
            url = f"{self.base_url}/embeddings"

            data = {
                "model": self.config.embedding_model,
                "input": text[:8000]
            }

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=data, headers=headers, timeout=60)
            response.raise_for_status()

            embedding = response.json()["data"][0]["embedding"]
            return np.array(embedding, dtype=np.float32)

        except Exception as e:
            print(f"  ⚠️ Embedding API 실패, fallback 사용: {e}")
            vector_dim = 768
            vector = np.zeros(vector_dim, dtype=np.float32)
            return vector

class GeminiClient:
    """Gemini API Client """

    def __init__(self, config: WriterConfig):
        self.config = config

        api_key = self.config.api_key if hasattr(self.config, 'api_key') else None

        self.client = genai.Client(api_key=api_key)

    def generate(self, model: str, prompt: str, system: str = "",
                 temperature: float = 0.7, format_json: bool = False,
                 max_tokens: Optional[int] = None, **kwargs) -> str:

        contents: List[types.Content] = []

        user_parts = [types.Part(text=prompt)]
        contents.append(types.Content(role="user", parts=user_parts))

        config_params: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens or self.config.max_generation_tokens,
        }

        if system:
            config_params["system_instruction"] = system

        if format_json:
            config_params["response_mime_type"] = "application/json"

        try:
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(**config_params)
            )

            return response.text

        except APIError as e:
            print(f"⚠️ Gemini API 호출 실패: {e}")
            raise
        except Exception as e:
            print(f"⚠️ 예기치 않은 오류 발생: {e}")
            raise

    def get_embedding(self, text: str) -> np.ndarray:
        """임베딩 생성 (fallback 포함)"""

        model_name = self.config.embedding_model

        try:
            # 1. API 호출
            response = self.client.models.embed_content(
                model=model_name,
                content=text,
                task_type="RETRIEVAL_DOCUMENT"
            )

            # 2. 결과 반환
            # 응답 객체에서 임베딩 벡터를 .embedding 속성으로 추출해야 합니다.
            # 💡 수정된 부분: response['embedding'] -> response.embedding
            embedding = response.embedding
            return np.array(embedding, dtype=np.float32)

        except APIError as e:
            # API 호출 실패 시
            print(f"  ⚠️ Embedding API 실패: {e}")

            # 3. Fallback 처리
            vector_dim = 768  # 'text-embedding-004'의 차원은 768입니다.
            vector = np.zeros(vector_dim, dtype=np.float32)
            return vector
        except Exception as e:
            # 예기치 않은 다른 오류 발생 시
            print(f"  ⚠️ Embedding 처리 중 예기치 않은 오류 발생, fallback 사용: {e}")
            vector_dim = 768
            vector = np.zeros(vector_dim, dtype=np.float32)
            return vector