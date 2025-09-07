import re
from typing import List, Dict, Optional
from langgraph import Node
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType

# Function definitions should be above where they are used

def extract_entities(text: str) -> Dict[str, List[str]]:
    company_pattern = r"\b(?:Google|Microsoft|Apple|Amazon|Tesla)\b"
    industry_pattern = r"\b(?:Technology|Healthcare|Finance|Retail|Education)\b"
    location_pattern = r"\b(?:USA|India|Germany|UK|Canada)\b"
    role_pattern = r"\b(?:Engineer|Manager|Director|Analyst|Consultant)\b"
    product_pattern = r"\b(?:ProductA|ProductB|ProductC|ServiceX|ServiceY)\b"
    
    companies = re.findall(company_pattern, text)
    industries = re.findall(industry_pattern, text)
    locations = re.findall(location_pattern, text)
    roles = re.findall(role_pattern, text)
    products = re.findall(product_pattern, text)
    
    return {
        "companies": companies,
        "industries": industries,
        "locations": locations,
        "roles": roles,
        "products": products
    }

def determine_recency(text: str) -> Optional[str]:
    recency_keywords = ["recent", "last week", "this month", "yesterday", "today"]
    for keyword in recency_keywords:
        if keyword in text.lower():
            return keyword
    return None

def set_max_results(text: str) -> int:
    default_max_results = 10
    numbers = re.findall(r"\b\d+\b", text)
    if numbers:
        return int(numbers[0])
    return default_max_results

# Now define tools after functions are ready
tools = [
    Tool(
        name="extract_entities",
        func=extract_entities,
        description="Extract entities such as companies, industries, locations, etc."
    ),
    Tool(
        name="determine_recency",
        func=determine_recency,
        description="Determine the recency of the information."
    ),
    Tool(
        name="set_max_results",
        func=set_max_results,
        description="Set the maximum number of results per task."
    ),
]

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4")

# Initialize the agent
agent = initialize_agent(
    tools,
    llm,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

class IntentParser(Node):
    def run(self, inputs: Dict[str, str]) -> Dict[str, any]:
        text = inputs.get("text", "")
        
        response = agent.invoke({"input": text})
        
        return {
            "companyList": response.get("companies", []),
            "industry": response.get("industries", []),
            "geo": response.get("locations", []),
            "roleKeywords": response.get("roles", []),
            "productKeywords": response.get("products", []),
            "recency": response.get("recency", None),
            "maxResultsPerTask": response.get("maxResults", 10)
        }
