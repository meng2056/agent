from pydantic import BaseModel, Field

class Settings(BaseModel):

    CHUNK_MAX_TOKENS: int = 3000
    EMBED_MAX_TOKENS: int = 6144

    ALLOWED_EXTENSIONS: set[str] = {'.py', '.v', '.sv'}

    PYTHON_TARGET_NODES: set[str] = {"class_definition", "function_definition"}

    VERILOG_TARGET_NODES: set[str] = {"module_declaration",
                                      "package_declaration",
                                      "class_declaration"}

    SAVE_ENRICHED: bool = False

    VECTOR_DB_COLLECTION_NAME: str = "racg_vector_db"
    VECTOR_DB_PATH: str = "/home/alanm/python_repo/ai/RACG/vector_path"

settings = Settings()