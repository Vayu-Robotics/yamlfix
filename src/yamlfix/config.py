"""Define the configuration of the main program."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from maison.config import ProjectConfig

from yamlfix.model import YamlfixConfig

log = logging.getLogger(__name__)


def configure_yamlfix(
    yamlfix_config: YamlfixConfig,
    config_files: Optional[List[str]] = None,
    additional_config: Optional[Dict[str, str]] = None,
) -> None:
    """Configure the YamlfixConfig object from .toml/.ini configuration files \
        and additional config overrides."""
    config_path: Optional[Path] = None

    if additional_config:
        config_path_env: Optional[str] = additional_config.get("config_path")
        if config_path_env:
            config_path = Path(config_path_env)
    
    # If config files are provided but no starting path, use the directory of the first config file
    if config_files and not config_path:
        config_path = Path(config_files[0]).parent

    log.debug("Loading config with source_files=%s, starting_path=%s", config_files, config_path)

    config: ProjectConfig = ProjectConfig(
        config_schema=YamlfixConfig,
        merge_configs=True,
        project_name="yamlfix",
        source_files=config_files,
        starting_path=config_path,
    )
    config_dict: Dict[str, Any] = config.to_dict()
    log.debug("Raw config dict: %s", config_dict)

    # Extract yamlfix-specific configuration from tool.yamlfix section if present
    yamlfix_section = config_dict.get("tool", {}).get("yamlfix", {})
    if yamlfix_section:
        log.debug("Found yamlfix section: %s", yamlfix_section)
        # Merge yamlfix section into the main config dict
        for key, value in yamlfix_section.items():
            config_dict[key] = value

    if additional_config:
        for override_key, override_val in additional_config.items():
            config_dict[override_key] = override_val

    config.validate()
    
    # After validation, check if the schema-mapped config is working
    schema_config_dict = config.to_dict()
    log.debug("Schema config dict: %s", schema_config_dict)
    
    # If the schema didn't pick up the yamlfix section, use our manual extraction
    if yamlfix_section and not schema_config_dict.get("exclude_dirs"):
        log.debug("Schema mapping failed, using manual extraction")
        config_dict = schema_config_dict
        for key, value in yamlfix_section.items():
            if hasattr(yamlfix_config, key):
                config_dict[key] = value
    else:
        config_dict = schema_config_dict
    
    log.debug("Final config dict: %s", config_dict)

    for config_key, config_val in config_dict.items():
        if hasattr(yamlfix_config, config_key):
            log.debug("Setting %s = %s", config_key, config_val)
            setattr(yamlfix_config, config_key, config_val)
