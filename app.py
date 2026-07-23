import os
import streamlit as st
import fitz  # PyMuPDF
from dotenv import load_dotenv
from google import genai
import chromadb
from chromadb.utils import embedding_functions
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Import your custom backend authentication helpers
from auth_utils import hash_password, verify_password, generate_otp, send_otp_email
from datetime import datetime, timedelta, timezone

# 1. Page Configuration
st.set_page_config(page_title="Project Veda v1.2", page_icon="🎓", layout="wide")

# Load environment variables for Supabase and Gemini
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase = None
if url and key:
    from supabase import create_client, Client
    supabase: Client = create_client(url, key)

# Initialize Session State for Authentication & Performance Tracking
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "signup_stage" not in st.session_state:
    st.session_state.signup_stage = "enter_details"
if "sync_status" not in st.session_state:
    st.session_state.sync_status = {}
if "show_upload_success" not in st.session_state:
    st.session_state.show_upload_success = False
if "uploader_key_counter" not in st.session_state:
    st.session_state.uploader_key_counter = 0

# ==========================================
# 🔐 AUTHENTICATION GATEWAY
# ==========================================
if not st.session_state.authenticated:
    st.title("🎓 Welcome to Project Veda")
    st.markdown("Please log in or create an account to access your workspace.")
    
    tab1, tab2 = st.tabs(["Log In", "Sign Up"])
    
    with tab1:
        st.subheader("Welcome Back")
        log_email = st.text_input("Email Address", key="l_email")
        log_pass = st.text_input("Password", type="password", key="l_pass")
        
        if st.button("Log In"):
            if log_email and log_pass:
                if not supabase:
                    st.error("❌ Supabase client is not initialized. Check your .env file.")
                else:
                    with st.spinner("Authenticating..."):
                        try:
                            res = supabase.table("custom_users").select("*").eq("email", log_email).execute()
                            if res.data and len(res.data) > 0:
                                user_record = res.data[0]
                                stored_hash = user_record["password_hash"]
                                
                                if verify_password(log_pass, stored_hash):
                                    # CLEAR PREVIOUS SESSION STATE CACHE
                                    for key in list(st.session_state.keys()):
                                        del st.session_state[key]
                                        
                                    st.session_state.authenticated = True
                                    st.session_state.user_email = log_email
                                    st.success("✅ Login successful!")
                                    st.rerun()
                                else:
                                    st.error("❌ Incorrect password.")
                            else:
                                st.error("❌ No account found with this email.")
                        except Exception as e:
                            st.error(f"❌ Login error: {e}")
            else:
                st.warning("Please fill in all fields.")

    with tab2:
        st.subheader("Create a New Account")
        
        if st.session_state.signup_stage == "enter_details":
            reg_email = st.text_input("Email Address", key="r_email")
            reg_pass = st.text_input("Create Password (min 6 chars)", type="password", key="r_pass")
            
            if st.button("Send Verification Code"):
                if reg_email and len(reg_pass) >= 6:
                    if not supabase:
                        st.error("❌ Supabase client is not initialized.")
                    else:
                        with st.spinner("Checking availability & sending OTP..."):
                            existing = supabase.table("custom_users").select("email").eq("email", reg_email).execute()
                            if existing.data:
                                st.error("❌ An account with this email already exists. Please log in.")
                            else:
                                otp = generate_otp()
                                expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
                                
                                supabase.table("otp_requests").insert({
                                    "email": reg_email,
                                    "otp_code": otp,
                                    "expires_at": expires_at.isoformat()
                                }).execute()
                                
                                success = send_otp_email(reg_email, otp)
                                if success:
                                    st.session_state.temp_email = reg_email
                                    st.session_state.temp_password = reg_pass
                                    st.session_state.signup_stage = "verify_otp"
                                    st.success("✅ Verification code sent to your email!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to send email. Check your SMTP settings in auth_utils.py.")
                else:
                    st.warning("Please enter a valid email and a password of at least 6 characters.")
                    
        elif st.session_state.signup_stage == "verify_otp":
            st.info(f"We sent a code to **{st.session_state.temp_email}**.")
            entered_otp = st.text_input("Enter 6-digit OTP", max_chars=6)
            
            if st.button("Verify & Complete Registration"):
                with st.spinner("Verifying code..."):
                    otp_res = supabase.table("otp_requests").select("*").eq("email", st.session_state.temp_email).eq("otp_code", entered_otp).execute()
                    
                    if otp_res.data:
                        record = otp_res.data[0]
                        expiry_time = datetime.fromisoformat(record["expires_at"])
                        
                        if datetime.now(timezone.utc) < expiry_time:
                            hashed_pw = hash_password(st.session_state.temp_password)
                            
                            supabase.table("custom_users").insert({
                                "email": st.session_state.temp_email,
                                "password_hash": hashed_pw
                            }).execute()
                            
                            supabase.table("otp_requests").delete().eq("email", st.session_state.temp_email).execute()
                            
                            st.success("🎉 Account successfully created! Please switch to the 'Log In' tab.")
                            st.session_state.signup_stage = "enter_details"
                        else:
                            st.error("❌ OTP has expired. Please start over.")
                    else:
                        st.error("❌ Invalid OTP code.")
                        
            if st.button("Cancel / Restart"):
                st.session_state.signup_stage = "enter_details"
                st.rerun()

