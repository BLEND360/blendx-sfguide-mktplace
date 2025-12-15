from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf
from crewai.tools import BaseTool


class GetStockInfoTool(BaseTool):
    name: str = "GetStockInfo"
    description: str = (
        "Get basic information about a stock/ticker including company name, sector, industry, etc."
    )

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Get basic information about a stock."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info
        except Exception as e:
            return {"error": f"Error retrieving stock info for {ticker}: {str(e)}"}


class GetHistoricalDataTool(BaseTool):
    name: str = "GetHistoricalData"
    description: str = "Get historical price data for a stock over a specified period."

    def _run(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> Dict[str, Any]:
        """Get historical price data for a stock."""
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period=period, interval=interval)

            # Convert DataFrame to a dictionary for easier handling by the agent
            data = history.reset_index()
            data["Date"] = data["Date"].astype(
                str
            )  # Convert datetime to string for json serialization

            # Calculate basic statistics
            stats = {
                "start_date": data["Date"].iloc[0] if not data.empty else "N/A",
                "end_date": data["Date"].iloc[-1] if not data.empty else "N/A",
                "start_price": (
                    round(data["Close"].iloc[0], 2) if not data.empty else "N/A"
                ),
                "end_price": (
                    round(data["Close"].iloc[-1], 2) if not data.empty else "N/A"
                ),
                "min_price": round(data["Low"].min(), 2) if not data.empty else "N/A",
                "max_price": round(data["High"].max(), 2) if not data.empty else "N/A",
                "price_change": (
                    round(data["Close"].iloc[-1] - data["Close"].iloc[0], 2)
                    if not data.empty
                    else "N/A"
                ),
                "price_change_pct": (
                    round(
                        ((data["Close"].iloc[-1] / data["Close"].iloc[0]) - 1) * 100, 2
                    )
                    if not data.empty
                    else "N/A"
                ),
                "avg_volume": (
                    round(data["Volume"].mean(), 2) if not data.empty else "N/A"
                ),
            }

            # Limit the number of data points to a reasonable amount to avoid overwhelming the agent
            max_points = 30
            if len(data) > max_points:
                step = len(data) // max_points
                sample_data = data.iloc[::step].tail(max_points)
            else:
                sample_data = data

            # Format sample data for the agent
            sample_data_dict = sample_data[
                ["Date", "Open", "High", "Low", "Close", "Volume"]
            ].to_dict("records")

            return {
                "ticker": ticker,
                "period": period,
                "interval": interval,
                "stats": stats,
                "sample_data": sample_data_dict,
            }
        except Exception as e:
            return {"error": f"Error retrieving historical data for {ticker}: {str(e)}"}


class GetIncomeStatementTool(BaseTool):
    name: str = "GetIncomeStatement"
    description: str = (
        "Get income statement for a company showing revenue, expenses, and profit over time."
    )

    def _run(self, ticker: str, period: str = "annual") -> Dict[str, Any]:
        """Get income statement for a company.

        Args:
            ticker: The stock ticker symbol
            period: 'annual' or 'quarterly' (default: 'annual')
        """
        try:
            stock = yf.Ticker(ticker)

            # Choose either quarterly or annual data based on period parameter
            if period.lower() == "quarterly":
                statement = stock.quarterly_income_stmt
                period_type = "quarterly"
            else:  # Default to annual
                statement = stock.income_stmt
                period_type = "annual"

            # Convert DataFrame to dictionary for easier handling by the agent
            statement_dict = {}

            if not statement.empty:
                for col in statement.columns:
                    col_str = (
                        col.strftime("%Y-%m-%d")
                        if hasattr(col, "strftime")
                        else str(col)
                    )
                    statement_dict[col_str] = {
                        row: str(statement.loc[row, col]) for row in statement.index
                    }

            return {
                "ticker": ticker,
                "period": period_type,
                "income_statement": statement_dict,
            }
        except Exception as e:
            return {
                "error": f"Error retrieving income statement for {ticker}: {str(e)}"
            }


