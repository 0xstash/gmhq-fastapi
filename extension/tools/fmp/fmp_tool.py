from __future__ import annotations
from griptape.artifacts import ListArtifact, ErrorArtifact, TextArtifact
from griptape.tools import BaseTool
from griptape.utils.decorators import activity
from schema import Schema, Literal, Optional
from attr import define, field
import requests
import logging


@define
class FMPClient(BaseTool):
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    api_key: str = field(kw_only=True)
    timeout: int = field(default=10, kw_only=True)

    @activity(
        config={
            "description": "Retrieves income statement data for a company using its stock symbol or CIK",
            "schema": Schema(
                {
                    Optional(
                        "symbol",
                        description="Stock symbol of the company (e.g., 'AAPL', 'MSFT')",
                    ): str,
                    Optional(
                        "cik",
                        description="CIK number of the company (e.g., '0000320193')",
                    ): str,
                    Literal(
                        "period",
                        description="Period of the report - either 'quarter' or 'annual'",
                    ): str,
                    Literal(
                        "limit",
                        description="Number of statements to return (default: 4)",
                    ): int,
                }
            ),
        }
    )
    def get_income_statement(self, params: dict) -> ListArtifact | ErrorArtifact:
        try:
            # Validate inputs
            symbol = params["values"].get("symbol")
            cik = params["values"].get("cik")
            if not symbol and not cik:
                return ErrorArtifact("Either symbol or CIK must be provided")

            period = params["values"]["period"].lower()
            if period not in ["quarter", "annual"]:
                return ErrorArtifact("Period must be either 'quarter' or 'annual'")

            limit = params["values"].get("limit", 4)

            # Construct the URL with API key at the end
            identifier = symbol if symbol else cik
            url = f"{self.BASE_URL}/income-statement/{identifier}?apikey={self.api_key}"

            # Other parameters
            request_params = {"period": period, "limit": limit}

            # Make the request
            response = requests.get(url, params=request_params, timeout=self.timeout)
            logging.info(f"Request URL: {response.url}")
            response.raise_for_status()

            statements = response.json()
            if not statements:
                return ErrorArtifact(f"No income statement data found for {identifier}")

            formatted_statements = []

            for statement in statements:
                # Calculate ratios as percentages for better readability
                gross_profit_ratio = statement.get("grossProfitRatio", 0) * 100
                operating_income_ratio = statement.get("operatingIncomeRatio", 0) * 100
                net_income_ratio = statement.get("netIncomeRatio", 0) * 100
                ebitda_ratio = statement.get("ebitdaratio", 0) * 100

                formatted_statement = TextArtifact(
                    f"""
                    Filing Information:
                    - Date: {statement.get('date')}
                    - Symbol: {statement.get('symbol')}
                    - CIK: {statement.get('cik')}
                    - Filing Date: {statement.get('fillingDate')}
                    - Accepted Date: {statement.get('acceptedDate')}
                    - Period: {statement.get('period')}
                    - Calendar Year: {statement.get('calendarYear')}
                    - Currency: {statement.get('reportedCurrency')}
                    
                    Revenue and Profitability:
                    - Revenue: ${statement.get('revenue', 0):,.2f}
                    - Cost of Revenue: ${statement.get('costOfRevenue', 0):,.2f}
                    - Gross Profit: ${statement.get('grossProfit', 0):,.2f}
                    - Gross Profit Margin: {gross_profit_ratio:.2f}%
                    
                    Operating Metrics:
                    - Operating Income: ${statement.get('operatingIncome', 0):,.2f}
                    - Operating Margin: {operating_income_ratio:.2f}%
                    - EBITDA: ${statement.get('ebitda', 0):,.2f}
                    - EBITDA Margin: {ebitda_ratio:.2f}%
                    
                    Expenses Breakdown:
                    - R&D: ${statement.get('researchAndDevelopmentExpenses', 0):,.2f}
                    - SG&A: ${statement.get('sellingGeneralAndAdministrativeExpenses', 0):,.2f}
                    - Total Operating Expenses: ${statement.get('operatingExpenses', 0):,.2f}
                    - Total Costs and Expenses: ${statement.get('costAndExpenses', 0):,.2f}
                    - Depreciation & Amortization: ${statement.get('depreciationAndAmortization', 0):,.2f}
                    
                    Interest and Taxes:
                    - Interest Income: ${statement.get('interestIncome', 0):,.2f}
                    - Interest Expense: ${statement.get('interestExpense', 0):,.2f}
                    - Income Before Tax: ${statement.get('incomeBeforeTax', 0):,.2f}
                    - Income Tax Expense: ${statement.get('incomeTaxExpense', 0):,.2f}
                    
                    Bottom Line:
                    - Net Income: ${statement.get('netIncome', 0):,.2f}
                    - Net Income Margin: {net_income_ratio:.2f}%
                    
                    Per Share Data:
                    - EPS: ${statement.get('eps', 0):.2f}
                    - EPS Diluted: ${statement.get('epsdiluted', 0):.2f}
                    - Weighted Avg Shares Outstanding: {statement.get('weightedAverageShsOut', 0):,.0f}
                    - Weighted Avg Shares Outstanding (Diluted): {statement.get('weightedAverageShsOutDil', 0):,.0f}
                    
                    Links:
                    - SEC Filing: {statement.get('link')}
                    - Final Document: {statement.get('finalLink')}
                    """
                )
                formatted_statements.append(formatted_statement)

            return ListArtifact(formatted_statements)

        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            if hasattr(e.response, "text"):
                logging.error(f"Response content: {e.response.text}")
            return ErrorArtifact(f"Failed to fetch income statement: {str(e)}")
        except Exception as e:
            logging.error(f"Error processing income statement: {e}")
            return ErrorArtifact(f"Error processing income statement: {str(e)}")

    @activity(
        config={
            "description": "Retrieves balance sheet data for a company using its stock symbol or CIK",
            "schema": Schema(
                {
                    Optional(
                        "symbol",
                        description="Stock symbol of the company (e.g., 'AAPL', 'MSFT')",
                    ): str,
                    Optional(
                        "cik",
                        description="CIK number of the company (e.g., '0000320193')",
                    ): str,
                    Literal(
                        "period",
                        description="Period of the report - either 'quarter' or 'annual'",
                    ): str,
                    Literal(
                        "limit",
                        description="Number of statements to return (default: 4)",
                    ): int,
                }
            ),
        }
    )
    def get_balance_sheet(self, params: dict) -> ListArtifact | ErrorArtifact:
        try:
            # Validate inputs
            symbol = params["values"].get("symbol")
            cik = params["values"].get("cik")
            if not symbol and not cik:
                return ErrorArtifact("Either symbol or CIK must be provided")

            period = params["values"]["period"].lower()
            if period not in ["quarter", "annual"]:
                return ErrorArtifact("Period must be either 'quarter' or 'annual'")

            limit = params["values"].get("limit", 4)

            # Construct the URL with API key at the end
            identifier = symbol if symbol else cik
            url = f"{self.BASE_URL}/balance-sheet-statement/{identifier}?apikey={self.api_key}"

            # Other parameters
            request_params = {"period": period, "limit": limit}

            # Make the request
            response = requests.get(url, params=request_params, timeout=self.timeout)
            logging.info(f"Request URL: {response.url}")
            response.raise_for_status()

            statements = response.json()
            if not statements:
                return ErrorArtifact(f"No balance sheet data found for {identifier}")

            formatted_statements = []

            for statement in statements:
                formatted_statement = TextArtifact(
                    f"""
                    Filing Information:
                    - Date: {statement.get('date')}
                    - Symbol: {statement.get('symbol')}
                    - CIK: {statement.get('cik')}
                    - Filing Date: {statement.get('fillingDate')}
                    - Accepted Date: {statement.get('acceptedDate')}
                    - Calendar Year: {statement.get('calendarYear')}
                    - Period: {statement.get('period')}
                    - Currency: {statement.get('reportedCurrency')}
                    
                    Current Assets:
                    - Cash and Cash Equivalents: ${statement.get('cashAndCashEquivalents', 0):,.2f}
                    - Short Term Investments: ${statement.get('shortTermInvestments', 0):,.2f}
                    - Cash and Short Term Investments: ${statement.get('cashAndShortTermInvestments', 0):,.2f}
                    - Net Receivables: ${statement.get('netReceivables', 0):,.2f}
                    - Inventory: ${statement.get('inventory', 0):,.2f}
                    - Other Current Assets: ${statement.get('otherCurrentAssets', 0):,.2f}
                    - Total Current Assets: ${statement.get('totalCurrentAssets', 0):,.2f}
                    
                    Non-Current Assets:
                    - Property, Plant & Equipment (Net): ${statement.get('propertyPlantEquipmentNet', 0):,.2f}
                    - Goodwill: ${statement.get('goodwill', 0):,.2f}
                    - Intangible Assets: ${statement.get('intangibleAssets', 0):,.2f}
                    - Goodwill and Intangible Assets: ${statement.get('goodwillAndIntangibleAssets', 0):,.2f}
                    - Long Term Investments: ${statement.get('longTermInvestments', 0):,.2f}
                    - Tax Assets: ${statement.get('taxAssets', 0):,.2f}
                    - Other Non-Current Assets: ${statement.get('otherNonCurrentAssets', 0):,.2f}
                    - Total Non-Current Assets: ${statement.get('totalNonCurrentAssets', 0):,.2f}
                    
                    Total Assets Summary:
                    - Other Assets: ${statement.get('otherAssets', 0):,.2f}
                    - Total Assets: ${statement.get('totalAssets', 0):,.2f}
                    - Total Investments: ${statement.get('totalInvestments', 0):,.2f}
                    
                    Current Liabilities:
                    - Accounts Payable: ${statement.get('accountPayables', 0):,.2f}
                    - Short Term Debt: ${statement.get('shortTermDebt', 0):,.2f}
                    - Tax Payables: ${statement.get('taxPayables', 0):,.2f}
                    - Deferred Revenue: ${statement.get('deferredRevenue', 0):,.2f}
                    - Other Current Liabilities: ${statement.get('otherCurrentLiabilities', 0):,.2f}
                    - Total Current Liabilities: ${statement.get('totalCurrentLiabilities', 0):,.2f}
                    
                    Non-Current Liabilities:
                    - Long Term Debt: ${statement.get('longTermDebt', 0):,.2f}
                    - Deferred Revenue Non-Current: ${statement.get('deferredRevenueNonCurrent', 0):,.2f}
                    - Deferred Tax Liabilities: ${statement.get('deferredTaxLiabilitiesNonCurrent', 0):,.2f}
                    - Other Non-Current Liabilities: ${statement.get('otherNonCurrentLiabilities', 0):,.2f}
                    - Total Non-Current Liabilities: ${statement.get('totalNonCurrentLiabilities', 0):,.2f}
                    
                    Total Liabilities Summary:
                    - Other Liabilities: ${statement.get('otherLiabilities', 0):,.2f}
                    - Capital Lease Obligations: ${statement.get('capitalLeaseObligations', 0):,.2f}
                    - Total Liabilities: ${statement.get('totalLiabilities', 0):,.2f}
                    - Total Debt: ${statement.get('totalDebt', 0):,.2f}
                    - Net Debt: ${statement.get('netDebt', 0):,.2f}
                    
                    Shareholders' Equity:
                    - Preferred Stock: ${statement.get('preferredStock', 0):,.2f}
                    - Common Stock: ${statement.get('commonStock', 0):,.2f}
                    - Retained Earnings: ${statement.get('retainedEarnings', 0):,.2f}
                    - Accumulated Other Comprehensive Income/Loss: ${statement.get('accumulatedOtherComprehensiveIncomeLoss', 0):,.2f}
                    - Other Total Stockholders Equity: ${statement.get('othertotalStockholdersEquity', 0):,.2f}
                    - Total Stockholders Equity: ${statement.get('totalStockholdersEquity', 0):,.2f}
                    - Total Equity: ${statement.get('totalEquity', 0):,.2f}
                    
                    Balance Check:
                    - Minority Interest: ${statement.get('minorityInterest', 0):,.2f}
                    - Total Liabilities and Stockholders Equity: ${statement.get('totalLiabilitiesAndStockholdersEquity', 0):,.2f}
                    - Total Liabilities and Total Equity: ${statement.get('totalLiabilitiesAndTotalEquity', 0):,.2f}
                    
                    Links:
                    - SEC Filing: {statement.get('link')}
                    - Final Document: {statement.get('finalLink')}
                    """
                )
                formatted_statements.append(formatted_statement)

            return ListArtifact(formatted_statements)

        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            if hasattr(e.response, "text"):
                logging.error(f"Response content: {e.response.text}")
            return ErrorArtifact(f"Failed to fetch balance sheet: {str(e)}")
        except Exception as e:
            logging.error(f"Error processing balance sheet: {e}")
            return ErrorArtifact(f"Error processing balance sheet: {str(e)}")
