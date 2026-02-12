"""Configuration management for Knowledge Corpus Manager.

Loads settings from config.yaml with environment variable overrides.
"""

import os
from pathlib import Path

import yaml


DEFAULT_CONFIG = {
    "corpus": {
        "root_path": "",
    },
    "database": {
        "path": str(Path.home() / ".kcm" / "corpus.db"),
    },
    "consolidation": {
        "output_dir": str(Path.home() / ".kcm" / "exports"),
    },
    "server": {
        "host": "127.0.0.1",
        "port": 5000,
        "debug": True,
    },
    "indexer": {
        "skip_patterns": ["~$*", "*.tmp", "Thumbs.db", ".DS_Store"],
        "supported_extensions": [".md", ".docx", ".xlsx", ".pdf", ".vsdx", ".txt", ".csv"],
    },
}

# Maps environment variable names to config paths
ENV_OVERRIDES: dict[str, tuple[str, str]] = {
    "KCM_CORPUS_ROOT": ("corpus", "root_path"),
    "KCM_DATABASE_PATH": ("database", "path"),
    "KCM_PORT": ("server", "port"),
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override dict into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str | None = None) -> dict:
    """Load configuration from YAML file with environment variable overrides.

    Args:
        config_path: Path to config.yaml. Defaults to project root config.yaml.

    Returns:
        Merged configuration dictionary.
    """
    config = DEFAULT_CONFIG.copy()
    config = _deep_merge(DEFAULT_CONFIG, {})

    # Load YAML config if it exists
    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "config.yaml")

    yaml_path = Path(config_path)
    if yaml_path.exists():
        with open(yaml_path, "r") as f:
            yaml_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, yaml_config)

    # Apply environment variable overrides
    for env_var, (section, key) in ENV_OVERRIDES.items():
        value = os.environ.get(env_var)
        if value is not None:
            if key == "port":
                value = int(value)
            config[section][key] = value

    # Expand ~ in paths
    config["database"]["path"] = str(Path(config["database"]["path"]).expanduser())
    config["consolidation"]["output_dir"] = str(
        Path(config["consolidation"]["output_dir"]).expanduser()
    )
    if config["corpus"]["root_path"]:
        config["corpus"]["root_path"] = str(
            Path(config["corpus"]["root_path"]).expanduser()
        )

    return config
