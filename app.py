import os
import time
import json
import openai
import http.client
import urllib.parse
import streamlit as st
#from dotenv import load_dotenv

# Load environment variables
#load_dotenv()

# Define the shipment tracking function
def track_shipment(tracking_number):
    dhl_api_key = os.getenv("DHL_API_KEY")

    params = urllib.parse.urlencode({
        'trackingNumber': tracking_number,
        'service': 'express'
    })

    headers = {
        'Accept': 'application/json',
        'DHL-API-Key': dhl_api_key
    }

    connection = http.client.HTTPSConnection("api-eu.dhl.com")

    connection.request("GET", "/track/shipments?" + params, "", headers)
    response = connection.getresponse()
    data = json.loads(response.read())
    connection.close()

    try: 
        if data['shipments']:
            return f"""Here is the information about the Shipment with tracking number {tracking_number}: \n
                - The status of the shipment is : {data['shipments'][0]['status']['description']} \n
                - The last status was updated at : {data['shipments'][0]['status']['timestamp']} \n
                - The origin of the shipment is : {data['shipments'][0]['origin']['address']['addressLocality']} \n
                - The destination of the shipment is : {data['shipments'][0]['destination']['address']['addressLocality']} \n
            """
    except: 
        return "Shipment not found"

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

assistant_id = 'asst_oTzsHowM6w0wACIQDiCwyFju'

# Streamlit interface
st.title("Shipment Tracker")

# Initialize conversation history in session state
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# Function to display conversation history
def display_conversation():
    for entry in st.session_state.conversation_history:
        if entry["role"] == "user":
            message = st.chat_message("user")
        else:
            message = st.chat_message("assistant")
        message.write(entry["content"])

# Display the conversation history at the beginning
display_conversation()

# Use st.chat_input for user input
prompt = st.chat_input("Ask Something")
if prompt:
    # Add user's message to conversation history
    st.session_state.conversation_history.append({"role": "user", "content": prompt})
    # Display the new user message immediately
    st.chat_message("user").write(prompt)

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Create a thread
    thread = client.beta.threads.create()

    # Add a message to the thread
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"{prompt}"
    )

    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

        if run_status.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )

            for msg in messages.data:
                role = msg.role
                content = msg.content[0].text.value
                if role == 'assistant':
                    st.session_state.conversation_history.append({"role": "assistant", "content": content})
                    # Display the new assistant message immediately
                    st.chat_message("assistant").write(content)
            break
        elif run_status.status == 'requires_action':
            required_actions = run_status.required_action.submit_tool_outputs.model_dump()
            tool_outputs = []
            for action in required_actions["tool_calls"]:
                func_name = action["function"]["name"]
                arguments = json.loads(action["function"]["arguments"])
                if func_name == "track_shipment":
                    output = track_shipment(arguments["tracking_number"])
                    tool_outputs.append({
                        "tool_call_id": action["id"],
                        "output": output
                    })

                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
        else:
            time.sleep(0.0001)
