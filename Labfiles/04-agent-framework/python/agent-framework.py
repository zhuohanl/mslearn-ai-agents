import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add references
from agent_framework import AgentThread, ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field
from typing import Annotated


# Load environment variables from .env file
load_dotenv()
project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

async def main():
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')

    # Load the expenses data file
    script_dir = Path(__file__).parent
    file_path = script_dir / 'data.txt'
    with file_path.open('r') as file:
        data = file.read() + "\n"

    # Display the data
    print(f"Here is the expenses data in your file:\n\n{data}")
    
    # Create a chat agent
    async with (
        # the AzureCliCredential object will automatically include the Azure AI Foundry project settings from the configuration
        AzureCliCredential() as credential,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                    project_endpoint=project_endpoint,
                    model_deployment_name=model_deployment,
                    async_credential=credential,
                ),
            name="expenses_agent",
            instructions=f"""You are an AI assistant for expense claim submission.
                            Here is the expenses data you're working with:
                            {data}
                            
                            When a user requests an expense claim, use the plug-in function to send an email to expenses@contoso.com with the subject 'Expense Claim' and a body that contains itemized expenses with a total.
                            Then confirm to the user that you've done so.""",
            tools=send_email,
        ) as agent,
    ):
        # Create the agent thread for ongoing conversation
        thread = agent.get_new_thread()

        # Conversation loop
        while True:
            # Get user input
            user_prompt = input("\nWhat would you like me to do? (or type 'quit' to exit): ")
            
            # Check for exit condition
            if user_prompt.lower() in ["quit", "exit", "bye"]:
                print("Goodbye!")
                break
            
            # Skip empty inputs
            if not user_prompt.strip():
                continue
            
            # Process the user's request
            await process_expenses_data(agent, thread, user_prompt)


async def process_expenses_data(agent, thread, user_prompt):
    """Process user request with the agent"""
    try:
        # Invoke the agent with the user's message
        # The expenses data is already in the agent's instructions
        response = await agent.run([user_prompt], thread=thread)
        # Display the response
        print(f"\nAgent: {response}")
    except Exception as e:
        # Something went wrong
        print(f"\nError: {e}")


# Create a tool function for the email functionality
def send_email(
        to: Annotated[str, Field(description="Who to send the email to")],
        subject: Annotated[str, Field(description="The subject of the email.")],
        body: Annotated[str, Field(description="The text body of the email.")]):
    print("\nTo:", to)
    print("Subject:", subject)
    print(body, "\n")


if __name__ == "__main__":
    asyncio.run(main())
