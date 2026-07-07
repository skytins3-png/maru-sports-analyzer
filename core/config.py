import os
from dataclasses import dataclass
import streamlit as st


@dataclass
class AppConfig:
    sports_api_key: str = ""
    sportmonks_api_token: str = ""
    skytoto_sports_api_provider: str = "sportmonks"
    skytoto_sports_api_url: str = ""
    odds_api_key: str = ""
    weather_api_key: str = ""
    gas_webapp_url: str = ""
    google_sheet_id: str = ""
    use_slow_api: bool = True

    @classmethod
    def from_env(cls):
        return cls(
            sports_api_key=os.getenv("SPORTS_API_KEY", ""),
            sportmonks_api_token=os.getenv("SPORTMONKS_API_TOKEN", os.getenv("SPORTS_API_KEY", "")),
            skytoto_sports_api_provider=os.getenv("SKYTOTO_SPORTS_API_PROVIDER", "sportmonks"),
            skytoto_sports_api_url=os.getenv("SKYTOTO_SPORTS_API_URL", ""),
            odds_api_key=os.getenv("ODDS_API_KEY", ""),
            weather_api_key=os.getenv("WEATHER_API_KEY", ""),
            gas_webapp_url=os.getenv("GAS_WEBAPP_URL", ""),
            google_sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
            use_slow_api=os.getenv("USE_SLOW_API", "Y").upper() in ("Y", "YES", "TRUE", "1"),
        )

    @classmethod
    def from_streamlit_secrets(cls):
        env_cfg = cls.from_env()
        try:
            secrets = st.secrets
            return cls(
                sports_api_key=secrets.get("SPORTS_API_KEY", env_cfg.sports_api_key),
                sportmonks_api_token=secrets.get("SPORTMONKS_API_TOKEN", secrets.get("SPORTS_API_KEY", env_cfg.sportmonks_api_token)),
                skytoto_sports_api_provider=secrets.get("SKYTOTO_SPORTS_API_PROVIDER", env_cfg.skytoto_sports_api_provider),
                skytoto_sports_api_url=secrets.get("SKYTOTO_SPORTS_API_URL", env_cfg.skytoto_sports_api_url),
                odds_api_key=secrets.get("ODDS_API_KEY", env_cfg.odds_api_key),
                weather_api_key=secrets.get("WEATHER_API_KEY", env_cfg.weather_api_key),
                gas_webapp_url=secrets.get("GAS_WEBAPP_URL", env_cfg.gas_webapp_url),
                google_sheet_id=secrets.get("GOOGLE_SHEET_ID", env_cfg.google_sheet_id),
                use_slow_api=str(secrets.get("USE_SLOW_API", env_cfg.use_slow_api)).upper() not in ("N", "NO", "FALSE", "0"),
            )
        except Exception:
            return env_cfg
