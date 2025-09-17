# ========== PROMPTS ==========
FEEDBACK_PROMPT = """
You are an expert instructor coach. Given the following set of student feedback items for a course, do three things:

1) Write a concise summary (2-3 sentences) capturing the main themes.
2) Tag the overall sentiment as one of: positive, neutral, negative.
3) Give 2–3 concrete, prioritized action recommendations the instructor can implement next week (each 6-12 words).

Return ONLY valid JSON without markdown code blocks. Use these exact keys: summary, sentiment, actions, example_quotes.

Input feedback items:
{feedback_items}
"""

LECTURE_PROMPT = """
You are an expert medical education reviewer and pedagogy coach.

Analyze the following lecture transcript and provide a structured critique covering:
1. **Overall summary** (2–3 sentences).
2. **Clarity & Structure**: strengths and weaknesses in explanation and flow.
3. **Missing Key Content**: concepts or guidelines typically expected but absent.
4. **Possible Factual Mistakes or Outdated Info**: flag cautiously, cite reasoning.
5. **Pedagogical Suggestions**: concrete steps to improve student engagement/learning.

Return ONLY valid JSON without markdown code blocks or backticks. Use these exact keys:
- "summary"
- "clarity_structure"  
- "missing_content"
- "factual_issues"
- "pedagogical_suggestions"

Transcript:
{transcript_text}
"""