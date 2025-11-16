"""OpenRouter API client for LLM evaluation."""
import os
import time
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class OpenRouterClient:
    """Client for interacting with OpenRouter API."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: Ignored - API key is only read from .env file
            model: Model name (defaults to 'openai/gpt-4o')
        """
        # Only use API key from .env file
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY in .env file.")
        
        self.model = model or 'openai/gpt-4o'
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
    def _make_request(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Make API request with retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            API response dictionary
            
        Raises:
            Exception: If request fails after retries
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/logge/WahlOMatic",
            "X-Title": "WahlOMat LLM Evaluation"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    print(f"Request failed, retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"API request failed after {self.max_retries} attempts: {e}")
        
    def get_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Get completion from LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            Response text from LLM
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self._make_request(messages)
        
        # Extract content from response
        if 'choices' in response and len(response['choices']) > 0:
            return response['choices'][0]['message']['content']
        else:
            raise Exception(f"Unexpected API response format: {response}")

