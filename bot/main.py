import argparse
import asyncio
import os

from dotenv import load_dotenv

from bot.agent import run_agent


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Chat with the appointment assistant")
    parser.add_argument("message", nargs="?", help="Message to send to the assistant")
    parser.add_argument("--conversation-id", default="default")
    parser.add_argument("--user-id", default=os.getenv("APPOINTMENTS_USER_ID"))
    args = parser.parse_args()
    message = args.message or input("You: ")
    if args.user_id:
        message = f"User ID: {args.user_id}\n{message}"
    response = asyncio.run(run_agent(message, args.conversation_id))
    print(response)


if __name__ == "__main__":
    main()
