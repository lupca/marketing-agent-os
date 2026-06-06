# core/ai_clients/llm_client.py
import os
import uuid
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.dependencies import get_session
from core.models import Workspace

load_dotenv()
logger = logging.getLogger("llm_client")
logging.basicConfig(level=logging.INFO)

# Model-specific pricing (USD per 1K tokens) for accurate cost tracking
MODEL_PRICING = {
    "Qwen/Qwen3.6-35B-A3B":   {"prompt": 0.00020, "completion": 0.00160},
    "Qwen/Qwen3.5-35B-A3B":   {"prompt": 0.00020, "completion": 0.00160},
    "Qwen/Qwen3-32B":          {"prompt": 0.00050, "completion": 0.00200},
    "deepseek-ai/DeepSeek-V3": {"prompt": 0.00027, "completion": 0.00110},
}
DEFAULT_PRICING = {"prompt": 0.00050, "completion": 0.00200}


def get_dynamic_llm_client(workspace_id_str: str, json_format: bool = False):
    """
    Dynamically instantiates a ChatOpenAI client based on Workspace database settings.
    Enforces that all configurations (URL, Model, Key) must be present in the database,
    adhering to single-source-of-truth principles.
    """
    with get_session() as db:
        try:
            ws_id = None
            if workspace_id_str and workspace_id_str != "None":
                try:
                    ws_id = uuid.UUID(workspace_id_str)
                except ValueError:
                    pass
            
            ws = None
            if ws_id:
                ws = db.query(Workspace).filter_by(id=ws_id).first()
                
            if not ws:
                ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
            if not ws:
                ws = db.query(Workspace).first()
                
            if not ws:
                raise ValueError("No workspaces found in database.")
            ws_settings = ws.settings or {}
            
            api_url = ws_settings.get("ai_api_url")
            if not api_url:
                logger.warning("[llm_client] 'ai_api_url' not found in workspace settings. Falling back to default local URL.")
                api_url = "http://localhost:11434/v1"
                
            api_key = ws_settings.get("siliconflow_api_key") or "dummy_key_for_testing_do_not_use_cloud"
            
            model_name = ws_settings.get("ai_model")
            if not model_name:
                logger.warning("[llm_client] 'ai_model' not found in workspace settings. Falling back to default Qwen model.")
                model_name = "Qwen/Qwen2.5-7B-Instruct"
                
            temperature = float(ws_settings.get("temperature", 0.2))
            enable_thinking = ws_settings.get("enable_thinking", False)
        
            # Normalize LLM Base URL to ensure OpenAI-compatible compatibility (e.g. append /v1 if missing)
            api_url = api_url.strip()
            if not api_url.endswith("/v1") and not api_url.endswith("/v1/"):
                api_url = api_url.rstrip("/") + "/v1"
            
            # Determine if we are routing locally to Ollama based on the Base URL
            is_local = "localhost" in api_url or "127.0.0.1" in api_url or "172." in api_url or "192.168." in api_url or "10." in api_url or "ollama" in api_url
        
            logger.info(f"[get_dynamic_llm_client] Routing evaluation - URL: {api_url}, Model: {model_name}, is_local: {is_local}")
        
            # Route locally if local URL is configured
            if is_local:
                # Normalize model name for local Ollama compatibility
                local_model = model_name
                if "Qwen/Qwen2.5-7B-Instruct" in model_name:
                    local_model = "qwen2.5:7b-instruct"
                elif "Qwen/Qwen2.5-14B-Instruct" in model_name:
                    local_model = "qwen2.5:14b-instruct"
                elif "Qwen/Qwen2.5-7B" in model_name:
                    local_model = "qwen2.5:7b"
                
                logger.info(f"Routing LLM requests LOCALLY to Ollama at {api_url} for model: {local_model} (original: {model_name})")
                model_kwargs = {}
                if json_format:
                    model_kwargs["response_format"] = {"type": "json_object"}
                
                return ChatOpenAI(
                    base_url=api_url,
                    api_key=api_key or "ollama", # placeholder for local Ollama
                    model=local_model,
                    temperature=temperature,
                    max_retries=3,
                    timeout=60,
                    model_kwargs=model_kwargs
                )
            
            # Otherwise, route to Cloud
            if not api_key:
                raise ValueError("Missing API key configuration in workspace settings for cloud LLM.")
            
            logger.info(f"Routing LLM requests to Cloud at {api_url} for model: {model_name}")
            model_kwargs = {
                "extra_body": {
                    "enable_thinking": enable_thinking  # Explicitly disables reasoning/thinking
                }
            }
            if json_format:
                model_kwargs["response_format"] = {"type": "json_object"}
            
            return ChatOpenAI(
                base_url=api_url,
                api_key=api_key,
                model=model_name,
                temperature=temperature,
                max_retries=3,
                timeout=60,
                model_kwargs=model_kwargs
            )
        except Exception as e:
            logger.error(f"Error loading dynamic LLM client: {e}")
            raise
from tenacity import retry, stop_after_attempt, wait_random_exponential

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(min=1, max=5)
)
def _invoke_llm_with_retry(model, messages):
    return model.invoke(messages)

def generate_text(prompt: str, system_prompt: str = None, json_format: bool = False, workspace_id: str = None) -> str:
    """Generate text using SiliconFlow ChatOpenAI model dynamically configured by workspace settings."""
    try:
        model = get_dynamic_llm_client(str(workspace_id), json_format=json_format)
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        response = _invoke_llm_with_retry(model, messages)
        
        # Extract token metrics for granular cost auditing
        try:
            meta = response.response_metadata or {}
            token_usage = meta.get("token_usage") or {}
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)
            total_tokens = token_usage.get("total_tokens", 0)
            
            # Retrieve pricing info dynamically
            pricing = MODEL_PRICING.get(model.model, DEFAULT_PRICING)
            cost = (prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]) / 1000.0
            
            # Log the decision to PostgreSQL audit trail
            from core.decision_logger import log_decision
            log_decision(
                workspace_id=workspace_id,
                agent_name="LLM Text Generator",
                action="Generate Text",
                decision_status="success",
                reason=f"Generated text with model: {model.model} (Tokens: {total_tokens}, Cost: ${cost:.5f})",
                metadata={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "total_cost_usd": cost,
                    "model": model.model
                }
            )
        except Exception as audit_err:
            logger.error(f"Failed to log billing audit: {audit_err}")
            
        return response.content
    except Exception as e:
        logger.error(f"Error in generate_text: {e}")
        raise
