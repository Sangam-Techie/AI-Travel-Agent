from typing import List, Dict, Any, Callable, Optional
from src.llm_client import LLMClient
import json
from datetime import datetime


class AgentLoop:
    """
    Core agent loop implementation.

    This handles:
    - Conversation state
    - Tool calling loop
    - LLM interactions
    """

    def __init__(
        self,
        system_prompt: str,
        tools: List[Dict],
        tool_functions: Dict[str, Callable],
        max_iterations: int = 10,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ):
        """
        Initialize the agent.

        Args:
            system_prompt: Instructions for the LLM
            tools: Tool definitions in OpenAI format
            tool_functions: Dict mapping tool names to actual functions
            max_iterations: Default cap on tool-calling loops per run() call
            temperature: Default sampling temperature for LLM calls
            max_tokens: Default max output tokens for LLM calls
        """
        self.llm = LLMClient()
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_functions = tool_functions
        self.default_max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Conversation state - starts with system message
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Traces for debugging/observability
        self.traces = []

        # Tracked so a server can expire idle sessions
        self.last_active = datetime.now()

    async def run(self, user_message: str, max_iterations: Optional[int] = None) -> str:
        """
        Run the agent loop for a user message.

        Args:
            user_message: The user's input
            max_iterations: Max tool calling loops for this call (falls back to the
                instance default, which is normally driven by app config)

        Returns:
            The agent's final response
        """
        max_iterations = max_iterations or self.default_max_iterations
        self.last_active = datetime.now()

        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})

        # Run the agent loop
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- Agent Loop Iteration {iteration} ---")

            try:
                response = await self.llm.chat_with_tools(
                    messages=self.messages,
                    tools=self.tools,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as e:
                # A network blip or upstream outage shouldn't crash the whole request -
                # tell the user plainly instead of a raw 500.
                error_msg = (
                    "I'm having trouble reaching the language model right now "
                    f"({e}). Please try again in a moment."
                )
                self.traces.append({"iteration": iteration, "event": "llm_error", "error": str(e)})
                self.messages.append({"role": "assistant", "content": error_msg})
                return error_msg

            # Extract the assistant's message
            assistant_message = response["choices"][0]["message"]

            now = datetime.now()

            # Log the "thought" for observability
            self.traces.append({
                "iteration": iteration,
                "role": "assistant",
                "content": assistant_message.get("content"),
                "tool_calls": assistant_message.get("tool_calls"),
                "timestamp": f"{now:%Y-%m-%d %H:%M:%S}"
            })

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
        return (
            "I apologize, but I'm having trouble completing this request within the "
            "allowed steps. Could you try rephrasing or narrowing your request?"
        )

    async def _execute_tool_call(self, tool_call: Dict) -> None:
        """
        Execute a single tool call and add result to messages.

        Args:
            tool_call: The tool call from LLM response
        """
        tool_name = tool_call["function"]["name"]
        tool_args_str = tool_call["function"]["arguments"]
        tool_id = tool_call["id"]
        self.traces.append({"event": "tool_start", "tool_id": tool_id, "tool": tool_name, "args": tool_args_str})

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
            self.traces.append({"event": "tool_result", "tool_id": tool_id, "tool": tool_name, "result": result})

            print("Tool executed successfully")

        except Exception as e:
            # If tool fails, tell the LLM about the error
            error_msg = f"Error executing {tool_name}: {str(e)}"
            print(f"{error_msg}")

            self.messages.append({"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": json.dumps({"error": error_msg})})
            self.traces.append({"event": "tool_error", "tool_id": tool_id, "tool": tool_name, "error": error_msg})

    def get_traces(self):
        return self.traces

    def get_conversation_history(self) -> List[Dict]:
        """Get the full conversation history."""
        return self.messages.copy()

    def reset(self) -> None:
        """Reset conversation to initial state."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.traces = []
        self.last_active = datetime.now()