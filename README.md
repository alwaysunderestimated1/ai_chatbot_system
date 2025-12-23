# AI Chatbot System

A production-ready AI chatbot backend built with **FastAPI**, **OpenAI GPT**, and **MongoDB**. Features streaming responses, RAG (Retrieval-Augmented Generation), tool use via function calling, OAuth2 authentication, and HTTP rate limiting.

---

## Features

- **Conversational AI** — Multi-turn chat powered by OpenAI GPT-4o with persistent session history
- **Streaming** — Real-time token streaming via Server-Sent Events
- **RAG Pipeline** — Ingest documents, chunk and embed them, retrieve relevant context automatically
- **Tool Use** — OpenAI function calling with built-in tools: datetime, calculator, knowledge base search
- **Session Management** — Create, list, rename, and delete conversations with auto-generated titles
- **OAuth2 Authentication** — JWT access/refresh tokens, user registration and login
- **Rate Limiting** — Global 100 req/min per IP, stricter limits on auth endpoints, per-user chat limits
- **MongoDB** — Async Motor driver with indexes for sessions, users, and document chunks

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| LLM | OpenAI GPT-4o (`openai` SDK) |
| Database | MongoDB (Motor async driver) |
| Auth | JWT (`PyJWT`) + bcrypt (`passlib`) |
| Rate limiting | `slowapi` |
| Embeddings | OpenAI `text-embedding-3-small` |
| Chunking | `tiktoken` (token-based) |
| Vector similarity | `numpy` cosine similarity |

---

## Prerequisites

- Python 3.11+
- MongoDB running locally or a connection URI (e.g. MongoDB Atlas)
- An OpenAI API key

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/alwaysunderestimated1/ai_chatbot_system.git
cd ai_chatbot_system

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and fill in your values (see below)

# 5. Start the server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## Environment Variables

Copy `.env.example` to `.env` and set the following:

```env
# Required
OPENAI_API_KEY=sk-...

# OpenAI settings
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=          # leave blank for no limit

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=chatbot_db

# JWT Auth
JWT_SECRET=change-this-to-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## API Overview

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a new user account |
| `POST` | `/auth/token` | Login — returns access + refresh tokens |
| `POST` | `/auth/refresh` | Exchange refresh token for a new token pair |
| `GET` | `/auth/me` | Get current authenticated user |

All other endpoints require `Authorization: Bearer <access_token>`.

#### Example: register and login

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "secret123"}'

# Login
curl -X POST http://localhost:8000/auth/token \
  -F "username=alice" -F "password=secret123"
```

---

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat/` | Send a message, get a full response |
| `POST` | `/chat/stream` | Send a message, get a streaming response (SSE) |
| `GET` | `/chat/history/{session_id}` | Retrieve message history for a session |

#### Request body

```json
{
  "session_id": "my-session-abc",
  "message": "What is the capital of France?",
  "system_prompt": "You are a helpful assistant.",
  "temperature": 0.7,
  "max_tokens": null,
  "use_rag": false,
  "use_tools": false
}
```

Set `use_rag: true` to inject relevant knowledge base context.  
Set `use_tools: true` to enable function calling (datetime, calculator, knowledge base search).

---

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/sessions/` | List all sessions (paginated, scoped to current user) |
| `GET` | `/sessions/{session_id}` | Get session metadata |
| `PATCH` | `/sessions/{session_id}` | Rename title or update system prompt |
| `DELETE` | `/sessions/{session_id}` | Delete a session |

---

### Documents (RAG)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/` | Ingest a document (chunk + embed + store) |
| `GET` | `/documents/` | List all documents |
| `POST` | `/documents/search` | Search the knowledge base by query |
| `DELETE` | `/documents/{doc_id}` | Delete a document and its chunks |

#### Ingest a document

```json
{
  "filename": "faq.txt",
  "content": "Q: What are your hours? A: We are open 9am–5pm Monday to Friday...",
  "chunk_size": 500
}
```

---

## Project Structure

```
app/
├── main.py                  # FastAPI app, lifespan, middleware
├── config.py                # Settings loaded from .env
├── limiter.py               # slowapi rate limiter instance
├── database/
│   └── mongodb.py           # Motor async client
├── middleware/
│   └── validation.py        # Message validation, per-user rate limiting
├── models/
│   ├── chat.py              # Message, Session, ChatRequest/Response models
│   ├── document.py          # Document, Chunk, SearchResult models
│   └── user.py              # User, Token models
├── routes/
│   ├── auth.py              # Register, login, refresh, me
│   ├── chat.py              # Chat and streaming endpoints
│   ├── sessions.py          # Session CRUD
│   └── documents.py         # Document ingestion and search
└── services/
    ├── auth_service.py      # JWT creation/validation, password hashing
    ├── chat_service.py      # Orchestrates RAG + tools + persistence
    ├── openai_service.py    # OpenAI API calls, tool-calling loop, streaming
    ├── rag_service.py       # Document chunking, embedding, retrieval
    ├── session_service.py   # Session CRUD and user scoping
    └── tool_service.py      # Tool definitions and safe execution
```

---

## Rate Limits

| Scope | Limit |
|---|---|
| Global (all endpoints) | 100 requests / minute / IP |
| `POST /auth/register` | 10 requests / minute / IP |
| `POST /auth/token` | 10 requests / minute / IP |
| `POST /auth/refresh` | 20 requests / minute / IP |
| Chat messages | 20 messages / minute / user |

---

## License

MIT
