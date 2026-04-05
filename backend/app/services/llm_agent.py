import json
import logging

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.banking import BankingAnalysis, BankingConnection
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.services.truelayer import TrueLayerService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a mortgage information assistant for a UK-based mortgage brokerage. \
You help customers explore their borrowing needs by gathering information about \
their financial situation, property requirements, and mortgage preferences.

IMPORTANT REGULATORY NOTICE:
- You are NOT a financial adviser. You do NOT provide mortgage advice.
- You gather information and present product options for informational purposes only.
- All product recommendations will be reviewed by a qualified human broker before \
any formal offer or recommendation is made.
- Always remind customers that a broker will review their case before any decisions are finalised.

YOUR ROLE:
1. Greet the customer warmly and understand their mortgage needs (purchase or remortgage)
2. Gather key information conversationally:
   - Their name and contact details
   - Employment type and annual income
   - Property type, estimated value, and location
   - Deposit amount (for purchases) or current equity (for remortgages)
   - Desired mortgage term
   - Whether they are a first-time buyer
3. When you have enough financial information, suggest connecting their bank account \
via Open Banking so the system can verify income and review expenses
4. Once banking data is available, review the analysis with them
5. When the profile is complete, run product matching to find suitable options
6. Present the top options clearly, explaining key features (rate, fees, term)
7. Explain that a broker will review everything before proceeding

CONVERSATION STYLE:
- Be warm, professional, and reassuring - buying a home is stressful
- Use plain English, not jargon. If you must use a term, explain it briefly
- Ask one or two questions at a time, don't overwhelm
- Acknowledge what the customer tells you before moving on
- If they seem unsure about something, explain the options clearly

