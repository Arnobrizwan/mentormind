import os
import logging
import httpx

logger = logging.getLogger(__name__)

def bootstrap_corpus():
    """Download the corpus database on container boot if DATASET_REPO is configured."""
    dataset_repo = os.getenv("DATASET_REPO")
    if not dataset_repo:
        logger.info("DATASET_REPO is not set; skipping corpus bootstrap.")
        return

    hf_token = os.getenv("HF_TOKEN")
    db_url = os.getenv("PASTPAPERS_DB_URL", "sqlite+aiosqlite:///./pastpapers.db")
    if not db_url.startswith("sqlite+aiosqlite:///"):
        logger.info("Non-sqlite database configured via PASTPAPERS_DB_URL; skipping bootstrap.")
        return

    # Extract db path from URL (remove sqlite+aiosqlite:///)
    db_path = db_url[len("sqlite+aiosqlite:///"):]

    # If the file already exists and is non-empty, do not overwrite it.
    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
        logger.info(f"Database file at {db_path} already exists; skipping bootstrap.")
        return

    logger.info(f"Bootstrapping corpus from Hugging Face dataset: {dataset_repo}...")
    url = f"https://huggingface.co/datasets/{dataset_repo}/resolve/main/pastpapers.db"
    
    headers = {}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    try:
        # Create directory structure if needed
        db_dir = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(db_dir, exist_ok=True)
        
        # Download database in chunks to avoid high memory utilization
        with httpx.Client(follow_redirects=True, timeout=60.0) as client:
            with client.stream("GET", url, headers=headers) as response:
                if response.status_code != 200:
                    logger.error(f"Failed to bootstrap corpus from HF: HTTP {response.status_code}")
                    return
                with open(db_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        
        logger.info(f"Successfully bootstrapped corpus to {db_path}.")
    except Exception as e:
        logger.error(f"Error occurred during corpus bootstrap: {e}")
