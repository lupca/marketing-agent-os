# core/ai_clients/context_manager.py
import uuid
import logging
from transformers import AutoTokenizer
from langchain_core.messages import trim_messages
from db.connection import SessionLocal
from core.models import Workspace

logger = logging.getLogger("context_manager")
logging.basicConfig(level=logging.INFO)

# Initialize Qwen Tokenizer locally for 100% accurate Vietnamese token counting
logger.info("Initializing Qwen Tokenizer for Vietnamese token counting...")
try:
    qwen_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct", use_fast=True)
    logger.info("Successfully loaded Qwen Tokenizer!")
except Exception as e:
    logger.warning(f"Could not load Qwen Tokenizer online: {e}. Falling back to clean Vietnamese word multiplication.")
    qwen_tokenizer = None


def get_trimmed_context(messages: list, max_tokens: int = 14000, workspace_id: str = None) -> list:
    """
    Trims the conversation messages list using LangChain's trim_messages utility
    to ensure it fits within the context window, utilizing Qwen tokenizer for 100% Vietnamese accuracy.
    Reads max_tokens dynamically from workspace settings if workspace_id is provided.
    """
    if not messages:
        return []
    
    # Dynamically read max_tokens from workspace settings if available
    if workspace_id:
        try:
            db = SessionLocal()
            ws = db.query(Workspace).filter_by(id=uuid.UUID(str(workspace_id))).first()
            if ws and ws.settings and ws.settings.get("max_tokens"):
                max_tokens = int(ws.settings["max_tokens"])
                logger.info(f"Using dynamic max_tokens={max_tokens} from workspace settings.")
            db.close()
        except Exception as e:
            logger.warning(f"Could not read max_tokens from workspace settings: {e}")
        
    def count_tokens_qwen(msgs: list) -> int:
        if qwen_tokenizer is not None:
            total_tokens = 0
            for m in msgs:
                total_tokens += len(qwen_tokenizer.encode(m.content or "")) + 4
            return total_tokens
        else:
            # Safe Vietnamese word fallback count
            total_tokens = 0
            for m in msgs:
                words = len((m.content or "").split())
                total_tokens += int(words * 1.8) + 4
            return total_tokens
        
    try:
        trimmed = trim_messages(
            messages,
            max_tokens=max_tokens,
            strategy="last",
            token_counter=count_tokens_qwen,
            include_system=True,
            allow_partial=False
        )
        logger.info(f"Successfully trimmed messages context. Before: {len(messages)}, After: {len(trimmed)}")
        return trimmed
    except Exception as e:
        logger.error(f"Error in trim_messages: {e}. Falling back to basic slice.", exc_info=True)
        from langchain_core.messages import SystemMessage
        system_msg = [messages[0]] if isinstance(messages[0], SystemMessage) else []
        other_msgs = messages[1:] if system_msg else messages
        return system_msg + other_msgs[-12:]
