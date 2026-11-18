import pytest
from agentone.cards.config import load_settings

def test_defaults_are_openai():
    s = load_settings({})
    assert (s.inference.provider, s.extraction.provider, s.embedding.provider) == ("openai",) * 3
    assert s.embedding.dim == 1536 and s.embedding.name == "openai:text-embedding-3-small"

def test_each_role_is_independent():
    s = load_settings({"INFERENCE_PROVIDER": "anthropic", "EXTRACTION_PROVIDER": "openai", "EXTRACTION_MODEL": "gpt-4.1-nano",
                       "EMBEDDING_PROVIDER": "voyage"})
    assert s.inference.model == "claude-sonnet-5-5" and s.extraction.model == "gpt-4.1-nano"
    assert s.embedding.name == "voyage:voyage-3.5" and s.embedding.dim == 1024

def test_anthropic_embeddings_rejected_with_guidance():
    with pytest.raises(ValueError, match="no embeddings API"): load_settings({"EMBEDDING_PROVIDER": "anthropic"})

def test_bad_provider_and_unknown_dim():
    with pytest.raises(ValueError): load_settings({"INFERENCE_PROVIDER": "gemini"})
    with pytest.raises(ValueError, match="EMBEDDING_DIM"): load_settings({"EMBEDDING_MODEL": "my-model"})
    assert load_settings({"EMBEDDING_MODEL": "my-model", "EMBEDDING_DIM": "768"}).embedding.dim == 768
