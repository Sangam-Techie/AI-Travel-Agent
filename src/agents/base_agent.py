from typing import List, Dict, Any, Callable
from src.llm_client import LLMClient
import json

class AgentLoop:
    """
    Core agent loop implementation.

    This handles:
    -Conversation state
    -Tool calling loop
    -LLM interactions
    """

    def __init__(self, system_prompt: str, tools: List[Dict], tool_functions: Dict[str, Callable]):
        """
        Initialize the agent.

        Args:
            system_prompt: Instructions for the LLM
            tools: Tool definitions in OpenAI format
            tool_functions: Dict mapping tool names to actual functions
        """
        self.llm = LLMClient()
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_functions = tool_functions

        # Conversation state - starts with system message
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

    async def run(self, user_message: str, max_iterations: int = 5) -> str:
        """
        Run the agent loop for a user message.

        Args:
            user_message: The user's input
            max_iterations: Max tool calling loops (prevents infinite loop)

        Returns:
            The agent's final response
        """
        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})

        # Run the agent loop
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- Agent Loop Iteration {iteration} ---")

            # Get LLM response with tools
            response = await self.llm.chat_with_tools(messages=self.messages, tools=self.tools)

            # Extract the assistant's message
            assistant_message = response["choices"][0]["message"]

            # Check if LLM wants to call tools
            tool_calls = assistant_message.get("tool_calls")

            if not tool_calls:
                # No tools needed - we have final response
                final_response = assistant_message["content"]

                # Add to history
                self.messages.append({"role": "assistant", "content": final_response})

                print(f"Final response ready: {final_response[:100]}....")
                return final_response

            # LLM wants to call tools
            print(f"LLM requested {len(tool_calls)} tool call(s)")

            # Add assistant message with tool calls to history
            self.messages.append({"role": "assistant", "content": assistant_message.get("content"), "tool_calls": tool_calls})

            # Execute each tool call
            for tool_call in tool_calls:
                await self._execute_tool_call(tool_call)

            # Loop continues - send tool results back to LLM

        # If we hit max iterations, return what we have
        return "I apologize, but I'm having trouble completing this request. Please try again"
    
    async def _execute_tool_call(self, tool_call: Dict) -> None:
        """
        Execute a single tool call and add result to messages.

        Args:
            tool_call: The tool call from LLM response
        """
        tool_name = tool_call["function"]["name"]
        tool_args_str = tool_call["function"]["arguments"]
        tool_id = tool_call["id"]

        print(f" Calling tool: {tool_name}")
        print(f" Arguments: {tool_args_str}")

        try:
            # Parse arguments
            tool_args = json.loads(tool_args_str)

            # Get the actual function
            if tool_name not in self.tool_functions:
                raise ValueError(f"Unknown tool: {tool_name}")

            func = self.tool_functions[tool_name]
            # Call the function
            result = await func(**tool_args)
            # Add result to messages
            self.messages.append({"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": json.dumps(result)})

            print("Tool executed successfully")

        except Exception as e:
            # If tool fails, tell the LLM about the error
            error_msg = f"Error executing {tool_name}: {str(e)}"
            print(f"{error_msg}")

            self.messages.append({"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": json.dumps({"error": error_msg})})

    
    def get_conversation_history(self) -> List[Dict]:
        """Get the full conversation history."""
        return self.messages.copy()

    def reset(self) -> None:
        """Reset converstion to initail state."""
        self.messages = [{"role": "system", "content": self.system_prompt}]