"""Command line interface definition."""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from _io import TextIOWrapper

from yamlfix import services, version
from yamlfix.config import configure_yamlfix
from yamlfix.entrypoints import load_logger
from yamlfix.model import YamlfixConfig

log = logging.getLogger(__name__)


def _matches_any_glob(
    file_to_test: Path, dir_: Path, globs: Optional[List[str]]
) -> bool:
    return any(file_to_test in dir_.glob(glob) for glob in (globs or []) if glob)

def _find_all_yaml_files(
    dir_: Path, include_globs: Optional[List[str]], exclude_globs: Optional[List[str]]
) -> List[Path]:
    include_files = []
    for include_glob in (include_globs or []):
        if include_glob:
            include_files.extend(dir_.rglob(include_glob))
    return [
        file
        for file in include_files
        if not _matches_any_glob(file, dir_, exclude_globs) and os.path.isfile(file)
    ]



@click.command()
@click.version_option(version="", message=version.version_info())
@click.option("--verbose", "-v", help="Enable verbose logging.", count=True)
@click.option(
    "--check",
    is_flag=True,
    help="Check if file(s) needs fixing. No files will be written in this case.",
)
@click.option(
    "--config-file",
    "-c",
    multiple=True,
    type=str,
    help="Path to a custom configuration file.",
)
@click.option(
    "--env-prefix",
    type=str,
    default="YAMLFIX",
    help="Read yamlfix relevant environment variables starting with this prefix.",
)
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    type=str,
    help="Files matching this glob pattern will be ignored.",
)
@click.option(
    "--include",
    "-i",
    multiple=True,
    type=str,
    default=["*.yaml", "*.yml"],
    help=(
        "Files matching this glob pattern will be included, "
        "unless they are also excluded. Default to '*.yaml' and '*.yml'."
    ),
)
@click.argument("files", type=str, required=True, nargs=-1)
def cli(  # pylint: disable=too-many-arguments
    files: Tuple[str],
    verbose: bool,
    check: bool,
    config_file: Optional[List[str]],
    include: Optional[List[str]],
    exclude: Optional[List[str]],
    env_prefix: str,
) -> None:
    """Corrects the source code of the specified files.

    Specify directory to recursively fix all yaml files in it.

    Use - to read from stdin. No other files can be specified in this case.
    """
    load_logger(verbose)
    
    files_to_fix: List[TextIOWrapper] = []
    if "-" in files:
        if len(files) > 1:
            raise ValueError("Cannot specify '-' and other files at the same time.")
        files_to_fix = [sys.stdin]
    else:
        # Load configuration early to get exclude_dirs
        config = YamlfixConfig()
        if verbose:
            log.info("Config before loading: exclude_dirs=%s", config.exclude_dirs)
        configure_yamlfix(
            config, config_file, _parse_env_vars_as_yamlfix_config(env_prefix.lower())
        )
        if verbose:
            log.info("Config after loading: exclude_dirs=%s", config.exclude_dirs)
        
        # Merge CLI exclude arguments with configuration exclude_dirs
        all_excludes = list(exclude or [])
        if config.exclude_dirs:
            all_excludes.extend(config.exclude_dirs)
        
        if verbose:
            log.info("Exclude patterns: %s", all_excludes)
        
        paths = [Path(file) for file in files]
        real_files = []
        for provided_file in paths:
            if provided_file.is_dir():
                found_files = _find_all_yaml_files(provided_file, include, all_excludes)
                if verbose:
                    log.info("Found %d YAML files in %s", len(found_files), provided_file)
                    for f in found_files:
                        log.info("  %s", f)
                real_files.extend(found_files)
            else:
                real_files.append(provided_file)
        files_to_fix = [file.open("r+") for file in real_files]
    if not files_to_fix:
        log.warning("No YAML files found!")
        sys.exit(0)

    log.info("YamlFix: %s files", "Checking" if check else "Fixing")

    # If config wasn't loaded yet (stdin case), load it now
    if 'config' not in locals():
        config = YamlfixConfig()
        configure_yamlfix(
            config, config_file, _parse_env_vars_as_yamlfix_config(env_prefix.lower())
        )

    fixed_code, changed = services.fix_files(files_to_fix, check, config)
    for file_to_close in files_to_fix:
        file_to_close.close()

    if fixed_code is not None:
        print(fixed_code, end="")

    if changed and check:
        sys.exit(1)


def _parse_env_vars_as_yamlfix_config(env_prefix: str) -> Dict[str, str]:
    prefix_length = len(env_prefix) + 1  # prefix with underscore / delimiter (+1)
    additional_config: Dict[str, str] = {}

    for env_key, env_val in os.environ.items():
        sanitized_key = env_key.lower()

        if sanitized_key.startswith(env_prefix) and len(sanitized_key) > prefix_length:
            additional_config[sanitized_key[prefix_length:]] = env_val

    return additional_config


if __name__ == "__main__":  # pragma: no cover
    cli()  # pylint: disable=E1120
