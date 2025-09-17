import os
import json
import pandas as pd
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from dotenv import load_dotenv
import time
from prompts import FEEDBACK_PROMPT, LECTURE_PROMPT

load_dotenv()  # take environment variables from .env file

# ========== CONFIG ==========
openai.api_key = st.secrets["OPENAI_API_KEY"]  # set your API key as env var



# ========== HELPERS ==========

def call_llm(prompt, model="gpt-4o-mini", temperature=0.2, max_tokens=800):
    """Wrapper for OpenAI chat completion"""
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content

def process_feedback(df):
    """Group feedback by instructor/course and summarize"""
    results = []
    total_groups = len(df.groupby(["instructor_id", "course_id"]))
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ((inst, course), g) in enumerate(df.groupby(["instructor_id", "course_id"])):
        status_text.text(f'Analyzing feedback for Instructor {inst}, Course {course}...')
        
        feedback_items = "\n".join("- " + str(x) for x in g["feedback_text"].tolist())
        prompt = FEEDBACK_PROMPT.format(feedback_items=feedback_items[:2000])
        raw = call_llm(prompt)
        try:
            # Clean the response - remove markdown code blocks if present
            cleaned_raw = raw.strip()
            if cleaned_raw.startswith('```json'):
                cleaned_raw = cleaned_raw[7:]  # Remove ```json
            if cleaned_raw.endswith('```'):
                cleaned_raw = cleaned_raw[:-3]  # Remove trailing ```
            cleaned_raw = cleaned_raw.strip()
            
            parsed = json.loads(cleaned_raw)
        except Exception as e:
            st.error(f"Error parsing feedback response: {e}")
            parsed = {"summary": raw}
            
        results.append({
            "instructor_id": inst,
            "course_id": course,
            "summary": parsed.get("summary"),
            "sentiment": parsed.get("sentiment"),
            "actions": parsed.get("actions"),
            "examples": parsed.get("example_quotes")
        })
        
        progress_bar.progress((i + 1) / total_groups)
    
    status_text.text('Analysis complete!')
    time.sleep(1)
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)

def fetch_youtube_transcript(video_id, max_chars=60000):
    """Fetch transcript from YouTube by video ID"""
    transcript_data = YouTubeTranscriptApi().fetch(video_id)
    text = " ".join([seg.text for seg in transcript_data if seg.text.strip()])
    print(len(text), "characters in fetched transcript")
    if len(text) > max_chars:
        text = text[:max_chars] + " ...[truncated]"
    return text

def analyze_transcript(transcript_text):
    """Send transcript to LLM for critique"""
    prompt = LECTURE_PROMPT.format(transcript_text=transcript_text[:5000])
    raw = call_llm(prompt)
    try:
        # Clean the response - remove markdown code blocks if present
        cleaned_raw = raw.strip()
        if cleaned_raw.startswith('```json'):
            cleaned_raw = cleaned_raw[7:]  # Remove ```json
        if cleaned_raw.endswith('```'):
            cleaned_raw = cleaned_raw[:-3]  # Remove trailing ```
        cleaned_raw = cleaned_raw.strip()
        
        parsed = json.loads(cleaned_raw)
    except Exception as e:
        st.error(f"Error parsing LLM response: {e}")
        st.text("Raw response:")
        st.text(raw)
        parsed = {"summary": "Error parsing response", "error": str(e)}
    return parsed

def display_feedback_results(results):
    """Display feedback analysis results in a nice format"""
    for _, row in results.iterrows():
        with st.expander(f"📚 Instructor {row['instructor_id']} - Course {row['course_id']}", expanded=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader("📋 Summary")
                st.write(row['summary'] or "No summary available")
                
                if row['actions']:
                    st.subheader("🎯 Recommended Actions")
                    if isinstance(row['actions'], list):
                        for action in row['actions']:
                            st.write(f"• {action}")
                    else:
                        st.write(row['actions'])
                
                if row['examples']:
                    st.subheader("💬 Example Quotes")
                    if isinstance(row['examples'], list):
                        for quote in row['examples']:
                            st.info(f'"{quote}"')
                    else:
                        st.info(f'"{row["examples"]}"')
            
            with col2:
                sentiment = row['sentiment'] or 'neutral'
                if sentiment.lower() == 'positive':
                    st.success(f"😊 {sentiment.title()}")
                elif sentiment.lower() == 'negative':
                    st.error(f"😟 {sentiment.title()}")
                else:
                    st.info(f"😐 {sentiment.title()}")

def display_lecture_critique(critique):
    """Display lecture critique results in a nice format"""
    st.subheader("📊 Lecture Analysis Results")
    
    # Summary section
    if critique.get('summary'):
        st.subheader("📖 Overall Summary")
        st.write(critique['summary'])
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Clarity & Structure", 
        "❓ Missing Content", 
        "⚠️ Factual Issues", 
        "💡 Teaching Suggestions"
    ])
    
    with tab1:
        if critique.get('clarity_structure'):
            st.write(critique['clarity_structure'])
        else:
            st.write("No clarity and structure analysis available.")
    
    with tab2:
        if critique.get('missing_content'):
            st.write(critique['missing_content'])
        else:
            st.write("No missing content identified.")
    
    with tab3:
        if critique.get('factual_issues'):
            if critique['factual_issues'].strip().lower() not in ['none', 'no issues found', '']:
                st.warning(critique['factual_issues'])
            else:
                st.success("✅ No factual issues identified")
        else:
            st.info("No factual issues analysis available.")
    
    with tab4:
        if critique.get('pedagogical_suggestions'):
            st.write(critique['pedagogical_suggestions'])
        else:
            st.write("No pedagogical suggestions available.")

