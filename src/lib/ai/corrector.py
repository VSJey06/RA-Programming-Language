import re
from .knowledge import KnowledgeBase

class Corrector:
    @staticmethod
    def human_friendly_error(raw_error: str) -> str:
        errors_db = KnowledgeBase.get_errors()
        suggestions_db = errors_db.get('common_suggestions', {})

        # Check parser errors
        for err_type, err_info in errors_db.get('parser_errors', {}).items():
            pattern = err_info['pattern']
            match = re.search(pattern, raw_error, re.IGNORECASE)
            if match:
                keyword = match.group(1) if match.groups() else ""
                msg = err_info['message'].replace('{keyword}', keyword)
                if keyword in suggestions_db:
                    sug = err_info['suggestion'].replace('{suggestions}', suggestions_db[keyword])
                    return f"{msg}\n{sug}"
                return msg

        # Check runtime errors
        for err_type, err_info in errors_db.get('runtime_errors', {}).items():
            pattern = err_info['pattern']
            match = re.search(pattern, raw_error, re.IGNORECASE)
            if match:
                name = match.group(1) if match.groups() else "unknown"
                msg = err_info['message'].replace('{name}', name)
                return msg

        return f"Error: {raw_error}"