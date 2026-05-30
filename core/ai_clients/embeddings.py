# core/ai_clients/embeddings.py
import torch
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("embeddings")
logging.basicConfig(level=logging.INFO)

# Lazy-initialized Local Embeddings model (avoids crash if cuda/torch not fully initialized at import time)
_embeddings_model = None

def _get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        model_name = "BAAI/bge-m3"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading local SentenceTransformer embedding model '{model_name}' on device: {device.upper()}...")
        try:
            _embeddings_model = SentenceTransformer(model_name, device=device)
            logger.info(f"Successfully loaded local {model_name} model!")
        except Exception as e:
            logger.warning(f"Failed to load local embedding model {model_name} on GPU VRAM: {e}. Falling back to CPU.")
            try:
                _embeddings_model = SentenceTransformer(model_name, device="cpu")
                logger.info(f"Successfully loaded local {model_name} model on CPU!")
            except Exception as ex:
                logger.error(f"Critical error loading local embedding model {model_name}: {ex}")
                raise
    return _embeddings_model


def get_embedding(text_content: str) -> list:
    """Generate vector embedding (1024-dim) using local BAAI/bge-m3 model running on local GPU (CUDA)."""
    try:
        return _get_embeddings_model().encode(text_content).tolist()
    except Exception as e:
        logger.error(f"Error in get_embedding: {e}")
        raise