class GetBalanceSheetTool(BaseTool):
    name: str = "GetBalanceSheet"
    description: str = (
        "Get balance sheet for a company showing assets, liabilities, and shareholders' equity."
    )

    def _run(self, ticker: str, period: str = "annual") -> Dict[str, Any]:
        """Get balance sheet for a company.

        Args:
            ticker: The stock ticker symbol
            period: 'annual' or 'quarterly' (default: 'annual')
        """
        try:
            stock = yf.Ticker(ticker)

            # Choose either quarterly or annual data based on period parameter
            if period.lower() == "quarterly":
                statement = stock.quarterly_balance_sheet
                period_type = "quarterly"
            else:  # Default to annual
                statement = stock.balance_sheet
                period_type = "annual"

            # Convert DataFrame to dictionary for easier handling by the agent
            statement_dict = {}

            if not statement.empty:
                for col in statement.columns:
                    col_str = (
                        col.strftime("%Y-%m-%d")
                        if hasattr(col, "strftime")
                        else str(col)
                    )
                    statement_dict[col_str] = {
                        row: str(statement.loc[row, col]) for row in statement.index
                    }

            return {
                "ticker": ticker,
                "period": period_type,
                "balance_sheet": statement_dict,
            }
        except Exception as e:
            return {"error": f"Error retrieving balance sheet for {ticker}: {str(e)}"}


class GetCashFlowTool(BaseTool):
    name: str = "GetCashFlow"
    description: str = (
        "Get cash flow statement for a company showing operating, investing, and financing activities."
    )

    def _run(self, ticker: str, period: str = "annual") -> Dict[str, Any]:
        """Get cash flow statement for a company.

        Args:
            ticker: The stock ticker symbol
            period: 'annual' or 'quarterly' (default: 'annual')
        """
        try:
            stock = yf.Ticker(ticker)

            # Choose either quarterly or annual data based on period parameter
            if period.lower() == "quarterly":
                statement = stock.quarterly_cashflow
                period_type = "quarterly"
            else:  # Default to annual
                statement = stock.cashflow
                period_type = "annual"

            # Convert DataFrame to dictionary for easier handling by the agent
            statement_dict = {}

            if not statement.empty:
                for col in statement.columns:
                    col_str = (
                        col.strftime("%Y-%m-%d")
                        if hasattr(col, "strftime")
                        else str(col)
                    )
                    statement_dict[col_str] = {
                        row: str(statement.loc[row, col]) for row in statement.index
                    }

            return {
                "ticker": ticker,
                "period": period_type,
                "cash_flow": statement_dict,
            }
        except Exception as e:
            return {
                "error": f"Error retrieving cash flow statement for {ticker}: {str(e)}"
            }


