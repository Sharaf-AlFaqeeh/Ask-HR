import os
from pathlib import Path
from typing import Dict, Any, Optional
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

class SAPSettings(BaseModel):
    api_base_url: str = "https://mock.successfactors.eu/odata/v2"
    company_id: str = "HSAGroup"
    client_id: str = "ask_hr_orchestrator"
    mock_mode: bool = True

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
    if os.getenv("APP_ENV"):
        yaml_data.setdefault("app", {})["env"] = os.getenv("APP_ENV")
    if os.getenv("LLM_SERVICE_PORT"):
        yaml_data.setdefault("llm", {})["service_port"] = int(os.getenv("LLM_SERVICE_PORT"))
    if os.getenv("ORCHESTRATOR_SERVICE_PORT"):
        yaml_data.setdefault("orchestrator", {})["port"] = int(os.getenv("ORCHESTRATOR_SERVICE_PORT"))
    if os.getenv("LLM_MODEL_PATH"):
        yaml_data.setdefault("llm", {})["model_path"] = os.getenv("LLM_MODEL_PATH")
    if os.getenv("VECTOR_DB_PATH"):
        yaml_data.setdefault("vector_db", {})["storage_path"] = os.getenv("VECTOR_DB_PATH")

    # Load with pydantic-settings (Environment variables override YAML settings)
    _settings = EnterpriseSettings(
        app=AppSettings(**yaml_data.get("app", {})),
        llm=LLMSettings(**yaml_data.get("llm", {})),
        vector_db=VectorDBSettings(**yaml_data.get("vector_db", {})),
        orchestrator=OrchestratorSettings(**yaml_data.get("orchestrator", {})),
        sap=SAPSettings(**yaml_data.get("sap", {}))
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
