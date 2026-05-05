import asyncio
from agents import Agent, Runner

async def main():
    test_val = None
    
    async def my_tool(input_str: str) -> str:
        """A simple tool"""
        nonlocal test_val
        test_val = input_str
        return "Success"
        
    my_agent = Agent(name="Test", instructions="Just call my_tool with 'hello'", tools=[my_tool])
    result = await Runner.run(my_agent, "Do the thing")
    print("Result attributes:", dir(result))
    if hasattr(result, "messages"):
        print("Messages:", result.messages)
    print("Captured value:", test_val)

if __name__ == "__main__":
    asyncio.run(main())
