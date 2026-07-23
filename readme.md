# 🎓 Project Veda — AI Teacher v1.2

Project Veda is a personalized, cloud-synced AI teaching assistant. It allows users to create dedicated subject workspaces, upload course materials (PDFs), and interact with an AI "Oracle" that specifically studies and answers questions based on the uploaded notes.

## ✨ Features
* **ChatGPT-Style Workspaces:** Isolated chat threads and vector memory for different subjects.
* **Cloud-Synced PDFs:** Secure file storage using Supabase Storage Buckets.
* **Smart AI Memory:** Local text vectorization using ChromaDB to ensure the Oracle only references your specific course materials.
* **Custom Authentication:** Secure user login and OTP email verification.
* **Teacher Tools:** One-click generation of multiple-choice quizzes and comprehensive study guides.

## 🛠️ Tech Stack
* **Frontend:** Streamlit
* **AI Model:** Google Gemini (2.5 Flash)
* **Vector Database:** ChromaDB
* **Cloud Database & Storage:** Supabase (PostgreSQL & Storage Buckets)
* **Document Parsing:** PyMuPDF (fitz)

## 🚀 How to Run Locally

**1. Clone the repository**
```bash
git clone [https://github.com/abhij5681-eng/project-veda.git](https://github.com/abhij5681-eng/project-veda.git)
cd project-veda-v1.2

```

**2. Install dependencies**

```bash
pip install -r requirements.txt

```

**3. Set up Environment Variables**
Create a `.env` file in the root directory and add your API keys:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
GEMINI_API_KEY=your_google_gemini_key

```

**4. Run the application**

```bash
streamlit run app.py


