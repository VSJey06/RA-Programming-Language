from .analyzer import Analyzer
from .corrector import Corrector

def Assist(code_or_query: str) -> str:
    """Analyse existing RA code and suggest improvements."""
    # Assume input is RA code if it contains typical RA keywords
    if '@Cls' in code_or_query or '@Method' in code_or_query:
        structure = Analyzer.analyze_structure(code_or_query)
        suggestions = []
        if not structure['methods']:
            suggestions.append("No methods found. Consider adding @Method definitions.")
        if len(structure['classes']) == 0:
            suggestions.append("No class defined. Wrap code inside @Cls.")
        if suggestions:
            return "Improvements:\n- " + "\n- ".join(suggestions)
        else:
            return "Code structure looks good. No immediate improvements needed."
    else:
        # Treat as error message to correct
        return Corrector.human_friendly_error(code_or_query)