class GetEarningsTool(BaseTool):
    name: str = "GetEarnings"
    description: str = (
        "Get earnings data including historical earnings dates, EPS estimates vs. actuals."
    )

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Get earnings data for a stock."""
        try:
            stock = yf.Ticker(ticker)

            # Get earnings dates, EPS estimates, and EPS actuals
            earnings_dates = stock.earnings_dates

            # Convert DataFrame to a dictionary
            if earnings_dates is not None and not earnings_dates.empty:
                earnings_dates_dict = earnings_dates.reset_index()
                earnings_dates_dict["Earnings Date"] = earnings_dates_dict[
                    "Earnings Date"
                ].astype(str)
                earnings_dates_dict = earnings_dates_dict.to_dict("records")
            else:
                earnings_dates_dict = []

            return {"ticker": ticker, "earnings_dates": earnings_dates_dict}
        except Exception as e:
            return {"error": f"Error retrieving earnings data for {ticker}: {str(e)}"}


class GetDividendsTool(BaseTool):
    name: str = "GetDividends"
    description: str = (
        "Get historical dividends for a stock. Note: The dividend yield is already calculated as a percentage (e.g., 2.5 means 2.5%)."
    )

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Get dividend information for a stock."""
        try:
            stock = yf.Ticker(ticker)

            # Get dividend data
            dividends = stock.dividends

            # Calculate dividend statistics
            if dividends is not None and not dividends.empty:
                div_df = pd.DataFrame(dividends)
                div_df.index = div_df.index.astype(str)

                # Get the last four quarters if available
                last_year_divs = div_df.tail(4)
                ttm_dividend = last_year_divs.sum() if not last_year_divs.empty else 0

                # Get current price for yield calculation
                current_price = stock.info.get(
                    "currentPrice", stock.info.get("regularMarketPrice", 0)
                )

                # Calculate current yield
                current_yield = (
                    (ttm_dividend / current_price) * 100 if current_price > 0 else 0
                )

                # Format dividend history and sort by date (newest first)
                div_items = [(idx, float(val)) for idx, val in dividends.items()]
                # Sort by date in descending order (newest first)
                div_items.sort(key=lambda x: x[0], reverse=True)
                # Take only the 8 most recent entries
                recent_dividends = div_items[:8]
                # Format for output with dates as strings
                div_history = [
                    {"date": str(idx), "amount": amount}
                    for idx, amount in recent_dividends
                ]

                return {
                    "ticker": ticker,
                    "has_dividends": True,
                    "dividend_yield_percent": round(
                        (
                            float(current_yield.iloc[0])
                            if hasattr(current_yield, "iloc")
                            else current_yield
                        ),
                        2,
                    ),
                    "ttm_dividend": (
                        float(ttm_dividend.iloc[0])
                        if hasattr(ttm_dividend, "iloc")
                        else ttm_dividend
                    ),
                    "current_price": current_price,
                    "dividend_history": div_history,
                }
            else:
                return {
                    "ticker": ticker,
                    "has_dividends": False,
                    "message": "This stock does not pay dividends.",
                }
        except Exception as e:
            return {
                "error": f"Error retrieving dividend information for {ticker}: {str(e)}"
            }


class GetRecommendationsTool(BaseTool):
    name: str = "GetRecommendations"
    description: str = "Get analyst recommendations for a stock."

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Get analyst recommendations for a stock."""
        try:
            stock = yf.Ticker(ticker)

            # Get recommendations
            recommendations = stock.get_recommendations()

            # Process the recommendations
            if recommendations is not None and not recommendations.empty:
                # Simply convert the DataFrame to a dictionary
                rec_dict = recommendations.reset_index().to_dict("records")

                return {
                    "ticker": ticker,
                    "has_recommendations": True,
                    "recommendations": rec_dict,
                }
            else:
                return {
                    "ticker": ticker,
                    "has_recommendations": False,
                    "message": "No analyst recommendations available for this stock.",
                }
        except Exception as e:
            return {"error": f"Error retrieving recommendations for {ticker}: {str(e)}"}


class GetOptionsDataTool(BaseTool):
    name: str = "GetOptionsData"
    description: str = "Get options chain data for a stock."

    def _run(
        self, ticker: str, expiration_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get options chain data for a stock."""
        try:
            stock = yf.Ticker(ticker)

            # Get expiration dates
            expirations = stock.options

            if not expirations:
                return {
                    "ticker": ticker,
                    "has_options": False,
                    "message": "No options data available for this stock.",
                }

            # Use provided expiration date or default to the nearest one
            exp_date = (
                expiration_date if expiration_date in expirations else expirations[0]
            )

            # Get options chain for the selected expiration
            options = stock.option_chain(exp_date)

            # Format calls and puts data
            if options:
                calls = (
                    options.calls.reset_index().to_dict("records")
                    if not options.calls.empty
                    else []
                )
                puts = (
                    options.puts.reset_index().to_dict("records")
                    if not options.puts.empty
                    else []
                )

                # Limit the amount of data to avoid overwhelming the agent
                max_options = 5
                calls = calls[:max_options]
                puts = puts[:max_options]

                # Convert complex objects to strings for JSON serialization
                for options_list in [calls, puts]:
                    for option in options_list:
                        for key, value in option.items():
                            if not isinstance(
                                value, (int, float, str, bool, type(None))
                            ):
                                option[key] = str(value)

                return {
                    "ticker": ticker,
                    "has_options": True,
                    "expiration_date": exp_date,
                    "available_expirations": expirations,
                    "calls_sample": calls,
                    "puts_sample": puts,
                }
            else:
                return {
                    "ticker": ticker,
                    "has_options": False,
                    "message": "No options data available for the specified expiration date.",
                }
        except Exception as e:
            return {"error": f"Error retrieving options data for {ticker}: {str(e)}"}


