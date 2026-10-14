
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from backend.services.place_tool import search_places
from backend.services.weather_service import get_weather_forecast


# Load environment variables from the project root .env file.
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Please check your .env file."
    )


# Initialize the Gemini language model.
llm = ChatGoogleGenerativeAI(
      model="gemini-3.8-flash",
    google_api_key=api_key,
    temperature=0.2,
)


# Register tools available to the AI Agent.
tools = [
    search_places,
    get_weather_forecast,
]


# Create the LangGraph ReAct Agent.
agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=(
        "You are the AI Local Guide for Da Nang, Vietnam. "
        "Help users discover places and plan local activities. "
        "Use search_places when users ask about attractions, "
        "restaurants, cafes, shopping, or places within their budget. "
        "Use get_weather_forecast when users ask about weather. "
        "Use the available tools when current database or weather "
        "information is needed. "
        "Answer in the same language as the user. "
        "Do not invent place details or weather information. "
        "If the tools do not provide enough information, say so clearly."
    ),
)


def ask_agent(message: str) -> str:
    """
    Send a message to the AI Agent and return its response.
    """
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        },
        config={"recursion_limit": 10},
    )

    return result["messages"][-1].content
