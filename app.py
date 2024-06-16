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
    status = data['shipments'][0]['status']['description']
    connection.close()

    return status

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPEN_AI_KEY"))

assistant_id = 'asst_oTzsHowM6w0wACIQDiCwyFju'

# Fetching the assistant
assistant = client.beta.assistants.retrieve(
    assistant_id=assistant_id
)

# Streamlit interface
st.title("Shipment Tracker")

#prompt = st.text_input("Enter your prompt", )
prompt = st.chat_input("Ask Something")
if prompt:
    st.write(f"{prompt}")
#if st.button("Track Shipment"):
    if prompt:
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
            assistant_id=assistant.id
        )

        #st.write("Tracking your shipment, please wait...")

        while True:
            #time.sleep(5)

            # Retrieve the status of the run
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

            if run_status.status == 'completed':
                messages = client.beta.threads.messages.list(
                    thread_id=thread.id
                )

                # Loop through the messages to find the assistant's response
                for msg in messages.data:
                    role = msg.role
                    content = msg.content[0].text.value
                    if role == 'assistant':
                        #st.success(content)
                        message = st.chat_message("assistant")
                        message.write(content)
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

                        # Submit the tool outputs to Assistant API
                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
            else:
                time.sleep(5)
    else:
        st.error("Please enter a valid tracking number.")
