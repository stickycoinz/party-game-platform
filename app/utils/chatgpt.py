import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Optional

class ChatGPTQuestionGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1/chat/completions"
        
    async def generate_trivia_question(self, category: str, difficulty: str = "medium") -> Dict[str, str]:
        """Generate a single trivia question for the given category."""
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
            
        prompt = f"""Generate a trivia question for the category "{category}" with {difficulty} difficulty.

Requirements:
- The question should be clear and unambiguous
- The answer should be concise (1-4 words when possible)
- The question should be appropriate for a party game
- Make it engaging and fun

Please respond with ONLY a JSON object in this exact format:
{{"question": "Your question here?", "answer": "Your answer here"}}

Category: {category}
Difficulty: {difficulty}"""

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a trivia question generator. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.8
                }
                
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        
                        # Try to parse the JSON response
                        try:
                            question_data = json.loads(content)
                            if "question" in question_data and "answer" in question_data:
                                return {
                                    "question": question_data["question"],
                                    "answer": question_data["answer"],
                                    "source": "AI-generated"
                                }
                        except json.JSONDecodeError:
                            print(f"Failed to parse ChatGPT response: {content}")
                            
                    else:
                        print(f"ChatGPT API error: {response.status}")
                        
        except Exception as e:
            print(f"Error generating question: {e}")
            
        # Fallback to None if generation fails
        return None
    
    async def generate_multiple_questions(self, category: str, count: int = 5, difficulty: str = "medium") -> List[Dict[str, str]]:
        """Generate multiple trivia questions for the given category."""
        questions = []
        
        # Generate questions concurrently
        tasks = [self.generate_trivia_question(category, difficulty) for _ in range(count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict) and result is not None:
                questions.append(result)
                
        return questions

# Global instance
chatgpt_generator = ChatGPTQuestionGenerator()

async def get_ai_question(category: str, difficulty: str = "medium") -> Optional[Dict[str, str]]:
    """Convenience function to get a single AI-generated question."""
    return await chatgpt_generator.generate_trivia_question(category, difficulty)
