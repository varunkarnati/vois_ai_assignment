# 🧾 Gourmet Grove – AI Restaurant Voice Assistant

This is an AI-powered conversational ordering system for a restaurant, where users interact via voice. Built using **FastAPI**, **LangChain**, **Groq LLM**, and **WebSockets**, the assistant allows users to:

- 🎙️ Talk naturally to place or modify their order
- 📋 View order summary updated in real-time
- 🗃️ Store all orders in a local JSON file (`orders_db.json`) as a simple database

---

## 🧰 Tech Stack

- **FastAPI** – for API & WebSocket backend
- **LangChain + Groq** – for LLM-driven dialogue + tool use
- **ElevenLabs** – for text-to-speech (TTS)
- **WebSockets** – for real-time streaming
- **Vanilla JS + HTML/CSS** – frontend interface
- **`orders_db.json`** – acts as a local order database

---

## 📦 Project Structure

```
├── app/
│   └── utils/
│       ├── tools.py          # All assistant tools with persistent order store
│       ├── llm.py            # LLM logic + LangChain tool orchestration
│       └── stt.py, tts.py    # (Speech-to-text / text-to-speech)
├── main.py                   # FastAPI app with WebSocket support
├── public/
│   └── index.html            # Restaurant-themed voice assistant UI
├── orders_db.json            # JSON file acting as persistent order DB
└── README.md
```

---

## 🚀 How to Run Locally

### 1. 🛠️ Install Dependencies

```bash
pip install -r requirements.txt
```

Make sure to include:

```txt
fastapi
uvicorn
langchain
langchain_groq
python-dotenv
pydub
soundfile
elevenlabs
```

### 2. 🔑 Set Environment Variables

Create a `.env` file:

```
GROQ_API_KEY=your_groq_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
```

---

### 3. ▶️ Start the Server

```bash
uvicorn main:app --reload
```

Open your browser to:  
📍 http://localhost:8000

---

## 🌐 Deployment

To deploy on **Render**, make sure:

- Your `index.html` is inside `/public`
- Your `main.py` mounts that directory:
  ```python
  app.mount("/", StaticFiles(directory=Path(__file__).parent / "public", html=True), name="static")
  ```
- WebSocket URL in `index.html` is environment-aware:

```js
const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
const wsUrl = `${protocol}://${location.host}/ws/converse`;
```

---

## 🧠 Supported Commands

Try speaking:

- "I want two cheeseburgers and a Coke"
- "Remove one Coke"
- "What are today’s specials?"
- "Clear my order"
- "How much is the total?"

---

## 🗃️ Orders are Stored in

> `orders_db.json`

Each order ID stores:

```json
{
  "abc1": {
    "items": ["2 x Cheeseburger", "1 x Soda"],
    "total": 21.97
  }
}
```

---

## 📌 Features To Improve

- Replace JSON with Redis or PostgreSQL
- Add login or session persistence
- Deploy on Hugging Face Spaces or Fly.io

---

## 👨‍🍳 Made with ❤️ for restaurants using AI