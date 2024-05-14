import json
import autogen
import asyncio

config_list = autogen.config_list_from_json(env_or_file="AOAI_CONFIG_LIST")
llm_config = {"config_list": config_list}

SEQUENTIAL_STEP = "SequentialStep"
PARALLEL_STEP = "ParallelStep"

# Retrieve the existing plan for a customer
def retrieve_plan(customer_id: str):
    # Open the JSON file and load it into a Python object
    with open('sample_plan.json') as f:
        data = json.load(f)
        
        return data

# Execute the plan retrieved for the customer
async def execute_plan(plan: json):
    carry_over = ""
    # Iterate over the "Steps" array
    for step in plan['Steps']:
        #print(f"Step ID: {step['Id']}, Step Name: {step['Name']}")

        print(f"\tRunning a {step['Type']} step")
        if(step['Type'] == SEQUENTIAL_STEP):
            carry_over = run_sequential_tasks(step, carry_over)
        elif(step['Type'] == PARALLEL_STEP):
            carry_over = await run_parallel_tasks(step, carry_over)

# Create an agent for a specific task
def create_agent_for_task(task: json):    
    # Create an agent based on the task
    # We use an assistant agent as we do not need human interaction for this demo
    assistant = autogen.AssistantAgent( #autogen.ConversableAgent( #
        name=task['Name'],
        system_message=task['InitialMessage'],
        #description=task['Description'],
        llm_config=llm_config,
    )
    
    return assistant

# Build the array used to send list of agents to a sequential chat
def build_agent_list_with_prereqs(agents: list, tasks: list):
    agent_list = []
    
    for agent in agents:
        task = tasks[agents.index(agent)]
        # print(f"\tTask: {task['Name']}, Prerequisites: {task['Prerequisites']}")
        prerequisites = task.get('Prerequisites', [])
        if prerequisites is not None and isinstance(prerequisites, list):
            prerequisites = prerequisites
        else:
            prerequisites = []
        # print(f"\tPrerequisites: {prerequisites}")
        agent_list.append({
            "chat_id": task['Id'],
            "recipient": agent,
            "message": agent.system_message,
            "max_turns": 2,
            "summary_method": "last_msg",
            "silent": False,
            "prerequisites": prerequisites
        })
    
    return agent_list
        
# Build the array used to send list of agents to a sequential chat
def build_agent_list(agents: list):
    agent_list = []
    
    for agent in agents:
        agent_list.append({
            "recipient": agent,
            "message": agent.system_message,
            "max_turns": 1,
            "summary_method": "last_msg",
        })
    
    return agent_list

# Execute a sequential step with the carry_over from previous chats as needed
def run_sequential_tasks(step: json, carry_over: str):
    agents = []

    # Iterate over the "Tasks" array within each step
    for task in step['Tasks']:
        agents.append(create_agent_for_task(task))
    
    # initiate the chat with the agents
    # The Number Agent always returns the same numbers.
    step_agent = autogen.AssistantAgent( #ConversableAgent( #
        name=step['Name'],
        system_message=step['InitialMessage'],
        description=step['Description'],
        llm_config=llm_config,
        human_input_mode="NEVER",
    )
    
    chat_results = step_agent.initiate_chats(build_agent_list(agents))
    
    summary = chat_results[-1].summary
    print(f"\t Returning carry_over summary of: {summary}")
    return summary
    
# Execute a parallel step
async def run_parallel_tasks(step: json, carry_over: str):
    agents = []
    tasks = []
    # Iterate over the "Tasks" array within each step
    for task in step['Tasks']:
        # print(f"\tTask: {task['Name']}, Prerequisites: {task['Prerequisites']}")
        agents.append(create_agent_for_task(task))
        tasks.append(task)
    
    # initiate the chat with the agents
    step_agent = autogen.AssistantAgent(
        name=step['Name'],
        system_message=step['InitialMessage'],
        description=step['Description'],
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    agent_list = build_agent_list_with_prereqs(agents, tasks)
    print(f"\tAgent List: {agent_list}")
    chat_results = await step_agent.a_initiate_chats(agent_list)
    
    #summary = chat_results[-1].summary
    #print(f"\tSummary: {summary}")
    return "summary"

async def main():  
    plan = retrieve_plan("123")

    await execute_plan(plan)

# Run the main function
asyncio.run(main())