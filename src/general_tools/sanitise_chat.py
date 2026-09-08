from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

def sanitize_history(history: list[ModelMessage], max_messages: int = 10) -> list[ModelMessage]:
    """
    Extracts purely clean User/Assistant text turns from prior history,
    completely stripping tool mechanics to guarantee OpenAI API compatibility.
    """
    if not history:
        return []

    clean_history: list[ModelMessage] = []

    for msg in history:
        if isinstance(msg, ModelRequest):
            # Extract only true user text inputs (ignoring System prompts & Tool returns)
            user_parts = [p for p in msg.parts if isinstance(p, UserPromptPart)]
            if user_parts:
                clean_history.append(ModelRequest(parts=user_parts, instructions=msg.instructions))

        elif isinstance(msg, ModelResponse):
            # Extract only text responses (ignoring ToolCallParts)
            text_parts = [p for p in msg.parts if isinstance(p, TextPart) and p.content.strip()]
            if text_parts:
                clean_history.append(ModelResponse(parts=text_parts, model_name=msg.model_name, timestamp=msg.timestamp))

    # Return only the most recent N conversational turns
    return clean_history[-max_messages:]