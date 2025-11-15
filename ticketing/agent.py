"""
Ticketing Agent Pipeline
This module defines the root agent for the ticketing application.
"""

from google.adk.agents.llm_agent import Agent, LlmAgent
# from google.adk.agents import SequentialAgent
from .subagents.ticketing_orchestrator.agent import ticketing_orchestrator
from .custom_utils.enviroment_interaction import load_instruction_from_file
# from .tools import zammad_client
from dotenv import load_dotenv
import os

load_dotenv()

model_name = os.getenv('LLM_MODEL', 'gemini-2.5-flash')

root_agent = LlmAgent(
    model=model_name,
    name='root_agent',
    instruction=load_instruction_from_file("root_agent.prompt"),
    sub_agents=[ticketing_orchestrator],
)