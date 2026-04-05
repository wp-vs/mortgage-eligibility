import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.schemas.chat import ChatRequest
from app.services.llm_agent import MortgageAgent

router = APIRouter()


@router.post("/send")
async def send_message(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == request.customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get or create conversation
    conv_result = await db.execute(
        select(Conversation).where(Conversation.customer_id == customer.id)
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(customer_id=customer.id, messages=[])
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    agent = MortgageAgent(db, customer, conversation)
    response = await agent.process_message(request.message)

    return {
        "customer_id": customer.id,
        "conversation_id": conversation.id,
        "message": response["message"],
        "tool_calls": response.get("tool_calls"),
        "ui_actions": response.get("ui_actions"),
    }


@router.post("/stream")
async def stream_message(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == request.customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    conv_result = await db.execute(
        select(Conversation).where(Conversation.customer_id == customer.id)
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(customer_id=customer.id, messages=[])
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    agent = MortgageAgent(db, customer, conversation)

    async def event_generator():
        async for chunk in agent.stream_message(request.message):
            yield {"event": chunk["event"], "data": json.dumps(chunk["data"])}

    return EventSourceResponse(event_generator())


@router.get("/{customer_id}/history")
async def get_conversation_history(
    customer_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Conversation).where(Conversation.customer_id == customer_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        return {"messages": []}
    return {"messages": conversation.messages}
