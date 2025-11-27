from crewai import Agent, Crew, Task, Process
from crewai_tools import SerperDevTool
from spcs_helpers import get_serper_api_key


class ExternalToolCrew:
    def __init__(self, llm):
        self.llm = llm
        # Initialize Serper tool with API key from SPCS secret or environment
        serper_api_key = get_serper_api_key()
        if not serper_api_key:
            raise ValueError("SERPER_API_KEY not found in SPCS secrets or environment variables")
        self.search_tool = SerperDevTool(api_key=serper_api_key)

    def researcher_agent(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Web Researcher",
            goal="Search the web for current information and provide comprehensive insights",
            backstory="An expert researcher skilled at finding and analyzing information from the web using search tools",
            verbose=True,
            tools=[self.search_tool]
        )

    def analyst_agent(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Data Analyst",
            goal="Analyze the research findings and create actionable insights",
            backstory="A skilled analyst who can synthesize information and provide clear recommendations",
            verbose=True
        )

    def research_task(self) -> Task:
        return Task(
            description="Search the web for information about the latest trends in AI and machine learning. Focus on recent developments in the last 3 months.",
            expected_output="A comprehensive report with at least 5 key findings about recent AI/ML trends, including sources.",
            agent=self.researcher_agent()
        )

    def analysis_task(self) -> Task:
        return Task(
            description="Analyze the research findings and create a summary with key insights and recommendations.",
            expected_output="A structured analysis with main insights, trends, and actionable recommendations based on the research.",
            agent=self.analyst_agent()
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.researcher_agent(), self.analyst_agent()],
            tasks=[self.research_task(), self.analysis_task()],
            process=Process.sequential,
            verbose=True
        )


async def run_external_tool_crew(llm):
    return await ExternalToolCrew(llm).crew().kickoff_async(inputs={})
