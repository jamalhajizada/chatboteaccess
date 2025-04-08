import os
import sys
import traceback
import logging
import json
from aiohttp import web
from aiohttp.web import Request, Response
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
    ConversationState,
    MemoryStorage
)
from botbuilder.schema import Activity, ActivityTypes
from botframework.connector import ConnectorClient
from bot import EchoBot
from dotenv import load_dotenv
import requests
import ssl
import graph_helper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app')

# Configure SSL - this is needed if there's a corporate proxy or custom CA
# Add this before any HTTP requests are made
requests.packages.urllib3.disable_warnings()

# Load environment variables
load_dotenv()
APP_ID = os.getenv("MicrosoftAppId", "")
APP_PASSWORD = os.getenv("MicrosoftAppPassword", "")
TENANT_ID = os.getenv("MicrosoftAppTenantId", "")

# For local development with the emulator, you can set this to True
# For production deployment to Azure, set this to False
DEV_MODE = os.getenv("DEV_MODE", "False") == "True"
# Control whether to verify SSL certificates
VERIFY_SSL = os.getenv("VERIFY_SSL", "True") == "True"

if DEV_MODE:
    logger.info("DEVELOPMENT MODE: Authentication disabled for local testing with Bot Framework Emulator")
    # Empty strings disable authentication
    SETTINGS = BotFrameworkAdapterSettings("", "")
else:
    logger.info("PRODUCTION MODE: Authentication enabled for Azure deployment")
    # Use real credentials for production
    SETTINGS = BotFrameworkAdapterSettings(
        app_id=APP_ID, 
        app_password=APP_PASSWORD,
        channel_auth_tenant=TENANT_ID  # Specify tenant for single-tenant apps
    )

# Configure SSL verification
if not VERIFY_SSL:
    logger.warning("WARNING: SSL certificate verification is disabled. This is not recommended for production.")
    # Disable SSL verification globally
    ssl._create_default_https_context = ssl._create_unverified_context
    # This affects all HTTPS requests in the application

ADAPTER = BotFrameworkAdapter(SETTINGS)

# Create memory storage and state
MEMORY = MemoryStorage()
CONVERSATION_STATE = ConversationState(MEMORY)

# Initialize the bot with conversation state
BOT = EchoBot(CONVERSATION_STATE)

# Error handler
async def on_error(context: TurnContext, error: Exception):
    # Log error details for debugging
    logger.error(f"Bot error: {type(error).__name__} - {str(error)}")
    logger.error("Stack trace:", exc_info=True)
    
    # Save state changes
    if CONVERSATION_STATE and context:
        try:
            await CONVERSATION_STATE.save_changes(context)
        except Exception as err:
            logger.error(f"Error saving state: {str(err)}")
    
    # Send a message to the user
    if context and context.activity and context.activity.type == ActivityTypes.message:
        await context.send_activity("The bot encountered an error. Administrators have been notified.")
    
ADAPTER.on_turn_error = on_error

async def messages(req: Request) -> Response:
    if req.method == 'OPTIONS':
        return Response(status=200, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': '*'
        })

    try:
        # Handle authentication and request headers
        logger.info("Received API request")
        auth_header = req.headers.get("Authorization", "")
        
        # Get activity from request
        body = await req.json()
        activity = Activity().deserialize(body)
        
        # Log basic activity details
        logger.info(f"Activity type: {activity.type}, Channel ID: {activity.channel_id}")
        
        # Log message content and sender info for message activities
        if activity.type == ActivityTypes.message:
            user_id = activity.from_property.id if activity.from_property else 'Unknown'
            user_name = activity.from_property.name if activity.from_property and hasattr(activity.from_property, 'name') else 'Unknown'
            logger.info(f"Message from {user_name} ({user_id}): {activity.text}")
            
            # Get tenant ID if available from channel_data
            tenant_id = None
            if (hasattr(activity, 'channel_data') and activity.channel_data and 
                isinstance(activity.channel_data, dict) and 'tenant' in activity.channel_data and 
                'id' in activity.channel_data['tenant']):
                tenant_id = activity.channel_data['tenant']['id']
                logger.debug(f"Tenant ID: {tenant_id}")
            
            # Lookup AD account using Graph API - use only one method
            if activity.from_property:
                ad_info = graph_helper.get_ad_account_for_teams_user(activity)
                if ad_info and "upn" in ad_info:
                    logger.info(f"User identified as: {ad_info.get('upn')}")
        
        # For conversation update activities, log members added/removed
        elif activity.type == ActivityTypes.conversation_update:
            if activity.members_added:
                for member in activity.members_added:
                    logger.info(f"Member added: {member.id} ({member.name if hasattr(member, 'name') else 'Unknown'})")
            
            if activity.members_removed:
                for member in activity.members_removed:
                    logger.info(f"Member removed: {member.id} ({member.name if hasattr(member, 'name') else 'Unknown'})")

        # Process the activity through the adapter
        await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        
        return Response(status=201)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return Response(status=500, text=str(e))

app = web.Application()
app.router.add_post("/api/messages", messages)
app.router.add_options("/api/messages", messages)

if __name__ == "__main__":
    try:
        logger.info(f"Starting server on port {os.getenv('PORT', 3979)}")
        web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 3979)))
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
