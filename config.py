from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    OPENAI_API_KEY: str

    OPENAI_BASE_URL: str

    LLM_MODEL: str


_cached_settings = None


def _find_env_file():
    """优先使用当前目录的 .env，其次回落到工具自身目录。"""

    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
    ]

    for candidate in candidates:

        if candidate.exists():
            return candidate

    return None


def get_settings() -> Settings:
    """
    延迟加载配置。

    导入模块或显示帮助时不应要求密钥，只有真正调用模型前才校验。
    缺少配置时由 Pydantic 抛出 ValidationError。
    """

    global _cached_settings

    if _cached_settings is None:

        env_file = _find_env_file()

        if env_file is not None:

            _cached_settings = Settings(_env_file=env_file)

        else:

            _cached_settings = Settings()

    return _cached_settings


class _LazySettings:
    """
    兼容原有的 `from config import settings` 用法。

    属性访问时才真正读取配置，模块导入阶段不做校验。
    测试通过替换 sys.modules["config"] 提供的 settings 仍旧生效。
    """

    def __getattr__(self, name):

        return getattr(get_settings(), name)


settings = _LazySettings()