# ==========================================
# 🎓 MAIN PROJECT VEDA v1.2 WORKSPACE
# ==========================================
else:
    user_email = st.session_state.user_email

    st.title("🎓 Project Veda — AI Teacher v1.2")
    st.caption(f"Logged in as: {user_email} | Cloud PDF Storage Enabled")

    with st.expander("📖 How to use Project Veda"):
        st.markdown("""
        **Welcome to Project Veda!** 
        
        *Veda is currently your secure, **Private Learning Assistant**. While Veda is not yet a fully tailored learning agent, we are actively on the path toward making Veda a truly Personalized Learning Assistant in future updates!*
        
        **Here is how to begin:**
        *   **📂 1. Create a Subject:** Use the sidebar to create a new workspace. Your knowledge vaults are strictly private to your account.
        *   **📥 2. Offer Texts:** Use the Offer Texts to the Oracle feature in the sidebar to submit your PDFs. The Oracle will memorize them instantly for your session while securely backing them up to the cloud.
        *   **🛠️ 3. Teacher Tools:** Generate practice quizzes or comprehensive study guides from your sacred archives using the sidebar.
        *   **💬 4. Seek Wisdom:** Ask the Oracle questions about your materials. Your chat history is automatically preserved.
        """)

    # Initialize both Gemini clients from environment variables
    # Initialize both Gemini clients from environment variables
    key_1 = os.environ.get("GEMINI_API_KEY_1") or os.environ.get("GEMINI_API_KEY")
    key_2 = os.environ.get("GEMINI_API_KEY_2")
    
    # Force the primary key into the environment so ChromaDB can find it automatically
    if key_1:
        os.environ["GEMINI_API_KEY"] = key_1

    client_primary = genai.Client(api_key=key_1) if key_1 else None
    client_secondary = genai.Client(api_key=key_2) if key_2 else None

    def generate_with_failover(prompt, model="gemini-2.5-flash"):
        """Attempts generation with primary key, failing over to secondary if quota is reached."""
        clients = []
        if client_primary:
            clients.append(("Primary", client_primary))
        if client_secondary:
            clients.append(("Secondary", client_secondary))

        if not clients:
            return "❌ **Configuration Error:** No Gemini API keys found. Please check your `.env` file."

        for label, client_obj in clients:
            try:
                response = client_obj.models.generate_content(model=model, contents=prompt)
                return response.text
            except Exception as e:
                err_str = str(e).lower()
                # Detect standard Quota/Rate Limit errors (HTTP 429, Resource Exhausted, Quota)
                is_quota_error = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str
                
                if is_quota_error:
                    print(f"⚠️ {label} Gemini API Key hit quota limit. Attempting failover...")
                    continue  # Try the next configured key
                else:
                    # Non-quota related error (e.g., network issue, bad prompt)
                    return f"❌ **Oracle Error:** {e}"

        # If loop finishes without returning, all available keys have been exhausted
        return "⚠️ **The Oracle is temporarily resting:** All configured Gemini API keys have reached their quota limits for today. Please try again later or add new API keys."

    @st.cache_resource
    def get_chroma_collection():
        chroma_client = chromadb.PersistentClient(path="./veda_memory")
        gemini_ef = embedding_functions.GoogleGenaiEmbeddingFunction(
            model_name="gemini-embedding-001"
        )
        return chroma_client.get_or_create_collection(
            name="class_materials", 
            embedding_function=gemini_ef
        )

    collection = get_chroma_collection()

    # --- USER-SPECIFIC CORE FUNCTIONS ---
    def get_database_inventory():
        data = collection.get(where={"user_email": user_email}, include=["metadatas"])
        inventory = {}
        if data and data["metadatas"]:
            for meta in data["metadatas"]:
                sub = meta.get("subject", "Uncategorized")
                src = meta.get("source", "Unknown")
                if sub not in inventory:
                    inventory[sub] = set()
                inventory[sub].add(src)
        return inventory

    def background_upload_worker(file_bytes, file_path, file_name):
        try:
            # Upload to Supabase silently
            supabase.storage.from_("veda_pdfs").upload(
                file=file_bytes,
                path=file_path,
                file_options={"content-type": "application/pdf"}
            )
            # Update session state to success
            st.session_state.sync_status[file_name] = "success"
        except Exception as e:
            print(f"Background upload error for {file_name}: {e}")
            st.session_state.sync_status[file_name] = "failed"
    
    def process_pdf(file_bytes, file_name, subject_name):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
            
        chunk_size = 1000
        overlap = 200
        chunks = []
        start = 0
        while start < len(full_text):
            end = start + chunk_size
            chunks.append(full_text[start:end])
            start += (chunk_size - overlap)
            
        ids = [f"{user_email}_{subject_name}_{file_name}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": file_name, "subject": subject_name, "user_email": user_email} for _ in range(len(chunks))]
        
        collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)

    def delete_file(filename, subject_name):
        # 1. Delete from ChromaDB
        collection.delete(where={"$and": [{"source": filename}, {"user_email": user_email}, {"subject": subject_name}]})
        # 2. Delete from Supabase Storage
        file_path = f"{user_email}/{subject_name}/{filename}"
        try:
            supabase.storage.from_("veda_pdfs").remove([file_path])
        except Exception as e:
            print(f"Failed to delete from storage: {e}")

    def delete_workspace(subject_name):
        # 1. Delete all vector chunks from ChromaDB for this user and subject
        try:
            collection.delete(where={"$and": [{"subject": subject_name}, {"user_email": user_email}]})
        except Exception as e:
            print(f"Error deleting ChromaDB records for workspace: {e}")

        # 2. Delete chat history records from Supabase
        try:
            supabase.table("chat_history").delete().eq("email", user_email).eq("subject", subject_name).execute()
        except Exception as e:
            print(f"Error deleting chat history for workspace: {e}")

        # 3. Delete physical PDF files from Supabase Storage folder
        try:
            folder_path = f"{user_email}/{subject_name}"
            files_res = supabase.storage.from_("veda_pdfs").list(folder_path)
            if files_res:
                file_paths = [f"{folder_path}/{file['name']}" for file in files_res]
                supabase.storage.from_("veda_pdfs").remove(file_paths)
        except Exception as e:
            print(f"Error deleting storage files for workspace: {e}")

        # 4. Clear active subject session state
        st.session_state.active_subject = None
        st.session_state.current_subject = None
        if "messages" in st.session_state:
            del st.session_state.messages

    def get_pdf_download_link(filename, subject_name):
        file_path = f"{user_email}/{subject_name}/{filename}"
        try:
            res = supabase.storage.from_("veda_pdfs").create_signed_url(file_path, 60)
            if isinstance(res, dict):
                return res.get('signedURL', None)
            elif isinstance(res, str):
                return res
            return None
        except Exception as e:
            st.sidebar.error(f"URL Error: {e}") 
            return None
        
    def get_subject_text(subject_name):
        data = collection.get(where={"$and": [{"subject": subject_name}, {"user_email": user_email}]}, include=["documents"])
        if not data or not data["documents"]:
            return ""
        return "\n".join(data["documents"])

    def ask_veda(question, subject_name):
        results = collection.query(
            query_texts=[question], 
            n_results=4,
            where={"$and": [{"subject": subject_name}, {"user_email": user_email}]} 
        )
        
        if not results['documents'][0]:
            return f"I don't have any notes on '{subject_name}' in your personal records to answer this yet."
            
        context = "\n---\n".join(results['documents'][0])
        
        prompt = f"""
        You are Project Veda, an expert AI Teacher. 
        Answer the student's question using ONLY the provided textbook context below. 
        If the answer cannot be found, say: "I couldn't find that in your uploaded notes."

        Context ({subject_name}):
        {context}

        Question: {question}
        """
        # --- FAILOVER APPLIED HERE ---
        return generate_with_failover(prompt)

    def generate_teacher_tool(tool_type, subject_name):
        all_text = get_subject_text(subject_name)
        if tool_type == "quiz":
            prompt = f"Based on the core concepts in these notes, generate a 5-question multiple-choice quiz. Provide options A, B, C, D, and an Answer Key at the bottom.\n\nNotes:\n{all_text[:30000]}"
        else:
            prompt = f"Provide a comprehensive study guide for this material. Include a Main Theme, Core Concepts, Key Vocabulary, and Critical Takeaways.\n\nNotes:\n{all_text[:30000]}"
            
        # --- FAILOVER APPLIED HERE ---
        return generate_with_failover(prompt)

    # --- SUPABASE CHAT HISTORY FUNCTIONS ---
    def load_chat_history(subject_name):
        if not subject_name or not user_email or not supabase:
            return []
        try:
            res = supabase.table("chat_history") \
                .select("role, content") \
                .eq("email", user_email) \
                .eq("subject", subject_name) \
                .order("created_at", desc=False) \
                .execute()
            return res.data if res.data else []
        except Exception as e:
            print(f"Error loading chat history: {e}")
            return []

    def save_chat_message(subject_name, role, content):
        if not subject_name or not user_email or not supabase:
            return
        try:
            supabase.table("chat_history").insert({
                "email": user_email,
                "subject": subject_name,
                "role": role,
                "content": content
            }).execute()
        except Exception as e:
            print(f"Error saving chat history: {e}")

    # ==========================================
    # 3. SIDEBAR UI & STATE CALLBACKS
    # ==========================================
    inventory = get_database_inventory()
    all_subjects = list(inventory.keys())

    # Initialize active subject in session state if not present
    if "active_subject" not in st.session_state:
        st.session_state.active_subject = all_subjects[0] if all_subjects else None

    # --- CALLBACK FUNCTIONS FOR PERFORMANCE ---
    def switch_workspace(selected_subject):
        st.session_state.active_subject = selected_subject

    def feed_notes_callback(subject):
        # Construct the dynamic key
        uploader_key = f"uploader_{subject}_{st.session_state.uploader_key_counter}"
        uploaded_files = st.session_state.get(uploader_key)
        
        if uploaded_files:
            current_inventory = get_database_inventory()
            known_files = current_inventory.get(subject, set())
            new_knowledge = False
            
            for file in uploaded_files:
                if file.name not in known_files:
                    file_bytes = file.read()
                    file_path = f"{st.session_state.user_email}/{subject}/{file.name}"
                    
                    # 1. IMMEDIATE LOCAL PROCESS (ChromaDB)
                    process_pdf(file_bytes, file.name, subject)
                    
                    # 2. MARK AS SYNCING
                    st.session_state.sync_status[file.name] = "syncing"
                    
                    # 3. FIRE BACKGROUND THREAD (Supabase)
                    t = threading.Thread(target=background_upload_worker, args=(file_bytes, file_path, file.name))
                    add_script_run_ctx(t)
                    t.start()
                    
                    new_knowledge = True
            
            if new_knowledge:
                st.session_state.show_upload_success = True
                
            # Increment the counter to completely clear the uploader box!
            st.session_state.uploader_key_counter += 1

    def delete_file_callback(filename, subject):
        delete_file(filename, subject)
        if filename in st.session_state.sync_status:
            del st.session_state.sync_status[filename]

    with st.sidebar:
        if st.button("🚪 Log Out", use_container_width=True):
            # WIPE ENTIRE SESSION STATE ON LOGOUT
            for key in list(st.session_state.keys()):
                del st.session_state[key]
                
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.rerun()
            
        st.divider()
        
        # New Workspace Creation (Optimized with callback)
        new_subject_input = st.text_input("➕ Create New Subject Workspace:", placeholder="e.g., Physics 101")
        if st.button("Create Workspace", use_container_width=True, on_click=switch_workspace, args=(new_subject_input,)):
            pass 

        st.divider()
        st.header("💬 Your Workspaces")
        
        # ChatGPT-style Sidebar List
        if not all_subjects:
            st.caption("No workspaces yet. Create one above!")
        else:
            for subject in all_subjects:
                # Highlight the active subject button
                is_active = (st.session_state.active_subject == subject)
                btn_type = "primary" if is_active else "secondary"
                
                col_sub, col_del = st.columns([4, 1])
                
                with col_sub:
                    st.button(
                        f"📚 {subject}", 
                        key=f"nav_{subject}", 
                        use_container_width=True, 
                        type=btn_type,
                        on_click=switch_workspace,
                        args=(subject,)
                    )
                        
                with col_del:
                    if st.button("🗑️", key=f"del_ws_{subject}", help=f"Delete workspace '{subject}'"):
                        delete_workspace(subject)
                        st.success(f"Deleted '{subject}' workspace.")
                        import time
                        time.sleep(1)
                        st.rerun()

        active_subject = st.session_state.active_subject
        
        # Only show file management and tools IF a workspace is active
        if active_subject:
            st.divider()
            # The form batches interactions and prevents drag-and-drop reruns
            with st.form(key=f"upload_form_{active_subject}", clear_on_submit=True):
                    uploaded_files = st.file_uploader("Offer Texts to the Oracle", type=["pdf"], accept_multiple_files=True)
                    submit_clicked = st.form_submit_button("Feed Notes to Oracle", use_container_width=True)
                    
                    if submit_clicked and uploaded_files:
                        current_inventory = get_database_inventory()
                        known_files = current_inventory.get(active_subject, set())
                        new_knowledge = False
                        
                        # 🔮 PERSONA: Local Processing
                        with st.spinner("🔮 Oracle is carefully reading and memorizing your ancient texts..."):
                            for file in uploaded_files:
                                if file.name in known_files:
                                    st.warning(f"👁️ The Oracle already knows of '{file.name}'.", icon="⚠️")
                                else:
                                    file_bytes = file.read()
                                    file_path = f"{st.session_state.user_email}/{active_subject}/{file.name}"
                                    
                                    # 1. IMMEDIATE LOCAL PROCESS (ChromaDB)
                                    process_pdf(file_bytes, file.name, active_subject)
                                    
                                    # 2. MARK AS SYNCING
                                    st.session_state.sync_status[file.name] = "syncing"
                                    
                                    # 3. FIRE BACKGROUND THREAD (Supabase)
                                    t = threading.Thread(target=background_upload_worker, args=(file_bytes, file_path, file.name))
                                    add_script_run_ctx(t)
                                    t.start()
                                    
                                    new_knowledge = True
                                    
                        if new_knowledge:
                            # 🔮 PERSONA: Ready State
                            st.success("✨ The Oracle has mastered the texts! You may now seek its wisdom.")
                            import time
                            time.sleep(1)
                            st.rerun() # <--- FORCE IMMEDIATE UI UPDATE
                
                # --- DYNAMIC UI RENDERING ---
            st.caption("Sacred Archives:")
            if active_subject in inventory:
                    for file_name in inventory[active_subject]:
                        col1, col2, col3 = st.columns([5, 2, 1])
                        
                        status = st.session_state.sync_status.get(file_name, "success")
                        
                        if status == "syncing":
                            # 🔮 PERSONA: Cloud Syncing
                            col1.caption(f"📜 {file_name} \n*(🔮 Oracle is transcribing to the cloud vault...)*")
                            col2.caption("Scribing...")
                        elif status == "failed":
                            # 🔮 PERSONA: Cloud Failed
                            col1.caption(f"📜 {file_name} \n*(⚠️ Oracle's cloud connection faltered)*")
                            col2.caption("Mortal Memory")
                        else:
                            # 🔮 PERSONA: Cloud Success
                            col1.caption(f"📜 {file_name} \n*(✨ Safely secured in the Vault)*")
                            
                            download_url = get_pdf_download_link(file_name, active_subject)
                            if download_url:
                                col2.markdown(f"[📥 DL]({download_url})")
                            else:
                                col2.caption("Seal Broken")
                            
                        col3.button("X", key=f"del_{active_subject}_{file_name}", on_click=delete_file_callback, args=(file_name, active_subject))
            else:
                    st.caption("No texts offered yet.")
                    
            with st.expander(f"🛠️ Teacher Tools", expanded=False):
                if st.button("📝 Generate Quiz", use_container_width=True, key=f"quiz_btn_{active_subject}"):
                    all_text = get_subject_text(active_subject)
                    if not all_text.strip():
                        st.warning("⚠️ Oracle needs you to feed notes into this workspace first!")
                    else:
                        with st.spinner("🔮 Oracle is crafting your quiz..."):
                            user_msg = f"Can you generate a practice quiz for {active_subject}?"
                            quiz_ans = generate_teacher_tool("quiz", active_subject)
                            
                            save_chat_message(active_subject, "user", user_msg)
                            save_chat_message(active_subject, "assistant", quiz_ans)
                            
                            # Instantly append to active session state so it renders right away
                            st.session_state.messages.append({"role": "user", "content": user_msg})
                            st.session_state.messages.append({"role": "assistant", "content": quiz_ans})
                    
                if st.button("📖 Create Study Guide", use_container_width=True, key=f"guide_btn_{active_subject}"):
                    all_text = get_subject_text(active_subject)
                    if not all_text.strip():
                        st.warning("⚠️ Oracle needs you to feed notes into this workspace first!")
                    else:
                        with st.spinner("🔮 Oracle is writing your study guide..."):
                            user_msg = f"Please generate a summary study guide for {active_subject}."
                            guide_ans = generate_teacher_tool("summary", active_subject)
                            
                            save_chat_message(active_subject, "user", user_msg)
                            save_chat_message(active_subject, "assistant", guide_ans)
                            
                            # Instantly append to active session state so it renders right away
                            st.session_state.messages.append({"role": "user", "content": user_msg})
                            st.session_state.messages.append({"role": "assistant", "content": guide_ans})

    # ==========================================
    # 4. MAIN CHAT INTERFACE & STATE MANAGEMENT
    # ==========================================
    if not active_subject:
        st.info("👈 Please create a workspace in the sidebar to begin.")
    else:
        if "current_subject" not in st.session_state:
            st.session_state.current_subject = None

        if st.session_state.current_subject != active_subject:
            st.session_state.current_subject = active_subject
            st.session_state.messages = load_chat_history(active_subject)

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if user_question := st.chat_input(f"Ask Veda about {active_subject}..."):
            st.session_state.messages.append({"role": "user", "content": user_question})
            with st.chat_message("user"):
                st.markdown(user_question)
            
            save_chat_message(active_subject, "user", user_question)
            
            with st.chat_message("assistant"):
                with st.spinner("📖 Oracle is thinking..."):
                    answer = ask_veda(user_question, active_subject)
                    st.markdown(answer)
            
            st.session_state.messages.append({"role": "assistant", "content": answer})
            save_chat_message(active_subject, "assistant", answer)
            
            st.rerun()