class GetMajorHoldersTool(BaseTool):
    name: str = "GetMajorHolders"
    description: str = "Get information about major shareholders of a company."

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Get information about major shareholders of a company."""
        try:
            stock = yf.Ticker(ticker)

            # Get major holders
            major_holders = stock.major_holders

            if major_holders is not None and not major_holders.empty:
                # Convert DataFrame to a dictionary
                holders_dict = []
                for i, row in major_holders.iterrows():
                    if len(row) >= 2:
                        holders_dict.append(
                            {"percentage": row[0], "description": row[1]}
                        )

                return {"ticker": ticker, "major_holders": holders_dict}
            else:
                return {
                    "ticker": ticker,
                    "message": "No major holders data available for this stock.",
                }
        except Exception as e:
            return {"error": f"Error retrieving major holders for {ticker}: {str(e)}"}


class GetInstitutionalHoldersTool(BaseTool):
    name: str = "GetInstitutionalHolders"
    description: str = "Get information about institutional shareholders of a company."

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Get information about institutional shareholders of a company."""
        try:
            stock = yf.Ticker(ticker)

            # Get institutional holders
            institutional_holders = stock.institutional_holders

            if institutional_holders is not None and not institutional_holders.empty:
                # Convert DataFrame to a dictionary
                holders_list = []
                for _, row in institutional_holders.iterrows():
                    holder_dict = {}
                    for col in institutional_holders.columns:
                        holder_dict[col] = str(row[col])
                    holders_list.append(holder_dict)

                return {"ticker": ticker, "institutional_holders": holders_list}
            else:
                return {
                    "ticker": ticker,
                    "message": "No institutional holders data available for this stock.",
                }
        except Exception as e:
            return {
                "error": f"Error retrieving institutional holders for {ticker}: {str(e)}"
            }


class GetNewsTool(BaseTool):
    name: str = "GetNews"
    description: str = "Get recent news articles related to a company."

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Get recent news articles related to a company."""
        try:
            stock = yf.Ticker(ticker)

            # Get news
            news = stock.news

            if news:
                # Format news data
                news_list = []
                for article in news[:10]:  # Limit to 10 most recent articles
                    # Get the content object
                    content = article.get("content", {})

                    # Extract provider info
                    provider = content.get("provider", {})
                    provider_name = (
                        provider.get("displayName", "")
                        if isinstance(provider, dict)
                        else ""
                    )

                    # Get link from clickThroughUrl or canonicalUrl
                    link = ""
                    click_through = content.get("clickThroughUrl", {})
                    if isinstance(click_through, dict) and "url" in click_through:
                        link = click_through.get("url", "")
                    elif isinstance(content.get("canonicalUrl", {}), dict):
                        link = content.get("canonicalUrl", {}).get("url", "")

                    news_item = {
                        "title": content.get("title", ""),
                        "publisher": provider_name,
                        "link": link,
                        "publish_time": content.get("pubDate", ""),
                        "summary": content.get("summary", ""),
                    }

                    news_list.append(news_item)

                return {"ticker": ticker, "news": news_list}
            else:
                return {
                    "ticker": ticker,
                    "message": "No recent news available for this stock.",
                }
        except Exception as e:
            return {"error": f"Error retrieving news for {ticker}: {str(e)}"}


class GetSustainabilityTool(BaseTool):
    name: str = "GetSustainability"
    description: str = "Get ESG (Environmental, Social, Governance) data for a company."

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Get ESG (Environmental, Social, Governance) data for a company."""
        try:
            stock = yf.Ticker(ticker)

            # Get sustainability data
            sustainability = stock.sustainability

            if sustainability is not None and not sustainability.empty:
                # Convert DataFrame to a dictionary
                sustainability_dict = {}
                for idx, value in sustainability.iloc[:, 0].items():
                    sustainability_dict[idx] = (
                        float(value) if isinstance(value, (int, float)) else str(value)
                    )

                return {
                    "ticker": ticker,
                    "has_sustainability_data": True,
                    "sustainability": sustainability_dict,
                }
            else:
                return {
                    "ticker": ticker,
                    "has_sustainability_data": False,
                    "message": "No sustainability (ESG) data available for this stock.",
                }
        except Exception as e:
            return {
                "error": f"Error retrieving sustainability data for {ticker}: {str(e)}"
            }


