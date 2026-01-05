"""Image upload handling for byte streams"""
import logging
import base64
from livekit.agents.llm import ImageContent

logger = logging.getLogger("agent-Alex-2f2")


async def handle_image_upload(agent, reader, participant_identity: str) -> None:
    """Handle image uploads from the frontend via byte stream"""
    try:
        chunks = []
        async for chunk in reader:
            chunks.append(chunk)
        image_bytes = b''.join(chunks)
        image_data_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        chat_ctx = agent.chat_ctx.copy()
        chat_ctx.add_message(role="user", content=["I'm sharing an image with you", ImageContent(image=image_data_url)])
        await agent.update_chat_ctx(chat_ctx)
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)





