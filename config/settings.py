"""
Library AI Agent - Configuration Settings
IBM Cloud Lite + watsonx.ai Studio Integration
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WatsonxConfig:
    """IBM watsonx.ai Studio configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("WATSONX_API_KEY", ""))
    project_id: str = field(default_factory=lambda: os.getenv("WATSONX_PROJECT_ID", ""))
    url: str = field(default_factory=lambda: os.getenv(
        "WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
    ))
    # Foundation model identifiers available on IBM watsonx.ai
    default_model: str = "ibm/granite-13b-instruct-v2"
    chat_model: str = "ibm/granite-13b-chat-v2"
    embedding_model: str = "ibm/slate-125m-english-rtrvr"

    # Generation parameters
    max_new_tokens: int = 512
    min_new_tokens: int = 10
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1


@dataclass
class WatsonNLUConfig:
    """IBM Watson Natural Language Understanding configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("WATSON_NLU_API_KEY", ""))
    url: str = field(default_factory=lambda: os.getenv(
        "WATSON_NLU_URL", "https://api.us-south.natural-language-understanding.watson.cloud.ibm.com"
    ))
    version: str = "2022-04-07"


@dataclass
class DatabaseConfig:
    """IBM Cloud database configuration (Db2 on Cloud / PostgreSQL)."""
    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    name: str = field(default_factory=lambda: os.getenv("DB_NAME", "library_db"))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "library_admin"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    ssl_mode: str = "require"
    # Connection pool settings
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class CloudantConfig:
    """IBM Cloudant NoSQL database configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("CLOUDANT_API_KEY", ""))
    url: str = field(default_factory=lambda: os.getenv("CLOUDANT_URL", ""))
    db_name: str = "library_profiles"


@dataclass
class IBMCloudConfig:
    """IBM Cloud Functions and general cloud configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("IBM_CLOUD_API_KEY", ""))
    region: str = field(default_factory=lambda: os.getenv("IBM_CLOUD_REGION", "us-south"))
    namespace: str = field(default_factory=lambda: os.getenv(
        "IBM_CLOUD_FUNCTIONS_NAMESPACE", "library-agent"
    ))


@dataclass
class GoogleOAuthConfig:
    """Google OAuth 2.0 configuration."""
    client_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", ""))
    client_secret: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", ""))
    redirect_uri: str = field(default_factory=lambda: os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:5000/api/auth/google/callback"
    ))
    # Google OAuth endpoints
    auth_uri: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_uri: str = "https://oauth2.googleapis.com/token"
    userinfo_uri: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    scopes: list = field(default_factory=lambda: [
        "openid", "email", "profile"
    ])


@dataclass
class AppConfig:
    """Main application configuration."""
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "5000")))
    secret_key: str = field(default_factory=lambda: os.getenv(
        "SECRET_KEY", "library-agent-dev-secret-key-change-in-production"
    ))
    cors_origins: list = field(default_factory=lambda: ["*"])

    # Feature flags
    use_watsonx: bool = field(default_factory=lambda: os.getenv("USE_WATSONX", "true").lower() == "true")
    use_watson_nlu: bool = field(default_factory=lambda: os.getenv("USE_WATSON_NLU", "true").lower() == "true")
    use_cloudant: bool = field(default_factory=lambda: os.getenv("USE_CLOUDANT", "false").lower() == "true")
    use_demo_mode: bool = field(default_factory=lambda: os.getenv("DEMO_MODE", "false").lower() == "true")

    # Auth
    session_lifetime_days: int = 7
    jwt_secret: str = field(default_factory=lambda: os.getenv(
        "JWT_SECRET", "library-jwt-secret-change-in-production"
    ))

    # Recommendation engine settings
    max_recommendations: int = 10
    similarity_threshold: float = 0.6
    profile_weight: float = 0.4
    query_weight: float = 0.6

    # Reservation settings
    loan_period_days: int = 14
    max_renewals: int = 2
    max_books_per_student: int = 5
    reservation_hold_days: int = 3


# Singleton config instances
watsonx_config = WatsonxConfig()
watson_nlu_config = WatsonNLUConfig()
database_config = DatabaseConfig()
cloudant_config = CloudantConfig()
ibm_cloud_config = IBMCloudConfig()
app_config = AppConfig()
google_oauth_config = GoogleOAuthConfig()
