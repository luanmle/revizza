API_BASE_URL = "https://revizza-api-37fd874aff98.herokuapp.com/api/v1"
SUPABASE_URL = "https://dbluidhmkpdkallwpzgc.supabase.co"
# Chave publicável do cliente; nunca substituir por service_role/sb_secret_.
SUPABASE_ANON_KEY = "sb_publishable_jVxfN_0wgwjJl5m5yxuo4Q_ObKZIcQ5"


def connection_settings(config: dict) -> dict[str, str]:
    return {
        "api_base_url": config.get("api_base_url") or API_BASE_URL,
        "supabase_url": config.get("supabase_url") or SUPABASE_URL,
        "supabase_anon_key": config.get("supabase_anon_key") or SUPABASE_ANON_KEY,
    }
