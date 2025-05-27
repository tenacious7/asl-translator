from flask import Flask, request, jsonify
import requests
import re
import os
from spellchecker import SpellChecker
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class HuggingFaceSentenceGenerator:
    def __init__(self, api_key="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"):
        self.api_key = api_key
        self.API_URL = "https://api-inference.huggingface.co/models/gpt2-large"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.spell = SpellChecker()
        
    def generate_sentence(self, collected_words, max_length=100, temperature=0.7, top_p=0.95, top_k=50):
        """Generate a coherent sentence from the collected words."""
        if not collected_words:
            return "No words provided."
            
        try:
            # Clean and correct the input words
            cleaned_words = self._clean_input_words(collected_words)
            
            # Create prompt with cleaned words
            prompt = self._create_prompt(cleaned_words)
            
            # Query the model
            response = self._query_model(prompt, max_length, temperature, top_p, top_k)
            
            # Process the generated text
            if isinstance(response, list) and len(response) > 0 and 'generated_text' in response[0]:
                generated_text = response[0]['generated_text']
            elif isinstance(response, dict) and 'generated_text' in response:
                generated_text = response['generated_text']
            else:
                # If response format is unexpected, use fallback
                return self._fallback_sentence(cleaned_words)
                
            # Clean up the sentence
            clean_sentence = self._clean_sentence(generated_text)
            
            # Verify the sentence contains most of the original words
            words_found = sum(1 for word in cleaned_words if word.lower() in clean_sentence.lower())
            if words_found < len(cleaned_words) * 0.7:
                # If less than 70% of words are in the sentence, try with a different prompt
                prompt = self._create_alternative_prompt(cleaned_words)
                response = self._query_model(prompt, max_length, temperature, top_p, top_k)
                
                if isinstance(response, list) and len(response) > 0 and 'generated_text' in response[0]:
                    generated_text = response[0]['generated_text']
                    clean_sentence = self._clean_sentence(generated_text)
                    
                    # If still not good enough, use fallback
                    words_found = sum(1 for word in cleaned_words if word.lower() in clean_sentence.lower())
                    if words_found < len(cleaned_words) * 0.7:
                        return self._fallback_sentence(cleaned_words)
            
            return clean_sentence

        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return self._fallback_sentence(collected_words)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return self._fallback_sentence(collected_words)
    
    def _clean_input_words(self, words):
        """Clean and correct input words using spell checker."""
        cleaned_words = []
        for word in words:
            # Skip empty strings or single characters (except 'a' and 'i')
            if not word or (len(word) == 1 and word.lower() not in ['a', 'i']):
                continue
                
            # Convert to lowercase for spell checking
            word = word.lower()
            
            # Correct spelling if word length is > 2
            if len(word) > 2:
                word = self.spell.correction(word) or word
                
            cleaned_words.append(word)
            
        return cleaned_words
            
    def _create_prompt(self, words):
        """Create an optimized prompt for better sentence generation."""
        words_str = ", ".join(words)
        return f"Generate a natural, grammatically correct, and conversational English sentence using these words: {words_str}. The sentence should be coherent and meaningful. Sentence:"
    
    def _create_alternative_prompt(self, words):
        """Create an alternative prompt for when the first attempt fails."""
        words_str = " ".join(words)
        return f"Rephrase this into a proper English sentence: {words_str}."

    def _query_model(self, prompt, max_length, temperature, top_p, top_k):
        """Query the Hugging Face model with enhanced parameters."""
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_length": max_length,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "do_sample": True,
                "repetition_penalty": 1.2
            },
        }
        response = requests.post(self.API_URL, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def _clean_sentence(self, text):
        """Clean and extract the most relevant sentence from generated text."""
        # Extract the part after our prompt instruction
        prompt_end = text.find("Sentence:")
        if prompt_end != -1:
            text = text[prompt_end + len("Sentence:"):].strip()
        
        # Split into sentences using regex that respects abbreviations
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s', text)
        
        # Filter out empty or very short sentences
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
        
        if not valid_sentences:
            return text.strip().capitalize()
            
        # Get the first valid sentence
        main_sentence = valid_sentences[0].strip()
        
        # Capitalize the first letter
        if main_sentence and len(main_sentence) > 0:
            main_sentence = main_sentence[0].upper() + main_sentence[1:]
            
        # Ensure proper ending punctuation
        if main_sentence and not main_sentence.endswith(('.', '!', '?')):
            main_sentence += '.'
            
        return main_sentence
    
    def _fallback_sentence(self, words):
        """Generate a simple but grammatical sentence when API fails."""
        if not words:
            return ""
            
        # Common sentence structures for different word counts
        if len(words) == 1:
            return f"{words[0].capitalize()}."
        
        if len(words) == 2:
            return f"{words[0].capitalize()} {words[1]}."
        
        if len(words) >= 3:
            # Try to form a more natural sentence with basic subject-verb-object structure
            middle_words = " ".join(words[1:-1])
            return f"{words[0].capitalize()} {middle_words} {words[-1]}."
            
        # Should never reach here, but just in case
        return " ".join(word.capitalize() for word in words) + "."

# Initialize the sentence generator
sentence_generator = HuggingFaceSentenceGenerator()

@app.route('/generate_sentence', methods=['POST'])
def generate_sentence_route():
    try:
        data = request.get_json()
        collected_words = data.get('words', [])

        if not isinstance(collected_words, list) or not all(isinstance(word, str) for word in collected_words):
            return jsonify({"error": "Invalid input. Expected a list of strings."}), 400

        # Generate the sentence
        sentence = sentence_generator.generate_sentence(collected_words)
        
        # Return the result
        return jsonify({"sentence": sentence})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Get port from environment variable or use default 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
