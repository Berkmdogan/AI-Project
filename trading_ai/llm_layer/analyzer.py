import anthropic
from trading_ai.core.config import get_settings
from trading_ai.core.models import MarketState, MLPrediction
from trading_ai.llm_layer.prompts import SYSTEM_PROMPT, build_user_prompt

settings = get_settings()

# Client singleton
_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def analyze(state: MarketState, pred: MLPrediction) -> str:
    """
    MarketState + MLPrediction → Claude analizi (string).

    Sistem prompt'u prompt caching ile önbelleğe alınır:
    tekrarlayan sinyallerde API maliyeti düşer.
    """
    client      = get_client()
    user_prompt = build_user_prompt(state, pred)

    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                # Sistem prompt sabittir → cache_control ile önbelleğe al
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": user_prompt}
        ],
    )

    return response.content[0].text


def analyze_with_meta(state: MarketState, pred: MLPrediction) -> dict:
    """Analiz metni + token kullanımı + cache bilgisi döner."""
    client      = get_client()
    user_prompt = build_user_prompt(state, pred)

    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": user_prompt}
        ],
    )

    usage = response.usage
    return {
        "text": response.content[0].text,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
        "cache_create_tokens": getattr(usage, "cache_creation_input_tokens", 0),
    }
