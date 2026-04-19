# AI Travel Agent

A production-ready travel assistant powered by large language models with real-time flight and weather data integration.

🌐 Live Demo

- Frontend (Streamlit): https://ai-travel-agent-frontend-ym7d.onrender.com

- API Documentation (FastAPI): https://ai-travel-agent-zp3u.onrender.com



## 🌟 Features

- **Intelligent Agent Loop**: Custom-built agent that decides when to call tools vs respond directly
- **Real Flight Search**: Integration with Amadeus API for live flight data
- **Weather Information**: Real-time weather data via OpenWeatherMap
- **RESTful API**: FastAPI-powered web service with automatic documentation
- **Session Management**: Maintains conversation context across multiple requests
- **Async Architecture**: Non-blocking operations for optimal performance
- **Frontend**: Streamlit for high-performance AI prototyping.
- **Observability**: Custom JSON Tracing for monitoring agent "thought" iterations.

🕵️ Observability & Tracing

- Unlike standard chatbots, this agent features a Developer Mode. It exposes the "Inner Monologue" of the LLM, showing exactly when a tool is called, the   arguments passed, and the latency of each step. This is critical for debugging complex agentic workflows.

🚀 Deployment

- Deployed using a Two-Tier Architecture on Render. The frontend and backend are decoupled, communicating via secure REST endpoints with CORS protection.

## 🏗️ Architecture
```
User Request → FastAPI Server → Agent Loop → LLM (Groq)
                                     ↓
                              Tool Selection
                                     ↓
                         ┌───────────┴───────────┐
                         ↓                       ↓
                  Amadeus API            OpenWeather API
                  (Flights)                 (Weather)
                         ↓                       ↓
                         └───────────┬───────────┘
                                     ↓
                              Format Response
                                     ↓
                              Return to User
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- API Keys (all free tier):
  - [Groq](https://console.groq.com/)
  - [Amadeus](https://developers.amadeus.com/)
  - [OpenWeatherMap](https://openweathermap.org/api)

### Installation

1. **Clone the repository:**
```bash
   git clone https://github.com/Sangam-Techie/AI-Travel-Agent.git
   cd travel-agent-tutorial
```

2. **Create virtual environment:**
```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Or using standard venv
   python -m venv .venv
   source .venv/bin/activate
```

3. **Install dependencies:**
```bash
   uv pip install fastapi uvicorn httpx python-dotenv pydantic pydantic-settings
```

4. **Set up environment variables:**
```bash
   cp .env.example .env
   # Edit .env and add your API keys
```

5. **Run the server:**
```bash
   python src/main.py
```

6. **Test it out:**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## 📖 API Usage

### Chat Endpoint

**Request:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find me flights from NYC to Paris next week",
    "session_id": "user123"
  }'
```

**Response:**
```json
{
  "response": "I found 3 flights from NYC to Paris...",
  "session_id": "user123"
}
```

### Conversation History
```bash
curl http://localhost:8000/history/user123
```

### Reset Conversation
```bash
curl -X POST http://localhost:8000/reset/user123
```

## 🧪 Testing
```bash
# Run API tests
python tests/test_api.py

# Test individual components
python src/llm_client.py          # Test LLM connection
python src/tools/travel_tools.py  # Test API integrations
python src/agents/travel_agent.py # Test complete agent
```

## 📁 Project Structure
```
travel-agent-tutorial/
├── src/
│   ├── agents/
│   │   ├── base_agent.py      # Core agent loop
│   │   └── travel_agent.py    # Travel-specific agent
│   ├── tools/
│   │   └── travel_tools.py    # API integrations
│   ├── api/
│   │   ├── server.py          # FastAPI application
│   │   ├── models.py          # Request/response models
│   │   └── config.py          # Configuration
│   ├── llm_client.py          # LLM client wrapper
│   └── main.py                # Entry point
├── tests/
│   └── test_api.py            # API tests
├── .env                       # Environment variables (not in git)
├── .gitignore
└── README.md
```

## 🔑 Key Learnings

This project demonstrates:

1. **Agent Loop Architecture**: Hand-built agent without frameworks to understand the fundamentals
2. **Tool Calling**: How LLMs decide when and how to use external tools
3. **Async Programming**: Why and how to use async for API-heavy applications
4. **State Management**: Maintaining conversation context across requests
5. **API Design**: Building a clean RESTful API with FastAPI
6. **Real-world Integration**: Working with actual third-party APIs

## 🐛 Troubleshooting

**Server won't start:**
- Check that all API keys are set in `.env`
- Verify Python version: `python --version` (should be 3.11+)
- Check if port 8000 is already in use

**API calls failing:**
- Verify API keys are valid
- Check API rate limits (free tiers have limits)
- Review logs for specific error messages

**Agent not calling tools:**
- Check tool definitions in `travel_agent.py`
- Verify LLM has access to tools
- Review system prompt clarity

## 📝 License

MIT License - feel free to use this for learning!

## 🙏 Acknowledgments

- Built as part of a progressive AI engineering learning path
- APIs: Groq, Amadeus, OpenWeatherMap
- Framework: FastAPI
