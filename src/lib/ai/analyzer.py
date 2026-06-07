import re
from .knowledge import KnowledgeBase

class Analyzer:
    @staticmethod
    def analyze_structure(code: str) -> dict:
        syntax = KnowledgeBase.get_syntax()
        result = {
            'classes': [],
            'methods': [],
            'variables': [],
            'errors': []
        }

        # Class extraction
        class_pattern = syntax['class_pattern']
        for match in re.finditer(class_pattern, code):
            result['classes'].append(match.group(1))

        # Method extraction
        method_pattern = syntax['method_pattern']
        for match in re.finditer(method_pattern, code):
            result['methods'].append({
                'name': match.group(1),
                'params': match.group(2)
            })

        # Variable extraction
        var_pattern = syntax['variable_pattern']
        for match in re.finditer(var_pattern, code):
            result['variables'].append(match.group(1))

        return result

    @staticmethod
    def explain(code: str) -> str:
        structure = Analyzer.analyze_structure(code)
        lines = []
        if structure['classes']:
            lines.append(f"This code defines classes: {', '.join(structure['classes'])}.")
        if structure['methods']:
            methods = [m['name'] for m in structure['methods']]
            lines.append(f"It contains methods: {', '.join(methods)}.")
        if structure['variables']:
            lines.append(f"Variables declared: {', '.join(structure['variables'])}.")
        if not any([structure['classes'], structure['methods'], structure['variables']]):
            lines.append("The code snippet has no recognizable RA structure.")
        return " ".join(lines)