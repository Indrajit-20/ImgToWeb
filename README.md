# ImgToWeb
it make ui form the images that are good formated 

## Project Structure

```
image-to-web/
├── backend/
│   ├── main.py            ← FastAPI app (your Render backend)
│   ├── requirements.txt
│   ├── render.yaml        ← One-click Render deploy config
│   └── .env.example       ← Copy to .env for local dev
└── frontend/
    ├── index.html         ← Upload UI (deploy to Vercel)
    └── vercel.json
```

---

## Step 1 — Get your FREE Gemini API Key

1. Go to → https://aistudio.google.com/app/apikey
2. Sign in with Google → click **Create API Key**
3. Copy the key (starts with `AIza...`)

Free tier: **15 requests/minute**, 1,500/day — plenty for a student project.

---

## Step 2 — Deploy the Backend to Render (Free)

1. Push the `backend/` folder to a GitHub repo
2. Go to → https://render.com → **New → Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
5. Under **Environment Variables**, add:
   - Key: `GEMINI_API_KEY`
   - Value: your key from Step 1
6. Click **Deploy** → wait ~2 minutes
7. Copy your URL: `https://your-app-name.onrender.com`

---

## Step 3 — Deploy the Frontend to Vercel (Free)

1. Push the `frontend/` folder to GitHub (can be same repo)
2. Go to → https://vercel.com → **New Project** → import repo
3. Set **Root Directory** to `frontend`
4. Click **Deploy**

---

## Step 4 — Use It!

1. Open your Vercel URL
2. Paste your Render backend URL in the "Backend URL" field
3. Upload a screenshot or wireframe
4. Click **Generate Site** → get HTML in seconds!

---

## Local Development

```bash
cd backend
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then open `frontend/index.html` in your browser and use `http://localhost:8000` as the backend URL.

---

## Tech Stack

| Layer | Tool | Cost |
|---|---|---|
| Image optimization | Pillow | Free |
| Backend | FastAPI + Uvicorn | Free |
| Backend hosting | Render | Free |
| AI generation | Gemini 2.5 Flash | Free (15 req/min) |
| Frontend hosting | Vercel | Free |

**Total monthly cost: $0**
