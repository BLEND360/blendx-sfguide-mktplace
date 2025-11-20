from crewai import Agent, Crew, Task, Process
from crewai_tools import SerperDevTool

class YourCrewName:
    def __init__(self, llm):
        self.llm = llm
        # Initialize Serper tool for web search
        # The API key will be automatically read from SERPER_API_KEY environment variable
        self.search_tool = SerperDevTool()

    def agent_one(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Web Research Specialist",
            goal="Search the web for the latest information on AI and machine learning trends",
            backstory="An expert researcher who specializes in finding and analyzing the latest technology trends from across the internet",
            verbose=True,
            tools=[self.search_tool]
        )

    def agent_two(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Market Analysis Expert",
            goal="Analyze and synthesize research findings into actionable insights",
            backstory="A seasoned analyst with expertise in interpreting market data and technology trends",
            verbose=True,
            tools=[]
        )

    def task_one(self) -> Task:
        return Task(
            description="Use the search tool to find the latest news and trends about artificial intelligence and machine learning in 2025. Focus on recent developments, major announcements, and emerging technologies.",
            expected_output="A comprehensive summary of the latest AI and ML trends found through web search, including sources and key findings.",
            agent=self.agent_one()
        )

    def task_two(self) -> Task:
        return Task(
            description="Analyze the research findings from the web search and create a detailed report highlighting the most important trends, potential impacts, and recommendations.",
            expected_output="A well-structured analysis report that synthesizes the research findings into clear insights and actionable recommendations.",
            agent=self.agent_two()
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.agent_one(), self.agent_two()],
            tasks=[self.task_one(), self.task_two()],
            process=Process.sequential,
            verbose=True
        )
    
    
def run_crew(llm):
    return YourCrewName(llm).crew().kickoff(inputs={"any": "input here"})
