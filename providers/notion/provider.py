from providers.base import Provider

class NotionProvider(Provider):
    @property
    def name(self):
        return "notion"

    def invoke(self, prompt: str) -> str:
        return "Notion MCP provider scaffold"
