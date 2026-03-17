import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    @property
    def AWS_BEARER_TOKEN_BEDROCK(self) -> str:
        return os.getenv("AWS_BEARER_TOKEN_BEDROCK", "")

    @property
    def BEDROCK_REGION(self) -> str:
        return os.getenv("BEDROCK_REGION", "ap-south-1")

    @property
    def BEDROCK_MODEL_ID(self) -> str:
        return os.getenv(
            "BEDROCK_MODEL_ID",
            "apac.anthropic.claude-sonnet-4-20250514-v1:0",
        )

    AVAILABLE_MODELS = {
        "Claude Sonnet 4": "apac.anthropic.claude-sonnet-4-20250514-v1:0",
        "Claude 3.5 Sonnet v2": "apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "Claude 3 Haiku": "apac.anthropic.claude-3-haiku-20240307-v1:0",
    }


Cfg = Config()
