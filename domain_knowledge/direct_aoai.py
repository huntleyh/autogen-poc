from openai import AzureOpenAI
import json
import os

config = None
with open("AOAI_CONFIG_LIST", "r") as file:
    json_str = file.read()
    config = json.loads(json_str)

AI_SEARCH_ENDPOINT=os.environ["AI_SEARCH_ENDPOINT"]
AI_SEARCH_INDEX_NAME=os.environ["AI_SEARCH_INDEX_NAME"]
AI_SEARCH_SEMANTIC_CONFIG_NAME=os.environ["AI_SEARCH_SEMANTIC_CONFIG_NAME"]
AI_SEARCH_KEY=os.environ["AI_SEARCH_KEY"]

client = AzureOpenAI(
  api_key = config[0]["api_key"],  
  api_version = config[0]["api_version"],
  azure_endpoint = config[0]["base_url"]
)

def retrieve_llm_response_on_question(question: str):
    response = client.chat.completions.create(
        model=config[0]["model"],
        messages=[
            {"role": "user", "content": question}
        ],
        extra_body={
            "data_sources": [
                {
                    "type": "azure_search",
                    "parameters": {
                        "endpoint": AI_SEARCH_ENDPOINT,
                        "index_name": AI_SEARCH_INDEX_NAME,
                        "semantic_configuration": AI_SEARCH_SEMANTIC_CONFIG_NAME,
                        "query_type": "semantic",
                        "fields_mapping": {},
                        "in_scope": "true",
                        "role_information": "You are an AI assistant that helps people find information.",
                        "filter": None,
                        "strictness": 3,
                        "top_n_documents": 5,
                        "authentication": {
                            "type": "api_key",
                            "key": AI_SEARCH_KEY
                        }
                    }
                }
            ]
        }
    )

    # print(response.model_dump_json(indent=2))
    # print(response.choices[0].message.content)
    return response.choices[0].message.content