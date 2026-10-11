"""
Multi-provider LLM client for the resume analysis task.

Supports two backends, selected via the LLM_PROVIDER environment variable:

  LLM_PROVIDER=anthropic   -> calls Claude directly via the Anthropic SDK
                              (ANTHROPIC_API_KEY, CLAUDE_MODEL)

  LLM_PROVIDER=<anything else, e.g. "openrouter", "grok", "deepseek">
                           -> routed through OpenRouter's OpenAI-compatible
                              Chat Completions API (OPENROUTER_API_KEY,
                              OPENROUTER_MODEL). This is what lets you run
                              the analysis on DeepSeek, Grok, Llama, or any
                              other model OpenRouter exposes, just by
                              changing OPENROUTER_MODEL - no code changes.

Both paths:
  - Send the constructed prompt as a single user turn.
  - Strip any accidental markdown code fences from the response.
  - Parse the response into a Python dict.
  - Raise a single, catchable LLMAnalysisError for the UI layer.
"""

import json
import os
import re

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "deepseek/deepseek-chat-v3-0324"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"


class LLMAnalysisError(Exception):#custom exception error

    """Raised when the LLM call fails or returns unparseable output."""

    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message)
        self.raw_response = raw_response


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)#This regular expression is designed to match text that is enclosed within markdown code fences, specifically those that start with ``` or ```json and end with ```. The pattern captures the content inside the code fences while allowing for optional whitespace around it. The re.DOTALL flag allows the dot (.) in the regex to match newline characters, enabling the pattern to capture multi-line content within the code fences.
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _strip_code_fences(text: str) -> str:#it takes a string input (text) and removes any markdown code fences that may be present. Markdown code fences are typically used to denote blocks of code or preformatted text, and they can be specified with triple backticks (```) or triple backticks followed by "json" (```json). The function uses a regular expression to search for these patterns and extract the content inside the fences, returning it as a cleaned-up string without the surrounding fences.
    """Remove ```json ... ``` or ``` ... ``` fences if the model added them."""
    text = (text or "").strip()
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def _parse_json_response(raw_text: str) -> dict:#it takes the raw text output from the LLM, attempts to clean it by removing any markdown code fences, and then tries to parse it as JSON. If the parsing fails, it makes a salvage attempt to extract the largest JSON-like block from the text. If all attempts fail, it raises an LLMAnalysisError with details about the failure.
    """Parse the model's raw text output into a dict, with a salvage attempt."""
    cleaned = _strip_code_fences(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Salvage attempt: grab the largest {...} block in case the model
        # added stray preamble/trailing text despite instructions.
        match = _JSON_BLOCK_RE.search(cleaned)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise LLMAnalysisError(
            f"Model response was not valid JSON: {exc}", raw_response=raw_text
        )


def get_active_provider_info() -> dict:#it returns a dictionary containing information about the currently configured LLM provider and model, as well as whether the provider is properly configured with an API key. It checks the environment variables to determine which provider is being used (Anthropic or OpenRouter) and retrieves the corresponding model and API key configuration status. This function is useful for debugging and ensuring that the application is set up correctly to interact with the chosen LLM provider.
    """Return a small dict describing the currently configured provider/model."""
    provider = (os.getenv("LLM_PROVIDER") or "openrouter").strip().lower()
    if provider == "anthropic":
        return {
            "provider": "anthropic",
            "model": os.getenv("CLAUDE_MODEL", DEFAULT_ANTHROPIC_MODEL),
            "configured": _is_configured(os.getenv("ANTHROPIC_API_KEY")),
        }
    return {
        "provider": provider or "openrouter",
        "model": os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
        "configured": _is_configured(os.getenv("OPENROUTER_API_KEY")),
    }


def _is_configured(key: str) -> bool:
    return bool(key) and "REPLACE_WITH_YOUR_KEY" not in key


def run_resume_analysis(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:#this function is responsible for sending the analysis prompt to the configured LLM (Language Model) and returning the parsed JSON response. It takes in the prompt, optional provider, model, and API key parameters. Based on the specified or default provider, it calls either the Anthropic or OpenRouter backend to process the prompt. The function handles errors and raises a custom LLMAnalysisError if there are issues with the API call or if the response is not valid JSON.
    """
    Send the analysis prompt to the configured LLM and return parsed JSON.

    Args:
        prompt: The full prompt produced by prompts.analysis_prompt.build_prompt.
        provider: Optional override for LLM_PROVIDER ("anthropic" or any other
                  value, treated as an OpenRouter-routed model).
        model: Optional override for the model id.
        api_key: Optional override for the provider's API key (useful for a
                 sidebar "paste your own key" field instead of editing .env).

    Returns:
        A dict matching the OUTPUT_SCHEMA defined in prompts/analysis_prompt.py.

    Raises:
        LLMAnalysisError: On API errors or if the response is not valid JSON.
    """
    provider = (provider or os.getenv("LLM_PROVIDER") or "openrouter").strip().lower()

    if provider == "anthropic":
        return _run_anthropic(prompt, model=model, api_key=api_key)
    return _run_openrouter(prompt, model=model, api_key=api_key)


def _run_anthropic(prompt: str, model: str | None, api_key: str | None) -> dict:#this function is responsible for sending the analysis prompt to the Anthropic LLM (Language Model) and returning the parsed JSON response. It takes in the prompt, optional model, and API key parameters. The function checks if the Anthropic SDK is installed and if the API key is configured. It then creates an Anthropic client and sends the prompt to the specified model. The function handles errors related to the API call and raises a custom LLMAnalysisError if there are issues with the API or if the response is not valid JSON.
    try:
        import anthropic
    except ImportError as exc:
        raise LLMAnalysisError(
            "The 'anthropic' package is not installed. Run: pip install anthropic"
        ) from exc

    key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not _is_configured(key):
        raise LLMAnalysisError(
            "ANTHROPIC_API_KEY is not configured. Set it in your .env file "
            "(or paste one in the sidebar) - get one at https://console.anthropic.com/"
        )

    client = anthropic.Anthropic(api_key=key)
    model = model or os.getenv("CLAUDE_MODEL", DEFAULT_ANTHROPIC_MODEL)
    max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "8000"))

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as exc:
        raise LLMAnalysisError(f"Anthropic API error ({exc.status_code}): {exc.message}")
    except anthropic.APIConnectionError as exc:
        raise LLMAnalysisError(f"Could not reach the Anthropic API: {exc}")
    except Exception as exc:  # noqa: BLE001 - surface any unexpected SDK error cleanly
        raise LLMAnalysisError(f"Unexpected error calling Claude: {exc}")

    raw_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    return _parse_json_response(raw_text)


