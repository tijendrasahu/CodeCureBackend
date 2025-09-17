import os
from openai import OpenAI

# ==============================================================================
#  AI RESPONSE FUNCTION (USING OPENAI - CHATGPT)
# ==============================================================================
def get_ai_response(prompt_text: str, system_instruction: str) -> dict:
    """
    Sends a prompt and a system instruction to the OpenAI API (ChatGPT).
    Returns a dictionary with the response or an error.
    """
    # 1. API key ko .env file se load karta hai
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {"error": "OPENAI_API_KEY is not set in the .env file."}

    try:
        # 2. OpenAI client ko API key ke saath initialize karta hai
        client = OpenAI(api_key=api_key)

        # 3. OpenAI API ko call karta hai
        #    - `system_instruction` -> role: "system" (AI ke liye rules)
        #    - `prompt_text` -> role: "user" (User ka sawaal)
        chat_completion = client.chat.completions.create(
            model="gpt-4o-mini",  # Ek fast aur powerful model
            messages=[
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {
                    "role": "user",
                    "content": prompt_text,
                },
            ],
        )
        
        # 4. AI se mila saaf-suthra jawab waapis bhejta hai
        response_text = chat_completion.choices[0].message.content
        return {"response": response_text}

    except Exception as e:
        # Agar koi error aaye, toh error message bhejta hai
        print(f"OpenAI API call failed: {e}")
        return {"error": f"Failed to get AI response: {e}"}