# ========== STREAMLIT UI ==========

st.set_page_config(
    page_title="AI-Powered Instructor Assistant", 
    layout="wide",
    page_icon="🧑‍🏫"
)

# Custom CSS for better styling
st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 2rem 0;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 2rem;
}
.section-header {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 10px;
    border-left: 4px solid #667eea;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>🧑‍🏫 AI-Powered Instructor Assistant</h1><p>Transform your teaching with AI-driven insights</p></div>', unsafe_allow_html=True)

# ---- SECTION 1: Feedback Analysis ----
st.markdown('<div class="section-header"><h2>📊 Student Feedback Analysis</h2></div>', unsafe_allow_html=True)

st.markdown("""
Upload a CSV file containing student feedback data. The file should have columns:
- `instructor_id`: Instructor identifier
- `course_id`: Course identifier  
- `feedback_text`: Student feedback comments
""")

feedback_file = st.file_uploader("📁 Upload Feedback CSV", type=["csv"])

if feedback_file is not None:
    try:
        df = pd.read_csv(feedback_file)
        
        st.success(f"✅ Successfully loaded {len(df)} feedback entries")
        
        with st.expander("📋 Preview Data", expanded=False):
            st.dataframe(df.head())
            st.write(f"**Columns:** {', '.join(df.columns.tolist())}")
            st.write(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
        
        if st.button("🚀 Analyze Feedback", type="primary"):
            with st.spinner('🤖 AI is analyzing your feedback data...'):
                results = process_feedback(df)
            
            st.balloons()
            display_feedback_results(results)
            
            # Download button
            csv_data = results.to_csv(index=False)
            st.download_button(
                "📥 Download Analysis Results",
                csv_data,
                "feedback_analysis.csv",
                "text/csv",
                key='download-feedback'
            )
            
    except Exception as e:
        st.error(f"❌ Error reading CSV file: {str(e)}")

# ---- SECTION 2: Lecture Transcript Critique ----
st.markdown('<div class="section-header"><h2>📖 Lecture Transcript Critique</h2></div>', unsafe_allow_html=True)

# Initialize session state for transcript
if 'transcript_text' not in st.session_state:
    st.session_state.transcript_text = None

option = st.radio(
    "Choose your input method:",
    ["📄 Upload Transcript (.txt)", "🎥 YouTube Video ID"],
    horizontal=True
)

if option == "📄 Upload Transcript (.txt)":
    txt_file = st.file_uploader("📁 Upload transcript text file", type=["txt"])
    if txt_file is not None:
        st.session_state.transcript_text = txt_file.read().decode("utf-8")
        st.success(f"✅ Transcript loaded ({len(st.session_state.transcript_text)} characters)")
        
        with st.expander("👀 Preview Transcript", expanded=True):
            st.text_area("Transcript Preview", st.session_state.transcript_text+ "...", height=200)
# if option == "📄 Upload Transcript (.txt)":
#     txt_file = st.file_uploader("📁 Upload transcript text file", type=["txt"])
#     if txt_file is not None:
#         st.session_state.transcript_text = txt_file.read().decode("utf-8")
#         st.success(f"✅ Transcript loaded ({len(st.session_state.transcript_text)} characters)")
        
#         with st.expander("👀 Preview Transcript", expanded=True):
#             st.text_area(
#                 "Transcript Preview",
#                 st.session_state.transcript_text,  # ✅ full text without "..."
#                 height=400  # you can adjust height to fit better
#             )


elif option == "🎥 YouTube Video ID":
    st.info("💡 For a YouTube URL like `https://www.youtube.com/watch?v=12345`, the video ID is `12345`")
    video_id = st.text_input("🎬 Enter YouTube Video ID")
    
    if video_id:
        if st.button("📥 Fetch Transcript"):
            try:
                with st.spinner('🎥 Fetching transcript from YouTube...'):
                    st.session_state.transcript_text = fetch_youtube_transcript(video_id)
                
                st.success("✅ Transcript successfully fetched!")
                st.rerun()  # Refresh the app to show the preview and analyze button
                    
            except Exception as e:
                st.error(f"❌ Error fetching transcript: {str(e)}")
                st.info("💡 Make sure the video ID is correct and the video has captions available.")
    
    # Show preview if transcript is fetched
    if st.session_state.transcript_text:
        with st.expander("👀 Preview Transcript", expanded=True):
            st.text_area("Transcript Preview", st.session_state.transcript_text, height=400)

# Critique button (only show if we have transcript)
if st.session_state.transcript_text:
    if st.button("🎯 Analyze Lecture", type="primary"):
        with st.spinner('🤖 AI is analyzing your lecture transcript...'):
            critique = analyze_transcript(st.session_state.transcript_text)
        
        st.balloons()
        display_lecture_critique(critique)
        
        # Download button
        json_data = json.dumps(critique, indent=2)
        st.download_button(
            "📥 Download Critique Report",
            json_data,
            "lecture_critique.json",
            "application/json",
            key='download-critique'
        )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>🚀 Powered by AI • Built with Streamlit</p>
    <p><small>Transform your teaching experience with intelligent feedback analysis and lecture critiques</small></p>
</div>

""", unsafe_allow_html=True)
