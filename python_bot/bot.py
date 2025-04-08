from botbuilder.core import ActivityHandler, TurnContext, ConversationState
from botbuilder.schema import ActivityTypes, ChannelAccount, CardAction, ActionTypes, SuggestedActions, Activity
import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables if needed
load_dotenv()

# Langflow configuration
BASE_API_URL = "http://localhost:7860"
FLOW_ID = "0e85cb16-da5e-4ec7-9834-54e98ac79a64" 
#FLOW_ID = "62594e4c-1649-4c8b-a274-63a25b5019c9" just AD straight.
ENDPOINT = ""  # You can set a specific endpoint name in the flow settings

# Tweaks dictionary for the Langflow flow
TWEAKS = {
  "ChatInput-EbPFZ": {},
  "ChatOutput-ydVia": {},
  "CustomComponent-Pr7PM": {},
  "CustomComponent-RyD4d": {}
}

class EchoBot(ActivityHandler):
    def __init__(self, conversation_state=None):
        self.conversation_state = conversation_state
    
    async def on_message_activity(self, turn_context: TurnContext):
        # Get the message from the user
        user_message = turn_context.activity.text
        
        # Check if this is a button click for "Show my assets"
        if user_message and user_message == "Show my assets":
            await self._handle_show_my_assets(turn_context)
            return
        
        try:
            # Call the Langflow API
            response_data = self.run_flow(
                message=user_message,
                endpoint=ENDPOINT or FLOW_ID
            )
            
            # Extract only the text content from the Langflow response
            bot_response = "No response content found"
            
            try:
                # Extract text using our helper method
                bot_response = self.extract_text_from_langflow_response(response_data)
                print(f"Extracted response: {bot_response}")
                
            except Exception as extract_error:
                print(f"Error extracting text from response: {str(extract_error)}")
                
            # Send the response back to the user with the "Show my assets" button
            await self._send_response_with_options(turn_context, bot_response)
        except requests.exceptions.ConnectionError:
            # Handle connection errors specifically for when langflow is down
            error_message = "I'm being fixed, my AI module is not responding right now for some reason. Please try again later."
            print(f"Langflow connection error: Unable to connect to {BASE_API_URL}")
            await turn_context.send_activity(error_message)
        except requests.exceptions.Timeout:
            # Handle timeout errors
            error_message = "I'm taking too long to respond due to backend issues. Please try again later."
            print(f"Langflow timeout error: Request to {BASE_API_URL} timed out")
            await turn_context.send_activity(error_message)
        except requests.exceptions.RequestException as e:
            # Handle other request-related errors
            error_message = "I'm experiencing some technical difficulties with my AI module right now. Please try again later."
            print(f"Langflow request error: {str(e)}")
            await turn_context.send_activity(error_message)
        except Exception as e:
            # Handle any other unexpected errors
            error_message = "An unexpected error occurred. Our team has been notified."
            print(f"Unexpected error processing message: {str(e)}")
            await turn_context.send_activity(error_message)
    
    async def on_members_added_activity(self, member_added: ChannelAccount, turn_context: TurnContext):
        # Send a welcome message when a new user is added
        for member in member_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello to eAccess, now all you can do is type in an AD account, and I will pull the user's accesses for you to review.")
    
    async def on_turn(self, turn_context: TurnContext):
        # Process the activity based on its type
        if turn_context.activity.type == ActivityTypes.message:
            await self.on_message_activity(turn_context)
        elif turn_context.activity.type == ActivityTypes.conversation_update:
            if turn_context.activity.members_added:
                await self.on_members_added_activity(turn_context.activity.members_added, turn_context)
        
        # Save state changes at the end of the turn
        if self.conversation_state:
            await self.conversation_state.save_changes(turn_context)
    
    def extract_text_from_langflow_response(self, response_data):
        """
        Extract the text content from the Langflow response.
        
        Navigates the complex JSON structure to find the 'text' field
        that contains the actual message to be sent to the user.
        """
        try:
            # Check if the structure matches what we expect
            if "outputs" in response_data and len(response_data["outputs"]) > 0:
                first_output = response_data["outputs"][0]
                
                if "outputs" in first_output and len(first_output["outputs"]) > 0:
                    output_data = first_output["outputs"][0]
                    
                    # Try to find the text field following the path in the example
                    if ("results" in output_data and 
                        "message" in output_data["results"] and 
                        "data" in output_data["results"]["message"] and 
                        "text" in output_data["results"]["message"]["data"]):
                        
                        # This is the path shown in the example
                        return output_data["results"]["message"]["data"]["text"]
                    
                    # Alternative path that might exist
                    if "results" in output_data and "message" in output_data["results"]:
                        msg = output_data["results"]["message"]
                        if isinstance(msg, str):
                            return msg
                        elif isinstance(msg, dict) and "text" in msg:
                            return msg["text"]
                    
                    # Check in artifacts
                    if "artifacts" in output_data and "message" in output_data["artifacts"]:
                        return output_data["artifacts"]["message"]
                    
                    # Check in outputs
                    if "outputs" in output_data and "message" in output_data["outputs"]:
                        msg_output = output_data["outputs"]["message"]
                        if isinstance(msg_output, str):
                            return msg_output
                        elif isinstance(msg_output, dict) and "message" in msg_output:
                            return msg_output["message"]
                
                # Try the messages array as a fallback
                if "messages" in first_output and len(first_output["messages"]) > 0:
                    if "message" in first_output["messages"][0]:
                        return first_output["messages"][0]["message"]
            
            # If we couldn't extract the text through the expected path,
            # check for a simple result field
            if "result" in response_data:
                return response_data["result"]
            
            # Last resort: return a message indicating we couldn't extract the text
            return "I received a response but couldn't extract the text content properly."
            
        except Exception as e:
            # If any extraction error occurs, log it and return a fallback message
            print(f"Error extracting text from Langflow response: {str(e)}")
            return f"I received your message but encountered an error parsing the response: {str(e)}"
    
    def run_flow(self, message, endpoint, output_type="chat", input_type="chat", tweaks=None, api_key=None):
        """
        Run a flow with a given message and optional tweaks.
        
        :param message: The message to send to the flow
        :param endpoint: The ID or the endpoint name of the flow
        :param tweaks: Optional tweaks to customize the flow
        :return: The JSON response from the flow
        """
        api_url = f"{BASE_API_URL}/api/v1/run/{endpoint}"
        
        payload = {
            "input_value": message,
            "output_type": output_type,
            "input_type": input_type,
        }
        
        headers = None
        if tweaks:
            payload["tweaks"] = tweaks
        if api_key:
            headers = {"x-api-key": api_key}
            
        response = requests.post(api_url, json=payload, headers=headers)
        return response.json()
        
    async def _send_response_with_options(self, turn_context: TurnContext, message_text: str) -> None:
        """
        Send a response with the "Show my assets" button.
        
        Args:
            turn_context: The turn context for the current conversation.
            message_text: The text to send in the message.
        """
        # First send the main message
        await turn_context.send_activity(message_text)
        
        # Then send suggested actions with the "Show my assets" button
        reply = self._create_suggested_actions("What would you like to do next?", ["Show my assets"])
        await turn_context.send_activity(reply)
    
    def _create_suggested_actions(self, message_text: str, button_titles: list) -> Activity:
        """
        Create a message with suggested actions (buttons).
        
        Args:
            message_text: The text to display in the message.
            button_titles: List of texts to display on the buttons.
            
        Returns:
            An Activity with suggested action buttons.
        """
        card_actions = []
        for title in button_titles:
            card_actions.append(
                CardAction(
                    type=ActionTypes.im_back,
                    title=title,
                    value=title
                )
            )
            
        return Activity(
            type=ActivityTypes.message,
            text=message_text,
            suggested_actions=SuggestedActions(
                actions=card_actions
            )
        )
    
    async def _handle_show_my_assets(self, turn_context: TurnContext) -> None:
        """
        Handle the "Show my assets" button click by retrieving user email and querying Langflow.
        
        Args:
            turn_context: The turn context for the current conversation.
        """
        try:
            # Send typing indicator while processing
            await turn_context.send_activity(Activity(type=ActivityTypes.typing))
            
            # Get the user's identity from MS Teams
            activity = turn_context.activity
            
            # Get user email using Graph API through the helper
            import graph_helper
            ad_info = graph_helper.get_ad_account_for_teams_user(activity)
            
            user_email = None
            if ad_info and "upn" in ad_info:
                user_email = ad_info.get("upn")
                print(f"Retrieved user email: {user_email}")
            
            if user_email:
                # Create a query to send to Langflow
                query = f"show this user's assets. User email: {user_email}"
                
                # Send to Langflow
                response_data = self.run_flow(
                    message=query,
                    endpoint=ENDPOINT or FLOW_ID
                )
                
                # Extract the response
                bot_response = self.extract_text_from_langflow_response(response_data)
                
                # Send the response with options
                await self._send_response_with_options(turn_context, bot_response)
            else:
                # If we couldn't retrieve the email
                await turn_context.send_activity("I couldn't identify your email address. Please try again later or contact support.")
        except Exception as e:
            print(f"Error handling 'Show my assets' request: {str(e)}")
            await turn_context.send_activity("I encountered an error trying to retrieve your assets. Please try again later.")
