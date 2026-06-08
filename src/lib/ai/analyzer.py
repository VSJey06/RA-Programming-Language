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
            'loops': [],
            'conditions': [],
            'errors': []
        }

        class_pattern = syntax['class_pattern']
        for match in re.finditer(class_pattern, code):
            result['classes'].append(match.group(1))

        method_pattern = syntax['method_pattern']
        for match in re.finditer(method_pattern, code):
            result['methods'].append(match.group(1))

        var_pattern = syntax['variable_pattern']
        for match in re.finditer(var_pattern, code, re.MULTILINE):
            var_type = match.group(1)
            var_name = match.group(2)
            result['variables'].append({'name': var_name, 'type': var_type})

        loop_pattern = syntax['loop_pattern']
        for match in re.finditer(loop_pattern, code):
            result['loops'].append(match.group(1))

        cond_pattern = syntax['condition_pattern']
        for match in re.finditer(cond_pattern, code):
            result['conditions'].append(match.group(1))

        return result

    @staticmethod
    def explain(code: str) -> str:
        structure = Analyzer.analyze_structure(code)
        lines = []
        if structure['classes']:
            lines.append(f"This code defines classes: {', '.join(structure['classes'])}.")
        if structure['methods']:
            lines.append(f"It contains methods: {', '.join(structure['methods'])}.")
        if structure['variables']:
            names = [v['name'] for v in structure['variables']]
            lines.append(f"Variables declared: {', '.join(names)}.")
        if structure['loops']:
            lines.append(f"Uses loops: {', '.join(structure['loops'])}.")
        if structure['conditions']:
            lines.append(f"Contains conditionals.")
        if not any([structure['classes'], structure['methods'], structure['variables'],
                     structure['loops'], structure['conditions']]):
            lines.append("The code snippet has no recognizable RA structure.")
        return " ".join(lines)
