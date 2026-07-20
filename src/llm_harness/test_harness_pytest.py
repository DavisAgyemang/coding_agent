import os
from unittest.mock import MagicMock, patch

import pytest

from src.llm_harness.harness import LLMHarness


@pytest.fixture
def console():
    c = MagicMock()
    c.print = MagicMock()
    return c


@patch("src.llm_harness.harness.RepoMapper")
@patch("src.llm_harness.harness.Agent")
@patch("src.llm_harness.harness.OpenAIChatModel")
@patch("src.llm_harness.harness.AsyncAzureOpenAI")
def test_determine_provider_openai_prefix_returns_raw_model(
    mock_azure, mock_model, mock_agent, mock_repo_mapper, console
):
    harness = LLMHarness.__new__(LLMHarness)
    harness.raw_model_string = "openai:gpt-4o"
    harness.model_name = "gpt-4o"
    harness.use_entra_id = True
    harness.auth_method = "UNKNOWN"
    harness.console = console

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
        result = LLMHarness._determine_provider(harness)

    assert result == "openai:gpt-4o"
    assert harness.auth_method == "OpenAI API Key Verification"


@patch("src.llm_harness.harness.subprocess.run", side_effect=Exception("az missing"))
def test_get_entra_token_wraps_subprocess_errors(mock_run):
    harness = LLMHarness.__new__(LLMHarness)

    with pytest.raises(RuntimeError, match="Missing active identity token"):
        LLMHarness._get_entra_token(harness)
