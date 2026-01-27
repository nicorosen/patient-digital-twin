"""
Web search tool for medical information retrieval.

Allows the Medical Assistant to search the web for:
- Drug interactions and contraindications
- Clinical guidelines and protocols
- Medical literature and PubMed references
"""

from langchain_core.tools import tool

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger("agents.tools.web_search")


@tool
def search_medical_web(query: str) -> str:
    """Search the web for medical information such as drug interactions,
    clinical guidelines, treatment protocols, and medical literature.

    Use this tool when the patient asks about:
    - Drug interactions or side effects
    - Clinical guidelines or treatment recommendations
    - Medical conditions not covered by the patient's records
    - Latest medical research or evidence

    Args:
        query: The medical search query.

    Returns:
        Search results with relevant medical information.
    """
    settings = get_settings()

    if not settings.tavily_api_key:
        return (
            "Web search is not available. The TAVILY_API_KEY environment "
            "variable is not configured."
        )

    try:
        from langchain_community.tools.tavily_search import TavilySearchResults

        search = TavilySearchResults(
            api_key=settings.tavily_api_key,
            max_results=5,
            search_depth="advanced",
            include_answer=True,
        )

        logger.info(f"Searching web for: {query}")
        results = search.invoke(query)

        if not results:
            return "No results found for the given query."

        # Format results
        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            content = result.get("content", "")
            url = result.get("url", "")
            formatted.append(f"{i}. **{title}**\n   {content}\n   Source: {url}")

        return "\n\n".join(formatted)

    except ImportError:
        logger.error("langchain-community or tavily-python not installed")
        return (
            "Web search is not available. Required packages "
            "(langchain-community, tavily-python) are not installed."
        )
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Web search failed: {str(e)}"


WEB_SEARCH_TOOLS = [search_medical_web]
