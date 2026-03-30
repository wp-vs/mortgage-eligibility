from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.banking import BankingAnalysis, BankingConnection
from app.models.customer import Customer
from app.schemas.banking import (
    BankingAnalysisResponse,
    BankingCallbackRequest,
    BankingConnectRequest,
    BankingConnectResponse,
    BankingConnectionResponse,
)
from app.services.truelayer import TrueLayerService

router = APIRouter()


@router.post("/connect", response_model=BankingConnectResponse)
async def initiate_banking_connection(
    request: BankingConnectRequest, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Customer).where(Customer.id == request.customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    tl_service = TrueLayerService()
    connection = BankingConnection(customer_id=customer.id)
    db.add(connection)
    await db.commit()
    await db.refresh(connection)

    auth_url = tl_service.get_auth_url(connection.id)
    return BankingConnectResponse(auth_url=auth_url, connection_id=connection.id)


@router.post("/callback")
async def banking_callback(
    request: BankingCallbackRequest, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BankingConnection).where(BankingConnection.id == request.connection_id)
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    tl_service = TrueLayerService()

    # Exchange code for access token
    token_data = await tl_service.exchange_code(request.code)
    connection.access_token = token_data["access_token"]
    connection.status = "connected"
    await db.commit()

    # Fetch and analyse transactions
    from app.services.expense_analyser import ExpenseAnalyser
    from app.services.income_analyser import IncomeAnalyser

    transactions = await tl_service.get_transactions(connection.access_token)
    accounts = await tl_service.get_accounts(connection.access_token)

    if accounts:
        connection.provider_name = accounts[0].get("provider", {}).get("display_name")
        await db.commit()

    income_analyser = IncomeAnalyser()
    expense_analyser = ExpenseAnalyser()

    income_result = income_analyser.analyse(transactions)
    expense_result = expense_analyser.analyse(transactions)

    analysis = BankingAnalysis(
        customer_id=connection.customer_id,
        salary_frequency=income_result.get("frequency"),
        salary_regularity_score=income_result.get("regularity_score"),
        average_salary=income_result.get("average_salary"),
        salary_variation_pct=income_result.get("variation_pct"),
        flagged_expenses=expense_result.get("flagged_expenses"),
        estimated_monthly_rent=expense_result.get("estimated_monthly_rent"),
        total_monthly_commitments=expense_result.get("total_monthly_commitments"),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    return {"status": "connected", "analysis_id": analysis.id}


@router.get("/{customer_id}/status", response_model=BankingConnectionResponse | None)
async def get_banking_status(customer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BankingConnection)
        .where(BankingConnection.customer_id == customer_id)
        .order_by(BankingConnection.created_at.desc())
    )
    connection = result.scalar_one_or_none()
    return connection


@router.get("/{customer_id}/analysis", response_model=BankingAnalysisResponse | None)
async def get_banking_analysis(customer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BankingAnalysis)
        .where(BankingAnalysis.customer_id == customer_id)
        .order_by(BankingAnalysis.analysis_date.desc())
    )
    analysis = result.scalar_one_or_none()
    return analysis
