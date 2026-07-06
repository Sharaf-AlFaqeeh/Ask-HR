import os
from pathlib import Path
from typing import Dict, Any, Optional
# pyrefly: ignore [untyped-import]
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseModel):
    name: str = "AskHR Enterprise Engine"
    env: str = "development"
    debug: bool = True

class LLMSettings(BaseModel):
    service_host: str = "127.0.0.1"
    service_port: int = 8000
    model_path: str = "services/llm_inference_service/models/qwen2.5-7b-instruct-q4_k_m.gguf"
    n_ctx: int = 4096
    n_threads: int = 4
    n_gpu_layers: int = 0
    temperature: float = 0.1
    max_tokens: int = 1024

class VectorDBSettings(BaseModel):
    storage_path: str = "services/vector_db_service/local_qdrant_db"
    collection_name: str = "hr_policies"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

class OrchestratorSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080
    llm_api_url: str = "http://127.0.0.1:8000/v1"
    intent_confidence_threshold: float = 0.7
    use_sap_templates: bool = True
    # NLP analysis mode: "rule_first" (default), "rule_only", or "hybrid_always"
    nlp_mode: str = "rule_first"

class SAPSettings(BaseModel):
    api_base_url: str = "https://mock.successfactors.eu/odata/v2"
    company_id: str = "HSAGroup"
    client_id: str = "ask_hr_orchestrator"
    mock_mode: bool = True

class RedisSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None

class StorageSettings(BaseModel):
    type: str = "sqlite"
    session_ttl: int = 2592000
    redis: RedisSettings = Field(default_factory=RedisSettings)

class EnterpriseSettings(BaseSettings):
    """
    Combines config.yaml settings with environment overrides.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    app: AppSettings = Field(default_factory=AppSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)
    orchestrator: OrchestratorSettings = Field(default_factory=OrchestratorSettings)
    sap: SAPSettings = Field(default_factory=SAPSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    
    # Environment variables that override YAML values (or default settings)
    api_bearer_token: str = Field(default="askhr_super_secret_token_2026", validation_alias="API_BEARER_TOKEN")
    sap_client_secret: str = Field(default="mock_successfactors_client_secret_xyz123", validation_alias="SAP_CLIENT_SECRET")
    jwt_secret: str = Field(default="enterprise_ask_hr_jwt_secret_signing_key_456", validation_alias="JWT_SECRET")

_settings: Optional[EnterpriseSettings] = None

def load_settings(config_path: str = "config.yaml") -> EnterpriseSettings:
    """
    Loads config.yaml, maps it, and applies environment variable overrides.
    """
    global _settings
    
    yaml_data: Dict[str, Any] = {}
    path = Path(config_path)
    
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load {config_path}: {e}")
            
    # Apply direct overrides from environment variables if present
    app_env = os.getenv("APP_ENV")
    if app_env:
        yaml_data.setdefault("app", {})["env"] = app_env
        
    llm_port = os.getenv("LLM_SERVICE_PORT")
    if llm_port:
        yaml_data.setdefault("llm", {})["service_port"] = int(llm_port)
        
    orch_port = os.getenv("ORCHESTRATOR_SERVICE_PORT")
    if orch_port:
        yaml_data.setdefault("orchestrator", {})["port"] = int(orch_port)
        
    model_path = os.getenv("LLM_MODEL_PATH")
    if model_path:
        yaml_data.setdefault("llm", {})["model_path"] = model_path
        
    db_path = os.getenv("VECTOR_DB_PATH")
    if db_path:
        yaml_data.setdefault("vector_db", {})["storage_path"] = db_path

    # Apply Storage overrides
    storage_type = os.getenv("STORAGE_TYPE")
    if storage_type:
        yaml_data.setdefault("storage", {})["type"] = storage_type

    storage_ttl = os.getenv("STORAGE_SESSION_TTL")
    if storage_ttl:
        yaml_data.setdefault("storage", {})["session_ttl"] = int(storage_ttl)

    redis_host = os.getenv("REDIS_HOST")
    if redis_host:
        yaml_data.setdefault("storage", {}).setdefault("redis", {})["host"] = redis_host

    redis_port = os.getenv("REDIS_PORT")
    if redis_port:
        yaml_data.setdefault("storage", {}).setdefault("redis", {})["port"] = int(redis_port)

    redis_db = os.getenv("REDIS_DB")
    if redis_db:
        yaml_data.setdefault("storage", {}).setdefault("redis", {})["db"] = int(redis_db)

    redis_password = os.getenv("REDIS_PASSWORD")
    if redis_password:
        yaml_data.setdefault("storage", {}).setdefault("redis", {})["password"] = redis_password

    # Load with pydantic-settings (Environment variables override YAML settings)
    _settings = EnterpriseSettings(
        app=AppSettings(**yaml_data.get("app", {})),
        llm=LLMSettings(**yaml_data.get("llm", {})),
        vector_db=VectorDBSettings(**yaml_data.get("vector_db", {})),
        orchestrator=OrchestratorSettings(**yaml_data.get("orchestrator", {})),
        sap=SAPSettings(**yaml_data.get("sap", {})),
        storage=StorageSettings(**yaml_data.get("storage", {}))
    )
    
    return _settings


def get_settings() -> EnterpriseSettings:
    """
    Returns cached settings or loads default if not loaded yet.
    """
    global _settings
    if _settings is None:
        return load_settings()
    return _settings