class CompareStocksTool(BaseTool):
    name: str = "CompareStocks"
    description: str = "Compare performance and key metrics of multiple stocks."

    def _run(self, tickers: List[str], period: str = "1y") -> Dict[str, Any]:
        """Compare performance and key metrics of multiple stocks."""
        try:
            if not isinstance(tickers, list):
                return {"error": "Tickers must be provided as a list."}

            # Limit the number of tickers to compare
            max_tickers = 5
            if len(tickers) > max_tickers:
                tickers = tickers[:max_tickers]

            # Get data for each ticker
            stock_data = {}
            for ticker in tickers:
                stock = yf.Ticker(ticker)

                # Get basic info
                info = stock.info

                # Get historical data for performance comparison
                history = stock.history(period=period)

                if not history.empty:
                    start_price = history["Close"].iloc[0]
                    end_price = history["Close"].iloc[-1]
                    price_change = end_price - start_price
                    price_change_pct = (price_change / start_price) * 100
                else:
                    start_price = end_price = price_change = price_change_pct = "N/A"

                stock_data[ticker] = {
                    "name": info.get("shortName", "N/A"),
                    "sector": info.get("sector", "N/A"),
                    "market_cap": info.get("marketCap", "N/A"),
                    "current_price": info.get(
                        "currentPrice", info.get("regularMarketPrice", "N/A")
                    ),
                    "pe_ratio": info.get("trailingPE", "N/A"),
                    "forward_pe": info.get("forwardPE", "N/A"),
                    "dividend_yield": info.get("dividendYield", "N/A"),
                    "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
                    "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
                    "start_price": start_price,
                    "end_price": end_price,
                    "price_change": price_change,
                    "price_change_pct": (
                        round(price_change_pct, 2)
                        if isinstance(price_change_pct, (int, float))
                        else price_change_pct
                    ),
                }

            return {"tickers": tickers, "period": period, "comparison": stock_data}
        except Exception as e:
            return {"error": f"Error comparing stocks: {str(e)}"}


