"""Pydantic model for the ArchiMate Solution/Application/Technology layer."""

from pydantic import BaseModel


class SolutionArchElement(BaseModel):
    """An ArchiMate Application or Technology layer element."""

    id: str
    name: str
    archimate_type: str          # application-component|service|data-object|node|technology-service|artifact
    domain_id: str = ""
    status: str = "draft"
    description: str = ""
    confidence: float = 0.8
    # Application component fields
    version: str = ""
    deployment_status: str = "planned"  # planned|dev|staging|production
    # Agent fields
    is_agent: int = 0
    default_autonomy: str = ""
    default_track: str = ""
    knowledge_base_ref: str = ""
    promoted_to_actor: int = 0
    # Knowledge store fields
    is_knowledge_store: int = 0
    store_type: str = ""         # vector|graph|document|hybrid
    config_path: str = ""
    fallback_ref: str = ""
    ingestion_pipeline_ref: str = ""
    # Technology / infrastructure fields
    platform: str = ""
    environment: str = ""
    provider: str = ""           # Azure|on-prem|hybrid
    region: str = ""
    ga_status: str = "ga"        # ga|preview|deprecated|retired
