import json
import autogen
import asyncio
# from sqlalchemy import create_engine

import urllib
import os
from capabilities.stateaware import StateAware
from domain_knowledge.direct_aoai import retrieve_llm_response_on_question
from capabilities.task_tracker import TaskTrackingbility
from capabilities.stateaware_non_llm import StateAwareNonLlm
from models.agent_context import AgentContext, PlanContext

config_list = autogen.config_list_from_json(env_or_file="AOAI_CONFIG_LIST")
llm_config = {"config_list": config_list}

SEQUENTIAL_STEP = "SequentialStep"
PARALLEL_STEP = "ParallelStep"
MAX_TURNS_PER_AGENT = 5
MAX_ROUNDS_PER_GROUP_CHAT = 12

def add_capability(agent, deliverable: PlanContext, agent_id, agent_name, parent_agent_name):
    # Instantiate a StateAware object. Its parameters are all optional 
    # however we will need to have AgentContext changed at some point
    state_aware_ability = StateAwareNonLlm(
        verbosity=2,
        context= AgentContext(deliverable, agent_id, agent_name, parentAgentName=parent_agent_name)
    )
    
    # Now add state_aware_ability to the agent
    state_aware_ability.add_to_agent(agent)
    
async def main():
    deliverable = PlanContext(planId="Plan1", planName="Plan1", deliverableName="Client Profile")
    
    # We use an assistant agent as we do not need human interaction for this demo
    analyst = autogen.ConversableAgent( #autogen.AssistantAgent( #
        name="Analyst",
        system_message="Create a two line report for a client profile of 'Disney Corporation' with the current target market of the business. If you do not know then ASK the Critic for this info. Do NOT make assumptions.",
        #description=task['Description'],
        llm_config=llm_config,
        max_consecutive_auto_reply=1,
        human_input_mode="NEVER",
        code_execution_config=False
        #chat_messages=conversation_history
    )
    
    add_capability(analyst, deliverable, agent_id="1", agent_name="Analyst", parent_agent_name="User1")
    
    # We use an assistant agent as we do not need human interaction for this demo
    researcher = autogen.ConversableAgent( #autogen.AssistantAgent( #
        name="Researcher",
        system_message="Create a one line report of the current CTO of the 'Disney Corporation' business. If you do not know then ASK the Critic for this info. Do NOT make assumptions.",
        #description=task['Description'],
        llm_config=llm_config,
        max_consecutive_auto_reply=1,#,
        human_input_mode="NEVER",
        code_execution_config=False
        #chat_messages=conversation_history
    )
    
    add_capability(analyst, deliverable, agent_id="2", agent_name="Researcher", parent_agent_name="User1")
    
    # We use an assistant agent as we do not need human interaction for this demo
    critic = autogen.ConversableAgent( #autogen.AssistantAgent( #
        name="Critic",
        system_message="Critic. You are focused on ensuring the final output is complete. If an agent has an ASK then TERMINATE the discussion and wait for user input.",
        #description=task['Description'],
        llm_config=llm_config,
        max_consecutive_auto_reply=1,#,
        human_input_mode="NEVER",
        code_execution_config=False
        #chat_messages=conversation_history
    )
    
    add_capability(analyst, deliverable, agent_id="3", agent_name="Critic", parent_agent_name="User1")
    
    user_proxy_system_message = "Start building the completed client profile for 'Disney Corporation'."
    
    user_proxy = autogen.UserProxyAgent( # autogen.AssistantAgent(
            name="User1",
            system_message=user_proxy_system_message,
            #description=step['Description'],
            llm_config=llm_config,
            human_input_mode="NEVER",
            #max_consecutive_auto_reply=1,
            code_execution_config=False,
            is_termination_msg=lambda user_proxy_system_message: True # Always True so we terminate if we get a message to relay to the user
        )
    
    # Create a groupchat and groupchat manager based on the task
    groupchat = autogen.GroupChat([analyst, researcher, critic], messages=[], max_round=MAX_ROUNDS_PER_GROUP_CHAT)
    manager = autogen.GroupChatManager(
                    groupchat=groupchat, 
                    llm_config=llm_config, 
                    name="GroupManager")    

    chat_results = user_proxy.initiate_chat(manager, clear_history=False, message=user_proxy_system_message) #.initiate_chat(manager, message=user_proxy_system_message) #, user_proxy_system_message))
    
    print("Chat results: ", chat_results.summary)
        
# Run the main function
asyncio.run(main())