class CalculateReturnsTool(BaseTool):
    name: str = "CalculateReturns"
    description: str = "Calculate returns over different time periods for a stock."

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Calculate returns over different time periods for a stock."""
        try:
            stock = yf.Ticker(ticker)

            # Get historical data for different periods
            periods = {
                "1_week": "7d",
                "1_month": "1mo",
                "3_months": "3mo",
                "6_months": "6mo",
                "1_year": "1y",
                "3_years": "3y",
                "5_years": "5y",
                "10_years": "10y",
            }

            returns = {}
            for period_name, period in periods.items():
                try:
                    history = stock.history(period=period)
                    if not history.empty and len(history) > 1:
                        start_price = history["Close"].iloc[0]
                        end_price = history["Close"].iloc[-1]
                        return_pct = ((end_price / start_price) - 1) * 100
                        returns[period_name] = round(return_pct, 2)
                    else:
                        returns[period_name] = "N/A"
                except:
                    returns[period_name] = "N/A"

            # Calculate annualized returns
            ann_returns = {}
            if "1_year" in returns and returns["1_year"] != "N/A":
                ann_returns["1_year"] = returns["1_year"]

            if "3_years" in returns and returns["3_years"] != "N/A":
                ann_returns["3_years"] = round(
                    ((1 + (returns["3_years"] / 100)) ** (1 / 3) - 1) * 100, 2
                )

            if "5_years" in returns and returns["5_years"] != "N/A":
                ann_returns["5_years"] = round(
                    ((1 + (returns["5_years"] / 100)) ** (1 / 5) - 1) * 100, 2
                )

            if "10_years" in returns and returns["10_years"] != "N/A":
                ann_returns["10_years"] = round(
                    ((1 + (returns["10_years"] / 100)) ** (1 / 10) - 1) * 100, 2
                )

            # Get risk metrics if possible
            risk_metrics = {}
            try:
                if "1_year" in returns and returns["1_year"] != "N/A":
                    # Calculate standard deviation of daily returns (volatility)
                    daily_returns = history["Close"].pct_change().dropna()
                    volatility = (
                        daily_returns.std() * (252**0.5) * 100
                    )  # Annualized volatility
                    risk_metrics["volatility"] = round(volatility, 2)
            except:
                pass

            return {
                "ticker": ticker,
                "total_returns": returns,
                "annualized_returns": ann_returns,
                "risk_metrics": risk_metrics,
            }
        except Exception as e:
            return {"error": f"Error calculating returns for {ticker}: {str(e)}"}


class GetEstimatesTool(BaseTool):
    name: str = "GetEstimates"
    description: str = (
        "Get analyst estimates for a stock including revenue estimates, growth estimates, and earnings estimates."
    )

    def _run(self, ticker: str) -> Dict[str, Any]:
        """Get financial estimates for a stock."""
        try:
            stock = yf.Ticker(ticker)

            # Initialize result dictionary
            result = {
                "ticker": ticker,
            }

            # Get revenue estimates
            try:
                result["revenue_estimates"] = stock.revenue_estimate.to_dict()
            except Exception as e:
                result["revenue_estimates"] = {"error": str(e)}

            # Get earnings estimates
            try:
                result["earnings_estimates"] = stock.earnings_estimate.to_dict()
            except Exception as e:
                result["earnings_estimates"] = {"error": str(e)}

            return result

        except Exception as e:
            return {"error": f"Error retrieving estimates for {ticker}: {str(e)}"}


# Collection of all YFinance tools
class YFinanceTools:
    """Collection of all YFinance tools for financial analysis."""

    @staticmethod
    def get_all_tools(timeout: int = 30) -> List[BaseTool]:
        """Returns all YFinance tools with the specified timeout."""
        return [
            GetStockInfoTool(timeout=timeout),
            GetHistoricalDataTool(timeout=timeout),
            GetIncomeStatementTool(timeout=timeout),
            GetBalanceSheetTool(timeout=timeout),
            GetCashFlowTool(timeout=timeout),
            GetEarningsTool(timeout=timeout),
            GetDividendsTool(timeout=timeout),
            GetRecommendationsTool(timeout=timeout),
            GetOptionsDataTool(timeout=timeout),
            GetMajorHoldersTool(timeout=timeout),
            GetInstitutionalHoldersTool(timeout=timeout),
            GetNewsTool(timeout=timeout),
            GetSustainabilityTool(timeout=timeout),
            CompareStocksTool(timeout=timeout),
            CalculateReturnsTool(timeout=timeout),
            GetEstimatesTool(timeout=timeout),
        ]
