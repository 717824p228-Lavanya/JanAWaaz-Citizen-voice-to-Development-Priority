JanAwaaz

JanAwaaz ("Voice of the People") is a citizen complaint reporting platform. Citizens submit civic issues (roads, water, electricity, health, education) in their own language, and the system automatically classifies the issue and estimates urgency using a rule-based AI classifier. Officials get a dashboard to view all submissions, see hotspots on a map, and rank issues by priority for resolution.

Features


Citizen submission form — report an issue via text, photo, or voice note
Live AI classification — automatically detects category (Roads/Water/Electricity/Health/Education), language (English/Hindi/Tamil), and urgency score as you type
Shared submissions feed — every citizen's report is visible to everyone, not just the person who submitted it
Upvoting — citizens can flag "I have this issue too" to show demand
Official dashboard — view all submissions, hotspots, and a priority ledger for decision-making


Tech stack


Backend: Python, FastAPI, SQLite
Frontend: HTML, CSS, JavaScript (no framework — single index.html file)


Project structure

├── main.py          # FastAPI backend (API + database)
├── index.html        # Frontend (citizen form + official dashboard)
└── janawaaz.db        # SQLite database (auto-created on first run)

Setup & running locally

1. Install Python (3.10 or later) if you don't already have it.

2. Install dependencies:

bashpip install fastapi uvicorn

3. Run the backend server:

bashuvicorn main:app --port 8000

The API will be live at http://127.0.0.1:8000, with interactive docs at http://127.0.0.1:8000/docs.

4. Open the frontend:

Just open index.html in your browser. It talks to the backend automatically.

Running for a shared demo (multiple devices on the same WiFi)

By default, only your own laptop can see the app. To let other devices (like teammates or judges) view it on the same WiFi:

1. Find your laptop's WiFi IP address:

bashipconfig

Look for the IPv4 Address under your WiFi adapter (e.g. 10.212.81.67).

2. Start the server so it accepts outside connections:

bashpython -m uvicorn main:app --host 0.0.0.0 --port 8000

3. In index.html, update the API_BASE constant near the top of the <script> section to your IP:

jsconst API_BASE = 'http://10.212.81.67:8000';

4. Share the updated index.html with everyone on the same WiFi — they can open it directly in their browser without installing anything.

API endpoints

MethodEndpointDescriptionPOST/classifyClassify text (category, language, urgency) without savingGET/submissionsList all submissionsPOST/submissionsCreate a new submissionPOST/submissions/{id}/upvoteUpvote a submissionGET/submissions/{id}/commentsList comments on a submissionPOST/submissions/{id}/commentsAdd a commentGET/hotspotsGet geographic clusters of submissionsGET/ledgerGet priority ranking of issues by category

Team TECH STRIKERS

Add team member names here. NITHYASRI G, LAVANYA B

Hackathon 
 
Add hackathon name / track here if applicable. Build with AI - code for communities