UK MORTGAGE CONTEXT:
- LTV = Loan to Value = (mortgage amount / property value) * 100
- Typical max LTV is 95% for first-time buyers, 90% standard
- Income multiples typically 4-4.5x annual salary
- Standard terms: 25-35 years
- Product types: Fixed rate (2/3/5 year), Variable/Tracker, Discount
- Stamp duty thresholds apply (first-time buyer relief available)
"""

TOOLS = [
    {
        "name": "update_customer_profile",
        "description": "Update the customer's profile with information gathered during the conversation. Call this whenever the customer provides personal, financial, or property details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string", "description": "Customer's full name"},
                "email": {"type": "string", "description": "Customer's email address"},
                "phone": {"type": "string", "description": "Customer's phone number"},
                "employment_type": {
                    "type": "string",
                    "enum": ["employed", "self_employed", "contractor", "retired", "other"],
                    "description": "Type of employment",
                },
                "annual_income": {
                    "type": "number",
                    "description": "Annual gross income in GBP",
                },
                "deposit_amount": {
                    "type": "number",
                    "description": "Deposit amount in GBP",
                },
                "property_value": {
                    "type": "number",
                    "description": "Estimated property value in GBP",
                },
                "property_type": {
                    "type": "string",
                    "enum": [
                        "detached",
                        "semi_detached",
                        "terraced",
                        "flat",
                        "bungalow",
                        "new_build",
                        "other",
                    ],
                    "description": "Type of property",
                },
                "mortgage_type": {
                    "type": "string",
                    "enum": ["purchase", "remortgage"],
                    "description": "Whether this is a purchase or remortgage",
                },
                "mortgage_term_years": {
                    "type": "integer",
                    "description": "Desired mortgage term in years",
                },
                "first_time_buyer": {
                    "type": "boolean",
                    "description": "Whether the customer is a first-time buyer",
                },
                "property_location": {
                    "type": "string",
                    "description": "Property location (city/region)",
                },
            },
        },
    },
    {
        "name": "initiate_open_banking",
        "description": "Start the Open Banking connection process so the customer can link their bank account. Call this when you have gathered enough basic financial information and want to verify income/expenses.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "check_banking_status",
        "description": "Check whether the customer has connected their bank account and if analysis is available.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "search_products",
        "description": "Search for mortgage products that match the customer's profile. Call this once you have sufficient information: income, property value, deposit, employment type, and ideally banking analysis.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


class MortgageAgent:
    def __init__(
        self,
        db: AsyncSession,
        customer: Customer,
        conversation: Conversation,
    ):
        self.db = db
        self.customer = customer
        self.conversation = conversation
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    def _build_messages(self) -> list[dict]:
        messages = []
        for msg in self.conversation.messages or []:
            messages.append({"role": msg["role"], "content": msg["content"]})
        return messages

    def _build_context_note(self) -> str:
        c = self.customer
        parts = [f"Customer ID: {c.id}"]
        if c.full_name:
            parts.append(f"Name: {c.full_name}")
        if c.employment_type:
            parts.append(f"Employment: {c.employment_type.value}")
        if c.annual_income:
            parts.append(f"Income: £{c.annual_income:,.0f}")
        if c.property_value:
            parts.append(f"Property value: £{c.property_value:,.0f}")
        if c.deposit_amount:
            parts.append(f"Deposit: £{c.deposit_amount:,.0f}")
        if c.mortgage_type:
            parts.append(f"Type: {c.mortgage_type.value}")
        if c.first_time_buyer is not None:
            parts.append(f"First-time buyer: {'Yes' if c.first_time_buyer else 'No'}")
        return "\n".join(parts)

    async def _handle_tool_call(self, tool_name: str, tool_input: dict) -> dict:
        if tool_name == "update_customer_profile":
            return await self._update_profile(tool_input)
        elif tool_name == "initiate_open_banking":
            return await self._initiate_banking()
        elif tool_name == "check_banking_status":
            return await self._check_banking()
        elif tool_name == "search_products":
            return await self._search_products()
        return {"error": f"Unknown tool: {tool_name}"}

    async def _update_profile(self, fields: dict) -> dict:
        updated = []
        for field, value in fields.items():
            if hasattr(self.customer, field) and value is not None:
                setattr(self.customer, field, value)
                updated.append(field)
        await self.db.commit()
        await self.db.refresh(self.customer)
        return {"updated_fields": updated, "status": "success"}

    async def _initiate_banking(self) -> dict:
        tl_service = TrueLayerService()
        connection = BankingConnection(customer_id=self.customer.id)
        self.db.add(connection)
        await self.db.commit()
        await self.db.refresh(connection)
        auth_url = tl_service.get_auth_url(connection.id)
        return {
            "status": "banking_link_ready",
            "auth_url": auth_url,
            "message": "Open Banking link generated. The customer should click the link to connect their bank.",
        }

    async def _check_banking(self) -> dict:
        result = await self.db.execute(
            select(BankingConnection)
            .where(BankingConnection.customer_id == self.customer.id)
            .order_by(BankingConnection.created_at.desc())
        )
        connection = result.scalar_one_or_none()

        if not connection:
            return {"status": "not_started", "message": "No banking connection initiated."}

        if connection.status.value != "connected":
            return {
                "status": connection.status.value,
                "message": "Banking connection is pending. Customer needs to complete the bank link.",
            }

        # Check for analysis
        analysis_result = await self.db.execute(
            select(BankingAnalysis)
            .where(BankingAnalysis.customer_id == self.customer.id)
            .order_by(BankingAnalysis.analysis_date.desc())
        )
        analysis = analysis_result.scalar_one_or_none()

        if not analysis:
            return {"status": "connected", "message": "Bank connected but analysis not yet complete."}

        result_data = {
            "status": "analysis_complete",
            "salary_frequency": analysis.salary_frequency.value if analysis.salary_frequency else None,
            "salary_regularity_score": analysis.salary_regularity_score,
            "average_salary": float(analysis.average_salary) if analysis.average_salary else None,
            "salary_variation_pct": float(analysis.salary_variation_pct) if analysis.salary_variation_pct else None,
            "estimated_monthly_rent": float(analysis.estimated_monthly_rent) if analysis.estimated_monthly_rent else None,
            "total_monthly_commitments": float(analysis.total_monthly_commitments) if analysis.total_monthly_commitments else None,
            "flagged_expenses": analysis.flagged_expenses or [],
        }
        return result_data

    async def _search_products(self) -> dict:
        from app.services.eligibility import EligibilityEngine
        from app.services.recommendation import RecommendationService

        engine = EligibilityEngine(self.db)
        matches = await engine.find_matches(self.customer)

        if not matches:
            return {"status": "no_matches", "message": "No products matched the customer's profile."}

        rec_service = RecommendationService(self.db)
        recommendations = await rec_service.create_recommendations(
            self.customer, matches[:3]
        )

        # Update customer status
        self.customer.status = "submitted"
        await self.db.commit()

        results = []
        for rec in recommendations:
            results.append({
                "rank": rec["rank"],
                "lender": rec["lender_name"],
                "product": rec["product_name"],
                "rate": rec["rate"],
                "product_type": rec["product_type"],
                "initial_period_months": rec["initial_period_months"],
                "max_ltv": rec["max_ltv"],
                "arrangement_fee": rec["arrangement_fee"],
                "estimated_monthly_payment": rec.get("estimated_monthly_payment"),
                "match_score": rec["match_score"],
                "match_reasons": rec["match_reasons"],
            })

        return {"status": "matched", "top_products": results}

    async def process_message(self, user_message: str) -> dict:
        # Add user message to conversation
        messages = list(self.conversation.messages or [])
        messages.append({"role": "user", "content": user_message})

        context = self._build_context_note()
        system = f"{SYSTEM_PROMPT}\n\nCurrent customer profile:\n{context}"

        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

        ui_actions = []
        tool_calls_made = []

        # Loop to handle tool use
        while True:
            response = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=2048,
                system=system,
                messages=api_messages,
                tools=TOOLS,
            )

            if response.stop_reason == "tool_use":
                # Process tool calls
                assistant_content = response.content
                api_messages.append({"role": "assistant", "content": assistant_content})

                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        result = await self._handle_tool_call(block.name, block.input)
                        tool_calls_made.append(
                            {"tool": block.name, "input": block.input, "result": result}
                        )

                        # Check for UI actions
                        if block.name == "initiate_open_banking" and "auth_url" in result:
                            ui_actions.append({
                                "type": "open_banking_connect",
                                "auth_url": result["auth_url"],
                            })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })

                api_messages.append({"role": "user", "content": tool_results})
            else:
                # Extract text response
                text_parts = [
                    block.text for block in response.content if hasattr(block, "text")
                ]
                assistant_message = "\n".join(text_parts)

                # Save to conversation
                messages.append({"role": "assistant", "content": assistant_message})
                self.conversation.messages = messages
                await self.db.commit()

                return {
                    "message": assistant_message,
                    "tool_calls": tool_calls_made if tool_calls_made else None,
                    "ui_actions": ui_actions if ui_actions else None,
                }

    async def stream_message(self, user_message: str):
        messages = list(self.conversation.messages or [])
        messages.append({"role": "user", "content": user_message})

        context = self._build_context_note()
        system = f"{SYSTEM_PROMPT}\n\nCurrent customer profile:\n{context}"

        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

        full_response = ""

        while True:
            async with self.client.messages.stream(
                model=settings.anthropic_model,
                max_tokens=2048,
                system=system,
                messages=api_messages,
                tools=TOOLS,
            ) as stream:
                tool_use_blocks = []
                current_text = ""

                async for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            if hasattr(event.delta, "text"):
                                current_text += event.delta.text
                                yield {
                                    "event": "text",
                                    "data": {"text": event.delta.text},
                                }

                response = await stream.get_final_message()

                if response.stop_reason == "tool_use":
                    assistant_content = response.content
                    api_messages.append({"role": "assistant", "content": assistant_content})

                    tool_results = []
                    for block in assistant_content:
                        if block.type == "tool_use":
                            result = await self._handle_tool_call(block.name, block.input)

                            if block.name == "initiate_open_banking" and "auth_url" in result:
                                yield {
                                    "event": "ui_action",
                                    "data": {
                                        "type": "open_banking_connect",
                                        "auth_url": result["auth_url"],
                                    },
                                }

                            yield {
                                "event": "tool_call",
                                "data": {"tool": block.name, "status": "complete"},
                            }

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result),
                            })

                    api_messages.append({"role": "user", "content": tool_results})
                else:
                    text_parts = [
                        block.text
                        for block in response.content
                        if hasattr(block, "text")
                    ]
                    full_response = "\n".join(text_parts)

                    messages.append({"role": "assistant", "content": full_response})
                    self.conversation.messages = messages
                    await self.db.commit()

                    yield {"event": "done", "data": {"complete": True}}
                    return