def _run_openrouter(prompt: str, model: str | None, api_key: str | None) -> dict:#this function is responsible for sending the analysis prompt to the OpenRouter LLM (Language Model) and returning the parsed JSON response. It takes in the prompt, optional model, and API key parameters. The function constructs the request payload and headers, sends the request to the OpenRouter API, and handles any errors that may occur during the API call. If the response is valid, it parses the JSON content and returns it as a dictionary. If there are issues with the API call or if the response is not valid JSON, it raises a custom LLMAnalysisError.
    key = api_key or os.getenv("OPENROUTER_API_KEY", "")
    if not _is_configured(key):
        raise LLMAnalysisError(
            "OPENROUTER_API_KEY is not configured. Set it in your .env file "
            "(or paste one in the sidebar) - get one at https://openrouter.ai/keys"
        )

    model = model or os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "8000"))
    temperature = float(os.getenv("OPENROUTER_TEMPERATURE", "0.3"))

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:8501"),
        "X-Title": "AI Resume Intelligence Analyzer",
    }
    base_payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }

    # Try with strict JSON-mode first (supported by most OpenRouter models,
    # including DeepSeek); fall back to a plain request if the model/route
    # rejects the response_format parameter.
    for payload in (
        {**base_payload, "response_format": {"type": "json_object"}},
        base_payload,
    ):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=180)
        except requests.exceptions.RequestException as exc:
            raise LLMAnalysisError(f"Could not reach the OpenRouter API: {exc}")

        if resp.status_code == 400 and "response_format" in (resp.text or ""):
            # This model/route doesn't support JSON mode - retry without it.
            continue

        if not resp.ok:
            raise LLMAnalysisError(
                f"OpenRouter API error ({resp.status_code}) for model '{model}': "
                f"{resp.text[:500]}"
            )

        try:
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError) as exc:
            raise LLMAnalysisError(
                f"Unexpected OpenRouter response shape: {exc}",
                raw_response=resp.text[:2000],
            )

        return _parse_json_response(raw_text)

    raise LLMAnalysisError(f"OpenRouter rejected the request for model '{model}'.")
