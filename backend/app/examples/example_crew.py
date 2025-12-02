from crewai import Agent, Crew, Task, Process

class YourCrewName:
    def __init__(self, llm):
        self.llm = llm 
    def agent_one(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Data Analyst",
            goal="Analyze data trends in the market",
            backstory="An experienced data analyst with a background in economics",
            verbose=True,
            tools=[]
        )

    def agent_two(self) -> Agent:
        return Agent(
            llm=self.llm,
            role="Market Researcher",
            goal="Gather information on market dynamics",
            backstory="A diligent researcher with a keen eye for detail",
            verbose=True
        )

    def task_one(self) -> Task:
        return Task(
            description="Collect recent market data and identify trends.",
            expected_output="A report summarizing key trends in the market.",
            agent=self.agent_one()
        )

    def task_two(self) -> Task:
        return Task(
            description="Research factors affecting market dynamics.",
            expected_output="An analysis of factors influencing the market.",
            agent=self.agent_two()
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.agent_one(), self.agent_two()],
            tasks=[self.task_one(), self.task_two()],
            process=Process.sequential,
            verbose=True
        )
    
    
async def run_crew(llm):
    return await YourCrewName(llm).crew().kickoff_async(inputs={"any": "input here"})
