import os
import requests
import logging

from dotenv import load_dotenv
load_dotenv()

import uuid
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """A client for interacting with the OpenRouter API."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key=None, model=None):
        """
        Initializes the OpenRouterClient.

        Args:
            api_key (str): The OpenRouter API key. If None, attempts to load from the OPENROUTER_API_KEY env var.
            model (str): The OpenRouter model ID to use. If None, attempts to load from OPENROUTER_MODEL env var.
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key must be provided or set in the OPENROUTER_API_KEY environment variable.")
        
        self.model = model or os.environ.get("OPENROUTER_MODEL") or "deepseek/deepseek-v4-flash-0731"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/dis70rt/OfferLog", # Optional: Replace with your actual site URL for analytics
            "X-Title": "OfferLog" # Optional: Replace with your app name for OpenRouter rankings
        }

    def __repr__(self):
        return f"OpenRouterClient(model={self.model!r})"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        reraise=True
    )
    def generate_text(self, prompt, message_id=None, system_prompt=None, max_tokens=1000, temperature=0.1):
        """
        Generates text using the configured OpenRouter model.

        Args:
            prompt (str): The user prompt.
            message_id (str): Optional ID to link this run (e.g., a Gmail message ID). Generates a UUID if None.
            system_prompt (str): Optional system prompt to guide the model's behavior.
            max_tokens (int): Maximum number of tokens to generate.
            temperature (float): Sampling temperature (0.0 to 2.0).

        Returns:
            tuple: A tuple containing (text (str), metadata (dict)), or (None, metadata (dict)) if an error occurred.
        """

        if message_id is None:
            message_id = str(uuid.uuid4())
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            response = requests.post(f"{self.BASE_URL}/chat/completions", headers=self.headers, json=payload)
            response.raise_for_status()
            
            
            data = response.json()
            if "error" in data:
                raise requests.exceptions.RequestException(f"OpenRouter upstream error: {data['error']}")
                
            text = data["choices"][0]["message"]["content"]
            
            metadata = {
                "id": data.get("id"),
                "model": data.get("model"),
                "usage": data.get("usage", {}),
                "status": "success",
                "message_id": message_id
            }
            
            return text, metadata
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with OpenRouter API: {e}")
            if 'response' in locals() and response is not None and response.text:
                 logger.error(f"OpenRouter Error Response [{response.status_code}]: {response.text[:200]}")
            return None, {"message_id": message_id, "status": "api_error"}
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing OpenRouter response format: {e}")
            if 'data' in locals():
                logger.error(f"Raw data: {data}")
            return None, {"message_id": message_id, "status": "parse_error"}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        client = OpenRouterClient(model="deepseek/deepseek-v4-flash-0731")
        
        prompt = "Write a one-sentence summary of what an API is."
        print(f"Sending prompt to '{client.model}': {prompt}\n")
        
        result = client.generate_text(prompt)
        
        if result and result[0]:
            text, audit = result
            print(f"Response:\n{text}\n")
            print("--- Metadata (AuditRecord) ---")
            print(audit.model_dump_json(indent=2))
        else:
            print("Failed to get a response. Check your API key and network connection.")
            if result and result[1]:
                print(f"Audit Log: {result[1].model_dump_json(indent=2)}")
            
    except ValueError as e:
         print(f"Configuration Error: {e}")
