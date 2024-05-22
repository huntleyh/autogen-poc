# import skillsmodule
from autogen import ConversableAgent
import autogen

config_list = autogen.config_list_from_json(env_or_file="AOAI_CONFIG_LIST")
llm_config = {"config_list": config_list}

class Skills:
    name: str
    moduleName: str
    description: str
    
def assign_agent_skills(agent: ConversableAgent, skills: Skills):
    code = "def register_skills(agent: ConversableAgent):\n"
    
    for skill in skills:
        code = code + f"\tagent.register_for_llm(name=\"{skill.name}\", description=\"{skill.description}\")({skill.moduleName}) \n"    
    
    print(code)
    return code    

agent = ConversableAgent(
        name="demo",
        system_message="do nothing.",
        llm_config=llm_config,
        human_input_mode="NEVER")

skill = Skills()
skill.description = "someDescription"
skill.moduleName = "mod.name"
skill.name = "skillName"

code = assign_agent_skills(agent, [skill, skill])

exec(code)
register_skills(agent)
