# ---------------------------------------------------
# File Name: __init__.py
# Description: Auto-discover and load bot modules
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import glob
import logging
from os.path import basename, dirname, isfile, join

# Configure module loader logging
logger = logging.getLogger(__name__)

def __list_all_modules():
    """Dynamically discover all Python modules in the current directory"""
    try:
        module_dir = dirname(__file__)
        mod_paths = glob.glob(join(module_dir, "*.py"))
        
        all_modules = [
            basename(f)[:-3]  # Remove .py extension
            for f in mod_paths
            if isfile(f) and not basename(f).startswith('__')
        ]
        
        logger.info(f"✅ Loaded {len(all_modules)} modules: {sorted(all_modules)}")
        return sorted(all_modules)
        
    except Exception as e:
        logger.error(f"❌ Module loading failed: {e}")
        return []

# Auto-discover modules
ALL_MODULES = __list_all_modules()
__all__ = ALL_MODULES + ["ALL_MODULES"]
