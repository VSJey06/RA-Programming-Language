import json
import os
from pathlib import Path

class VersionManager:
    _current_version = None
    _cache = {}

    @classmethod
    def check_and_reload(cls):
        version_path = Path(__file__).parent / "version.json"
        with open(version_path, 'r') as f:
            data = json.load(f)
        new_version = data['version']

        cache_file = Path(__file__).parent / data.get('cache_file', '.ai_cache.json')
        if cache_file.exists():
            with open(cache_file, 'r') as cf:
                cls._cache = json.load(cf)
            old_version = cls._cache.get('version')
        else:
            old_version = None

        if new_version != old_version:
            cls._reload_knowledge()
            cls._cache['version'] = new_version
            with open(cache_file, 'w') as cf:
                json.dump(cls._cache, cf)

    @classmethod
    def _reload_knowledge(cls):
        from .knowledge import KnowledgeBase
        KnowledgeBase.reload()