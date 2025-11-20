# Serper Integration Guide

This document explains how Serper API is integrated into the CrewAI application and how to customize it for your use cases.

## What is Serper?

Serper is a Google Search API that provides access to Google search results. It's a cost-effective alternative to the official Google Search API, offering:
- Real-time web search results
- News search
- Image search
- Shopping results
- And more

Official documentation: [https://serper.dev/docs](https://serper.dev/docs)

---

## How It Works in This Application

### 1. Environment Variable

The Serper API key is injected into the container through the `SERPER_API_KEY` environment variable, which is configured in the service specification:

**File**: `app/src/fullstack.yaml`
```yaml
- name: eap-backend
  env:
    SERPER_API_KEY: _udf_serper_api_key
  secrets:
    - snowflake_secret: serper_api_key
      env_name: SERPER_API_KEY
```

### 2. CrewAI Tool Integration

The `SerperDevTool` from `crewai-tools` automatically reads the API key from the environment variable:

**File**: `backend/src/example_crew.py`
```python
from crewai_tools import SerperDevTool

class YourCrewName:
    def __init__(self, llm):
        self.llm = llm
        # Automatically reads SERPER_API_KEY from environment
        self.search_tool = SerperDevTool()
```

### 3. Agent Configuration

Agents can use the search tool to perform web searches:

```python
def agent_one(self) -> Agent:
    return Agent(
        llm=self.llm,
        role="Web Research Specialist",
        goal="Search the web for the latest information",
        tools=[self.search_tool]  # Tool is assigned here
    )
```

---

## Customizing Search Behavior

### Basic Search

The default `SerperDevTool()` performs general web searches:

```python
from crewai_tools import SerperDevTool

# Default search tool
search_tool = SerperDevTool()

agent = Agent(
    role="Researcher",
    goal="Find information about AI trends",
    tools=[search_tool]
)
```

### Search with Parameters

You can configure search parameters:

```python
from crewai_tools import SerperDevTool

# Search with specific parameters
search_tool = SerperDevTool(
    search_url="https://google.serper.dev/search",
    n_results=10,  # Number of results to return
)
```

### News Search

To search specifically for news:

```python
from crewai_tools import SerperDevTool

news_search_tool = SerperDevTool(
    search_url="https://google.serper.dev/news"
)

agent = Agent(
    role="News Researcher",
    goal="Find latest news about technology",
    tools=[news_search_tool]
)
```

---

## Example Use Cases

### 1. Market Research Crew

```python
from crewai import Agent, Crew, Task, Process
from crewai_tools import SerperDevTool

class MarketResearchCrew:
    def __init__(self, llm):
        self.llm = llm
        self.search_tool = SerperDevTool()

    def researcher_agent(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Market Researcher",
            goal="Find comprehensive information about market trends",
            backstory="Expert in market analysis with strong research skills",
            tools=[self.search_tool],
            verbose=True
        )

    def analyst_agent(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Business Analyst",
            goal="Analyze research findings and provide insights",
            backstory="Experienced analyst who turns data into actionable insights",
            verbose=True
        )

    def research_task(self) -> Task:
        return Task(
            description="Search for the latest trends in {industry} for 2025. Include market size, growth rates, key players, and emerging technologies.",
            expected_output="A detailed report with sources, statistics, and key findings about {industry} trends.",
            agent=self.researcher_agent()
        )

    def analysis_task(self) -> Task:
        return Task(
            description="Analyze the research findings and create strategic recommendations for entering the {industry} market.",
            expected_output="A strategic analysis with recommendations, opportunities, and risks.",
            agent=self.analyst_agent()
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.researcher_agent(), self.analyst_agent()],
            tasks=[self.research_task(), self.analysis_task()],
            process=Process.sequential,
            verbose=True
        )

def run_crew(llm, industry="artificial intelligence"):
    return MarketResearchCrew(llm).crew().kickoff(inputs={"industry": industry})
```

### 2. Competitive Analysis Crew

```python
class CompetitiveAnalysisCrew:
    def __init__(self, llm):
        self.llm = llm
        self.web_search = SerperDevTool()
        self.news_search = SerperDevTool(
            search_url="https://google.serper.dev/news"
        )

    def competitor_researcher(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Competitor Intelligence Specialist",
            goal="Gather comprehensive information about competitors",
            tools=[self.web_search, self.news_search],
            verbose=True
        )

    def competitor_research_task(self) -> Task:
        return Task(
            description="Research {company_name} and their main competitors. Find information about products, market position, recent news, and strategic moves.",
            expected_output="A comprehensive competitor analysis report with sources.",
            agent=self.competitor_researcher()
        )
```

### 3. Content Research Crew

```python
class ContentResearchCrew:
    def __init__(self, llm):
        self.llm = llm
        self.search_tool = SerperDevTool(n_results=15)

    def content_researcher(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Content Researcher",
            goal="Find relevant and trending topics for content creation",
            tools=[self.search_tool],
            verbose=True
        )

    def content_writer(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Content Writer",
            goal="Create engaging content based on research",
            verbose=True
        )

    def research_task(self) -> Task:
        return Task(
            description="Research trending topics and popular content about {topic}. Find what questions people are asking and what content performs well.",
            expected_output="A list of trending topics, popular questions, and content ideas with sources.",
            agent=self.content_researcher()
        )

    def writing_task(self) -> Task:
        return Task(
            description="Based on the research, create an outline for a comprehensive article about {topic}.",
            expected_output="A detailed article outline with key points, structure, and suggested sources.",
            agent=self.content_writer()
        )
```

---

## Error Handling

### Common Issues

1. **Invalid API Key**
   - Error: `401 Unauthorized`
   - Solution: Verify the secret contains the correct API key

2. **Rate Limiting**
   - Error: `429 Too Many Requests`
   - Solution: Check your Serper plan limits and implement request throttling

3. **Network Access Denied**
   - Error: Connection errors
   - Solution: Verify External Access Integration is properly configured

### Debugging

To debug Serper integration issues, check the service logs:

```sql
CALL my_app.app_public.get_service_logs('eap-backend', 100);
```

Look for:
- `SERPER_API_KEY` environment variable presence
- API call errors
- Network connectivity issues

---

## Best Practices

### 1. Optimize Search Queries

Be specific in your task descriptions to get better search results:

```python
# ❌ Too vague
description="Search for AI"

# ✅ Specific and actionable
description="Search for the latest breakthroughs in large language models announced in 2025, focusing on efficiency improvements and new architectures"
```

### 2. Limit Results

Don't request more results than needed:

```python
# Configure appropriate number of results
search_tool = SerperDevTool(n_results=10)  # Usually 5-10 is sufficient
```

### 3. Use Appropriate Search Types

Choose the right search type for your use case:
- General web search: Default `SerperDevTool()`
- News: `SerperDevTool(search_url="https://google.serper.dev/news")`
- Images: `SerperDevTool(search_url="https://google.serper.dev/images")`

### 4. Monitor API Usage

Keep track of your Serper API usage:
- Check your dashboard at [https://serper.dev/dashboard](https://serper.dev/dashboard)
- Set up usage alerts
- Monitor costs in production

### 5. Cache Results When Possible

If your crew makes repeated similar searches, consider caching results to reduce API calls.

---

## Testing Locally

To test Serper integration locally:

1. Set the environment variable:
```bash
export SERPER_API_KEY="your_api_key_here"
```

2. Run your crew:
```bash
python backend/src/fastapi_app.py
```

3. Test the endpoint:
```bash
curl -X POST http://localhost:8081/crew/start
```

---

## Additional Resources

- **Serper API Documentation**: [https://serper.dev/docs](https://serper.dev/docs)
- **CrewAI Tools Documentation**: [https://docs.crewai.com/tools/serperdevtool](https://docs.crewai.com/tools/serperdevtool)
- **Serper Playground**: [https://serper.dev/playground](https://serper.dev/playground) - Test queries before implementing

---

## Support

If you encounter issues with Serper integration:

1. **Check application logs**: Use `get_service_logs()` procedure
2. **Verify configuration**: Review setup instructions
3. **Test API key**: Use Serper playground to verify key works
4. **Contact support**: Reach out to Serper support for API issues
