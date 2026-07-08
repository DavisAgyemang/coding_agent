from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from openai import AsyncAzureOpenAI
from src.llm_tooling.repomap import RepoMapper
from src.llm_tooling import llm_actions
from pathlib import Path
import os
from typing import Optional, Union
import getpass
import subprocess
import json

class QueryResponse(BaseModel):
    reasoning: str = Field(description="Step-by-step logical breakdown of your thought process.")
    answer: str = Field(description="The final clear, concise answer or code response.")

class LLMHarness:
    def __init__(self,  model_name: str,  console, use_entra_id: bool = True):
        self.raw_model_string = model_name
        self.model_name = (
            model_name.replace("azure:", "")
            .replace("anthropic:", "")
            .replace("openai:", "")
            .replace("ollama:", "")
        )
        self.use_entra_id = use_entra_id
        self.auth_method = "UNKNOWN"
        self.resolved_model = self._determine_provider()
        self.console = console

        # Initialize Tree-Sitter workspace parser framework
        self.repo_mapper = RepoMapper(root_dir=Path.cwd())

        self.agent = Agent(
            model=self.resolved_model,
            output_type=QueryResponse,
        )
        self._link_llm_actions()
        self._register_dynamic_prompts()

    def _link_llm_actions(self):
        self.agent.tool_plain(llm_actions.inspect_repository_structure)
        self.agent.tool_plain(llm_actions.read_repo_file)
        self.agent.tool_plain(llm_actions.write_repo_file)
        self.agent.tool_plain(llm_actions.verify_code_health)

    def _register_dynamic_prompts(self):
        """Attaches dynamic structural repomapping instructions to the execution chain."""
        mapper = self.repo_mapper

        @self.agent.system_prompt
        def generate_workspace_context() -> str:
            skeleton_map = mapper.generate_map()

            base_prompt = (
                "You are an elite developer assistant with direct file-system access to the local repository.\n"
                "You can inspect files and write modifications to them using your provided tools.\n"
                "Always check a file's content before editing it.\n\n"
                "🚨 LEVEL 4 MANDATE: SELF-CORRECTING EXECUTION 🚨\n"
                "When asked to write, modify, or refactor code, you MUST follow this loop:\n"
                "1. Write or modify the target file using 'write_repo_file'.\n"
                "2. IMMEDIATELY call 'verify_code_health' targeting that file to test for errors.\n"
                "3. If an error is returned, analyze the crash logs, correct the bugs, rewrite the file, and re-verify until it returns success (✅).\n\n"
                "Below is the computed multi-file structural map of the workspace. Use this map to instantly "
                "locate classes, dependencies, and functions across different files before issuing tools:\n\n"
            )
            return base_prompt + skeleton_map

    def _determine_provider(self) -> Union[str, OpenAIChatModel]:
        # 1. 🟦 AZURE OPENAI ROUTING (Checks your new raw tracking string)
        if self.raw_model_string.startswith("azure:"):
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            if not endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is missing for Azure model.")

            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

            if self.use_entra_id:
                self.auth_method = "Microsoft Entra ID (Passwordless)"
                azure_client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_version=api_version,
                    azure_ad_token_provider=self._get_entra_token
                )
            else:
                if not os.getenv("AZURE_OPENAI_API_KEY"):
                    self.console.print(
                        "\n🔒 [yellow][SECURITY INTERCEPT] AZURE_OPENAI_API_KEY is missing from environment.[/yellow]")
                    user_key = getpass.getpass("Enter your Azure Secret API Key: ").strip()
                    if not user_key: raise ValueError("Azure API Key cannot be empty.")
                    os.environ["AZURE_OPENAI_API_KEY"] = user_key

                self.auth_method = "Static Corporate API Key"
                azure_client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_version=api_version,
                    api_key=os.environ["AZURE_OPENAI_API_KEY"]
                )

            # Pass clean model deployment string (e.g. "gpt-5.4-mini") down to Azure SDK
            return OpenAIChatModel(model_name=self.model_name,
                                   provider=OpenAIProvider(openai_client=azure_client))

        # 2. 🔀 NON-AZURE PROVIDER ROUTING (Extract prefix from raw string)
        provider_prefix = self.raw_model_string.split(":")[0] if ":" in self.raw_model_string else ""

        # 1️⃣ ANTHROPIC CLAUDE
        if provider_prefix == "anthropic":
            if not os.getenv("ANTHROPIC_API_KEY"):
                self.console.print(
                    "\n🔒 [yellow][SECURITY INTERCEPT] ANTHROPIC_API_KEY is missing from environment.[/yellow]")
                user_key = getpass.getpass("Enter your Anthropic API Key: ").strip()
                if not user_key: raise ValueError("Anthropic API Key cannot be empty.")
                os.environ["ANTHROPIC_API_KEY"] = user_key
            self.auth_method = "Anthropic API Key Verification"

        # 2️⃣ STANDARD OPENAI
        elif provider_prefix == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                self.console.print("\n🔒 [yellow][SECURITY INTERCEPT] OPENAI_API_KEY is missing from environment.[/yellow]")
                user_key = getpass.getpass("Enter your OpenAI API Key: ").strip()
                if not user_key: raise ValueError("OpenAI API Key cannot be empty.")
                os.environ["OPENAI_API_KEY"] = user_key
            self.auth_method = "OpenAI API Key Verification"

        # 3️⃣ LOCAL OLLAMA
        elif provider_prefix == "ollama":
            self.auth_method = "Local Air-Gapped Engine"

        # 4️⃣ CUSTOM STRING FALLBACK
        else:
            self.auth_method = "Standard Environment Variables Mapping"

        # Return full string ("openai:gpt-4o") so Pydantic AI's native router understands it
        return self.raw_model_string

    def _get_entra_token(self) -> str:
        try:
            cmd = ["az", "account", "get-access-token", "--resource", "https://cognitiveservices.azure.com", "--output",
                   "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)["accessToken"]
        except Exception as e:
            raise RuntimeError(f"Missing active identity token: {e}")