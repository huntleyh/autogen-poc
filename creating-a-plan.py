import autogen
from tools.call_llm import call_aoai
from domain_knowledge.direct_aoai import retrieve_llm_response_on_question
from autogen.agentchat.contrib.agent_builder import AgentBuilder
import autogen

config_file_or_env = "AOAI_CONFIG_LIST"
builder_model = "gpt-4-deployment"
agent_model = "gpt-4-deployment"

def get_configs():
    config_list_gpt4 = autogen.config_list_from_json(
        env_or_file=config_file_or_env,
        file_location=".",
        filter_dict={
            "model": {builder_model}
        },
    )

    gpt4_config = {
        "cache_seed": 42,  
        "temperature": 0,
        "config_list": config_list_gpt4,
        "timeout": 120,
    }

    return config_list_gpt4, gpt4_config

def get_roles_for_agents_via_autogen():
    config_list, gpt4_config = get_configs()

    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message="A human admin. Interact with the planner to discuss the plan. Plan execution does NOT need to be approved by this admin.",
        code_execution_config=False,
    )

    planner = autogen.AssistantAgent(
        name="Planner",
        description="An AI agent with access to confirm information against domain specific data.",
        system_message="""Planner. Suggest a plan based on domain knowledge for the proposed question. Revise the plan based on feedback from critic.
    Explain the plan first. Be clear which step is performed by whom and what each step entails. 
    Once you have confirmation on the plan then say DONE!!.
    """,
        llm_config=gpt4_config,
        max_consecutive_auto_reply=1,  # Limit the number of consecutive auto-replies.
    )

    # Register the call_aoai function to the two agents.
    autogen.register_function(
        call_aoai,
        caller=planner,  # The planner agent can suggest calls to the llm.
        executor=user_proxy,  # The user proxy agent can execute the llm calls.
        name="call_aoai",  # By default, the function name is used as the tool name.
        description="Confirm something based on domain knowledge",  # A description of the tool.
    )

    critic = autogen.AssistantAgent(
        name="Critic",
        description="A domain aware agent that does not allow any assumptions when answering questions.",
        system_message="Critic. Double check plan, ensure to critique each step so it is double checked and provide feedback. Make no assumptions and trust the domain data.",
        llm_config=gpt4_config,
        max_consecutive_auto_reply=1,  # Limit the number of consecutive auto-replies.
        is_termination_msg=lambda msg: "DONE!!" in msg["content"].lower(),
    )

    groupchat = autogen.GroupChat(
        agents=[user_proxy, planner, critic], messages=[], max_round=50
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

    # Start the chat
    user_proxy.initiate_chat(
        manager,
        message="""
    What ingredients are needed based on domain knowledge to make a sesame street count cookie
    """
    )

def dynamically_build_and_run_agents(task: str):
    config_list, gpt4_config = get_configs()
    builder = AgentBuilder(config_file_or_env=config_file_or_env, builder_model=builder_model, agent_model=agent_model)

    agent_list, agent_configs = builder.build(task, gpt4_config, coding=False)

    return agent_list, agent_configs
    
def start_task(execution_task: str, agent_list: list, llm_config: dict):
    config_list, gpt4_config = get_configs()

    group_chat = autogen.GroupChat(agents=agent_list, messages=[], max_round=12)
    manager = autogen.GroupChatManager(
        groupchat=group_chat, llm_config={"config_list": config_list, **llm_config}
    )
    agent_list[0].initiate_chat(manager, message=execution_task)

def use_direct_llm(task: str):
    question = f"""
        This is your task: {task}. Can you give me the roles needed to accomplish this? Respond with just the roles.
        No additional detail is needed. Only provide the comma delimited list of roles needed. 
    """

    roles_needed = retrieve_llm_response_on_question(question)

    question = f"""
    This is your task: {task}.
    Give me the steps to be completed for each of these roles to accomplish this task: {roles_needed}. 
    No additional detail is needed. Respond ONLY with the role and steps for each as a numbered list. 
    """
    
    steps_for_each_role = retrieve_llm_response_on_question(question)

    print("Roles required: " + roles_needed)
    print("Steps retrieved for each role: " + steps_for_each_role)

    builder_task_prompt=f"""
    Perform this task: {task}. 
    Do NOT create any other agents unless they are for human interaction.
    To do this task you need one agent each for these roles: {roles_needed}.
    These are the steps for each role:
    {steps_for_each_role}
    """

    agent_list, agent_config = dynamically_build_and_run_agents(builder_task_prompt)

    config_list, gpt4_config = get_configs()
    start_task(task, agent_list, gpt4_config)

print("APPROACH 1: Get list of and roles for agents using auto-gen")
## Approach 1
## Sample code to get list of and roles for agents using auto-gen
#get_roles_for_agents_via_autogen()

print('\n\n')
print("---------------------------------------------------")
print("---------------------------------------------------")

print("APPROACH 2: Query AOAI BYOD setup directly for both roles and tasks for each role")
## Approach 2
## Sample code to query AOAI BYOD setup directly for both roles and tasks for each role 
## then dynamically build and run agents using AutoGen
task = "bake a \"sesame street count cookie\""  # Task to be executed. This is a sample and runs on the AOAI BYOD setup
use_direct_llm(task)
