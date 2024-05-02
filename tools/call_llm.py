from typing import Annotated
from domain_knowledge.direct_aoai import retrieve_llm_response_on_question

def call_aoai(question: Annotated[str, 'Question to be asked against domain knowledge']) -> str:
    response = retrieve_llm_response_on_question(question)

    return response
    #return "you need flour and eggs"