from botbuilder.core import ActivityHandler, TurnContext, ConversationState
from botbuilder.schema import ActivityTypes, ChannelAccount, CardAction, ActionTypes, SuggestedActions, Activity, Attachment
import requests
import os
import json
import asyncio
from dotenv import load_dotenv
from assets_list import ASSETS_LIST  # Import the assets list

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
        # Handle both text messages and adaptive card submissions
        if (user_message and user_message == "Show my assets") or \
           (turn_context.activity.value and isinstance(turn_context.activity.value, dict) and \
            turn_context.activity.value.get("text") == "Show my assets"):
            await self._handle_show_my_assets(turn_context)
            return
            
        # Check if this is a submission from a multi-select card
        if turn_context.activity.value and isinstance(turn_context.activity.value, dict):
            # Log the received value for debugging
            print(f"Received activity value: {turn_context.activity.value}")
            
            # Process the multi-select response
            if "action" in turn_context.activity.value and turn_context.activity.value["action"] == "multiselect_submit":
                # Get the selected items from the ChoiceSet
                selected_items = turn_context.activity.value.get("multiSelectValues", [])
                # If it's a string (comma-separated values), split it
                if isinstance(selected_items, str):
                    selected_items = [item.strip() for item in selected_items.split(',')]
                    
                print(f"Selected items from dropdown: {selected_items}")
            elif "multiSelectValues" in turn_context.activity.value:
                # For backward compatibility with the old dropdown
                selected_items = turn_context.activity.value.get("multiSelectValues", [])
                # If it's a string (comma-separated values), split it
                if isinstance(selected_items, str):
                    selected_items = [item.strip() for item in selected_items.split(',')]
            else:
                # No recognized selection format
                selected_items = []
            
            # Send typing indicator while processing
            await turn_context.send_activity(Activity(type=ActivityTypes.typing))
            
            # Convert selected items to a comma-delimited string
            selected_items_text = ", ".join(selected_items)
            
            # Send the selected items to Langflow
            response_data = self.run_flow(
                message=f"Selected items: {selected_items_text}",
                endpoint=ENDPOINT or FLOW_ID
            )
            
            # Extract and send the response
            bot_response = self.extract_text_from_langflow_response(response_data)
            await self._send_response_with_options(turn_context, bot_response)
            return
        
        try:
            # Send typing indicator while processing
            await turn_context.send_activity(Activity(type=ActivityTypes.typing))
            
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
                
                # Check if the response contains the trigger keyword for multi-select dropdown
                if bot_response.startswith("SHOW_DROPDOWN:"):
                    # Parse the items to show in the dropdown
                    dropdown_content = bot_response.replace("SHOW_DROPDOWN:", "").strip()
                    items = [item.strip() for item in dropdown_content.split(",")]
                    
                    # Create and send the multi-select dropdown card
                    await self._send_multi_select_card(turn_context, "Please select items:", items)
                    return
                # Check if the response contains the trigger keyword for asset dropdown anywhere in the message
                # Normalize the response by replacing newlines with spaces to handle multi-line responses
                normalized_response = bot_response.replace("\n", " ")
                if "SHOW_ASSET_DROPDOWN" in normalized_response or "SHOW_ASSET_DROPDOWN" in bot_response:
                    # Log the detection for debugging
                    print(f"Asset dropdown trigger detected in: {bot_response}")
                    # Extract any message text before the keyword to use as the prompt
                    # First try with normalized response
                    if "SHOW_ASSET_DROPDOWN" in normalized_response:
                        prompt_parts = normalized_response.split("SHOW_ASSET_DROPDOWN")
                    else:
                        prompt_parts = bot_response.split("SHOW_ASSET_DROPDOWN")
                    prompt_text = prompt_parts[0].strip()
                    if not prompt_text:  # If there's no text before the keyword, use a default prompt
                        prompt_text = "Please select the assets you need access to:"
                    
                    # Use the predefined assets list
                    # Create and send the multi-select dropdown card with assets
                    await self._send_multi_select_card(turn_context, prompt_text, ASSETS_LIST)
                    return
                
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
        # We're not sending any welcome message when a new user is added
        # This prevents duplicate messages when a user opens the chat
        pass
    
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
        
        # Create an adaptive card with a larger button
        # Passing an empty string for the message text to remove the 'What would you like to do next?' text
        card = self._create_adaptive_card_with_button("", "Show my assets")
        
        # Create an activity with the adaptive card
        reply = Activity(
            type=ActivityTypes.message,
            attachments=[card]
        )
        
        # Send the card
        await turn_context.send_activity(reply)
    
    def _create_adaptive_card_with_button(self, message_text: str, button_title: str) -> Attachment:
        """
        Create an adaptive card with a larger, more prominent button.
        
        Args:
            message_text: The text to display in the message.
            button_title: Text to display on the button.
            
        Returns:
            An Attachment containing the adaptive card.
        """
        card_content = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.0",
            "body": [
                {
                    "type": "TextBlock",
                    "text": message_text,
                    "wrap": True,
                    "size": "Medium"
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": button_title,
                    "data": {"text": button_title},
                    "style": "positive",
                    "size": "large"
                }
            ]
        }
        
        return Attachment(
            content_type="application/vnd.microsoft.card.adaptive",
            content=card_content
        )
        
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
            
    async def _send_multi_select_card(self, turn_context: TurnContext, prompt_text: str, items: list) -> None:
        """
        Create and send an adaptive card with a multi-select dropdown.
        
        Args:
            turn_context: The turn context for the current conversation.
            prompt_text: The text to display above the dropdown.
            items: List of items to display in the dropdown.
        """
        # Log that we're sending a multi-select card for debugging
        print(f"Sending multi-select card with prompt: {prompt_text}")
        print(f"Items to display: {items}")
        
        # Create a multi-select dropdown with built-in search functionality
        card_content = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.2",
            "body": [
                {
                    "type": "TextBlock",
                    "text": prompt_text,
                    "wrap": True,
                    "size": "Medium",
                    "weight": "Bolder"
                },
                {
                    "type": "TextBlock",
                    "text": "Select all assets you need access to:",
                    "wrap": True,
                    "size": "Small"
                },
                {
                    "type": "Input.ChoiceSet",
                    "id": "multiSelectValues",
                    "isMultiSelect": True,
                    "style": "filtered",  # This adds a search box that actually works
                    "choices": [{"title": item, "value": item} for item in items],
                    "placeholder": "Search and select assets..."
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Submit",
                    "data": {"action": "multiselect_submit"}
                }
            ]
        }
        
        # First send a plain text message to ensure Teams is ready to receive the card
        await turn_context.send_activity("Please select from the options below:")
        
        # Create an attachment with the adaptive card
        attachment = Attachment(
            content_type="application/vnd.microsoft.card.adaptive",
            content=card_content
        )
        
        # Create and send the activity with the attachment
        reply = Activity(
            type=ActivityTypes.message,
            attachments=[attachment]
        )
        
        # Add a small delay to ensure Teams processes the messages in order
        await asyncio.sleep(0.5)
        
        await turn_context.send_activity(reply)
