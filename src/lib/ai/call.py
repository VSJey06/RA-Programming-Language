from .analyzer import Analyzer
from .corrector import Corrector
from .knowledge import KnowledgeBase

def Call(query: str) -> str:
    """Answer RA‑related questions (no chatbot, pure RA intelligence)."""
    query_lower = query.lower()

    if "explain inheritance" in query_lower:
        return ("In RA, inheritance is achieved using the '@Cls Child : Parent' syntax.\n"
                "Example:\n"
                "  @Cls Animal:\n"
                "    @Method speak():\n"
                "      .Print(\"Some sound\")\n"
                "  @Cls Dog : Animal:\n"
                "    @Method speak():\n"
                "      .Print(\"Woof\")")
    elif "syntax" in query_lower:
        syntax = KnowledgeBase.get_syntax()
        return f"RA keywords: {', '.join(syntax['keywords'])}"
    elif "error" in query_lower:
        return "Use .Assist with your code to analyse errors."
    else:
        return ("I am the RA Language Intelligence Engine.\n"
                "Ask me about RA syntax, errors, libraries, or code structure.")