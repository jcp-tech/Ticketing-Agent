"""
Ticketing Orchestrator Sequential Agent
"""

# ticketing_orchestrator/agent.py
from google.adk.agents.llm_agent import Agent, LlmAgent
from google.adk.agents import SequentialAgent
from ticketing.custom_utils.enviroment_interaction import load_instruction_from_file
from ticketing.tools import zammad_client
from dotenv import load_dotenv
import os

load_dotenv()

model_name = os.getenv('LLM_MODEL', 'gemini-2.5-flash')

ticket_classifier_agent = LlmAgent(
  model=model_name,
  name='ticket_classifier_agent',
  instruction=load_instruction_from_file("ticket_classifier_agent.prompt"),
)

ticket_search_agent = LlmAgent(
  model=model_name,
  name='ticket_search_agent',
  instruction=load_instruction_from_file("ticket_search_agent.prompt"),
  tools=[
    # zammad_client.init_zammad_client,
    zammad_client.get_all_tickets,
    zammad_client.get_ticket,
    zammad_client.get_ticket_details,
    zammad_client.get_ticket_articles,
    zammad_client.list_article_attachments,
    zammad_client.download_attachment,
  ],
)

ticket_creation_agent = LlmAgent(
  model=model_name,
  name='ticket_creation_agent',
  instruction=load_instruction_from_file("ticket_creation_agent.prompt"),
  tools=[
    # zammad_client.init_zammad_client,
    zammad_client.create_ticket,
  ],
)

ticket_update_agent = LlmAgent(
  model=model_name,
  name='ticket_update_agent',
  instruction=load_instruction_from_file("ticket_update_agent.prompt"),
  tools=[
    # zammad_client.init_zammad_client,
    zammad_client.set_ticket_state,
    zammad_client.set_ticket_priority,
    zammad_client.send_message_to_ticket,
  ],
)

ticketing_orchestrator = SequentialAgent(
    name='ticketing_orchestrator',
    description='This agent orchestrates the workflow for Zammad ticketing requests.',
    sub_agents=[
        ticket_classifier_agent,
        ticket_search_agent,
        ticket_creation_agent,
        ticket_update_agent,
    ],
)