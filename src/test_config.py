#!/usr/bin/env python3

from yamlfix.config import configure_yamlfix
from yamlfix.model import YamlfixConfig

def test_config():
    config = YamlfixConfig()
    print("Before configuration:")
    print(f"  exclude_dirs: {config.exclude_dirs}")
    print(f"  line_length: {config.line_length}")
    print(f"  sequence_style: {config.sequence_style}")
    
    # Test with explicit config file
    configure_yamlfix(config, ['/home/arul/vayu-school/pyproject.toml'])
    
    print("\nAfter configuration:")
    print(f"  exclude_dirs: {config.exclude_dirs}")
    print(f"  line_length: {config.line_length}")
    print(f"  sequence_style: {config.sequence_style}")

if __name__ == "__main__":
    test_config() 