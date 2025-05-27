import json
import nltk
from nltk.corpus import words, wordnet
from nltk.util import ngrams
import numpy as np

# Download required NLTK data
nltk.download('words')
nltk.download('wordnet')

class ASLWordSuggester:
    def __init__(self, dictionary_path='asl_words.json'):
        self.current_suggestions = []
        self.current_gesture_buffer = []
        self.last_gesture_time = None
        self.gesture_cooldown = 1.5
        self.last_gesture = None
        self.hand_out_required = False
        
        # Load words from JSON file
        self.load_dictionary(dictionary_path)
        
    def load_dictionary(self, file_path):
        """Load and organize words from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Organize words by length
                self.words_by_length = {}
                
                # Process all words from JSON
                all_words = data.get('words', [])
                for word in all_words:
                    word = word.upper()
                    length = len(word)
                    if length not in self.words_by_length:
                        self.words_by_length[length] = []
                    self.words_by_length[length].append(word)
                
        except Exception as e:
            print(f"Error loading dictionary: {e}")
            self.words_by_length = {}
    
    def get_suggestions_from_buffer(self):
        """Get word suggestions prioritizing by length"""
        if not self.current_gesture_buffer:
            return []
            
        gesture_sequence = ''.join(self.current_gesture_buffer)
        sequence_length = len(gesture_sequence)
        suggestions = []
        
        # First, try to find 2-letter words if sequence length is 1 or 2
        if sequence_length <= 2:
            two_letter_matches = self._find_matches(gesture_sequence, 2)
            suggestions.extend(two_letter_matches)
        
        # If we don't have enough suggestions, try current sequence length
        if len(suggestions) < 4:
            current_length_matches = self._find_matches(gesture_sequence, sequence_length)
            suggestions.extend(current_length_matches)
        
        # If still not enough, try one letter longer
        if len(suggestions) < 4:
            longer_matches = self._find_matches(gesture_sequence, sequence_length + 1)
            suggestions.extend(longer_matches)
        
        # Finally, try even longer words if needed
        if len(suggestions) < 4:
            for length in range(sequence_length + 2, 8):  # Up to 7 letters
                if len(suggestions) >= 4:
                    break
                extra_matches = self._find_matches(gesture_sequence, length)
                suggestions.extend(extra_matches)
        
        # Remove duplicates and limit to 4 suggestions
        suggestions = list(dict.fromkeys(suggestions))[:4]
        self.current_suggestions = suggestions
        return suggestions
    
    def _find_matches(self, sequence, target_length):
        """Find words of specific length that match the sequence"""
        matches = []
        if target_length not in self.words_by_length:
            return matches
            
        for word in self.words_by_length[target_length]:
            if self._word_matches_sequence(sequence, word):
                matches.append(word)
        
        return matches
    
    def _word_matches_sequence(self, sequence, word):
        """Check if word matches the gesture sequence"""
        word = word.upper()
        sequence = sequence.upper()
        
        # For single letter, match first letter
        if len(sequence) == 1:
            return word.startswith(sequence)
        
        # For two letters, prioritize exact start matches
        if len(sequence) == 2:
            return word.startswith(sequence)
        
        # For longer sequences, check if letters appear in order
        current_pos = 0
        for char in sequence:
            pos = word.find(char, current_pos)
            if pos == -1:
                return False
            current_pos = pos + 1
        return True

    def get_suggestions(self, sign, num_suggestions=3):
        """Get initial suggestions for a sign"""
        first_letter = sign[0].upper()
        self.current_suggestions = self.dictionary.get(first_letter, [])
        self.current_index = 0
        
        # Get multiple suggestions
        suggestions = []
        for _ in range(min(num_suggestions, len(self.current_suggestions))):
            suggestion = self.get_next_suggestion()
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions

    def get_next_suggestion(self):
        """Get next suggestion in the list"""
        if not self.current_suggestions:
            return None
        
        suggestion = self.current_suggestions[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.current_suggestions)
        return suggestion

    def get_previous_suggestion(self):
        """Get previous suggestion in the list"""
        if not self.current_suggestions:
            return None
        
        self.current_index = (self.current_index - 1 + len(self.current_suggestions)) % len(self.current_suggestions)
        return self.current_suggestions[self.current_index]

    def update_context(self, word):
        """Update context history with new word"""
        self.context_history.append(word)
        if len(self.context_history) > self.max_history:
            self.context_history.pop(0)

    def generate_sentence(self, words):
        """Generate a properly formatted sentence"""
        if not words:
            return ""
            
        sentence = " ".join(words)
        # Capitalize first letter
        sentence = sentence[0].upper() + sentence[1:]
        
        # Add period if not present
        if not sentence.endswith(('.', '?', '!')):
            sentence += '.'
            
        return sentence

    def add_gesture(self, gesture, current_time, hand_detected):
        """Add a gesture with improved sequence handling"""
        if self.hand_out_required and not hand_detected:
            self.hand_out_required = False
            return self.current_suggestions
            
        if self.hand_out_required:
            return self.current_suggestions
            
        if not self.last_gesture_time or (current_time - self.last_gesture_time) > self.gesture_cooldown:
            if gesture != self.last_gesture:
                # Add new gesture to buffer
                self.current_gesture_buffer.append(gesture)
                
                # Keep only the last 5 gestures
                if len(self.current_gesture_buffer) > 5:
                    self.current_gesture_buffer.pop(0)
                    
                self.last_gesture = gesture
                self.last_gesture_time = current_time
                self.hand_out_required = True
                
                # Get suggestions based on new sequence
                return self.get_suggestions_from_buffer()
                
        return self.current_suggestions
        
    def clear_gesture_buffer(self):
        """Clear the current gesture buffer"""
        self.current_gesture_buffer = []
        self.last_gesture = None
        self.last_gesture_time = None
        self.hand_out_required = False
        
    def get_current_sequence(self):
        """Get the current gesture sequence as a formatted string"""
        return ' → '.join(self.current_gesture_buffer) if self.current_gesture_buffer else ""

class WordPredictor:
    def __init__(self):
        self.current_letter = None
        self.current_word = None
        self.selected_words = []
        self.context_words = {}
        
        # Load ASL dictionary and organize by letters
        with open('asl_words.json', 'r') as f:
            words_data = json.load(f)
            self.word_dict = self.organize_words(words_data['words'])
        
        # Initialize basic context pairs
        self.initialize_context_pairs()
    
    def initialize_context_pairs(self):
        """Initialize basic context pairs for common word relationships"""
        self.context_words = {
            'HELLO': ['WORLD', 'THERE', 'FRIEND', 'EVERYONE'],
            'GOOD': ['MORNING', 'AFTERNOON', 'EVENING', 'NIGHT'],
            'HOW': ['ARE', 'YOU', 'ABOUT', 'MANY'],
            'THANK': ['YOU', 'VERY', 'MUCH', 'FOR'],
            'I': ['AM', 'WANT', 'NEED', 'LIKE'],
            'WHAT': ['IS', 'ARE', 'TIME', 'NAME'],
            # Add more common word pairs as needed
        }
    
    def organize_words(self, words):
        word_dict = {}
        for word in words:
            # Clean the word (remove ASL: prefix, etc)
            clean_word = self.clean_word(word)
            if clean_word:
                first_letter = clean_word[0].upper()
                if first_letter not in word_dict:
                    word_dict[first_letter] = []
                word_dict[first_letter].append(clean_word)
        return word_dict
    
    def clean_word(self, word):
        # Remove special formatting and get clean word
        word = word.replace('ASL: ', '').replace('"', '')
        if '-[' in word:
            word = word.split('-[')[0]
        return word.strip().upper()
    
    def get_suggestions(self, letter, num_suggestions=4):
        """Get word suggestions for a letter"""
        self.current_letter = letter.upper()
        
        if self.current_word and self.current_word in self.context_words:
            # Return context-based suggestions
            return self.context_words[self.current_word][:num_suggestions]
        
        # Return letter-based suggestions
        if self.current_letter in self.word_dict:
            return self.word_dict[self.current_letter][:num_suggestions]
        return []
    
    def get_next_letter_suggestions(self):
        """Get suggestions for next letter"""
        if not self.current_letter:
            return []
        
        next_letter = chr(((ord(self.current_letter) - 65 + 1) % 26) + 65)
        return self.get_suggestions(next_letter)
    
    def get_previous_letter_suggestions(self):
        """Get suggestions for previous letter"""
        if not self.current_letter:
            return []
        
        prev_letter = chr(((ord(self.current_letter) - 65 - 1) % 26) + 65)
        return self.get_suggestions(prev_letter)
    
    def select_word(self, word):
        """Handle word selection and update context"""
        self.current_word = word
        self.selected_words.append(word)
        return self.get_context_suggestions(word)
    
    def get_context_suggestions(self, word, num_suggestions=4):
        """Get context-based suggestions after word selection"""
        if word in self.context_words:
            return self.context_words[word][:num_suggestions]
        return []
    
    def generate_sentence(self):
        """Generate final sentence from selected words"""
        if not self.selected_words:
            return ""
        
        sentence = " ".join(self.selected_words)
        sentence = sentence.capitalize()
        if not sentence.endswith(('.', '?', '!')):
            sentence += '.'
            
        # Reset state
        self.reset_state()
        return sentence
    
    def reset_state(self):
        """Reset predictor state"""
        self.current_letter = None
        self.current_word = None
        self.selected_words = []

    def update_context(self, word):
        self.context_history.append(word)
        if len(self.context_history) > self.max_history:
            self.context_history.pop(0)
        
        # Update word frequency
        self.word_freq[word] = self.word_freq.get(word, 0) + 1

    def generate_sentence(self, words):
        # Basic sentence template
        if not words:
            return ""
            
        sentence = " ".join(words)
        # Capitalize first letter
        sentence = sentence[0].upper() + sentence[1:]
        
        # Add period if not present
        if not sentence.endswith(('.', '?', '!')):
            sentence += '.'
            
        return sentence

class SentenceGenerator:
    def __init__(self):
        # Word type classifications
        self.subjects = {'I', 'WE', 'YOU', 'HE', 'SHE', 'THEY'}
        self.verbs = {'WANT', 'NEED', 'LIKE', 'LOVE', 'HAVE', 'SEE', 'GO', 'HELP'}
        self.objects = {'FOOD', 'WATER', 'HOME', 'BOOK', 'PHONE', 'CAR'}
        self.descriptors = {'GOOD', 'BAD', 'BIG', 'SMALL', 'HOT', 'COLD'}
        
        # Basic sentence templates
        self.templates = [
            {'pattern': ['SUBJECT', 'VERB', 'OBJECT'],
             'format': '{0} {1} {2}'},
            {'pattern': ['SUBJECT', 'VERB'],
             'format': '{0} {1}'},
            {'pattern': ['VERB', 'OBJECT'],
             'format': '{0} {1}'}
        ]
    
    def classify_word(self, word):
        """Classify word type"""
        word = word.upper()
        if word in self.subjects:
            return 'SUBJECT'
        elif word in self.verbs:
            return 'VERB'
        elif word in self.objects:
            return 'OBJECT'
        elif word in self.descriptors:
            return 'DESCRIPTOR'
        return 'OTHER'
    
    def generate_sentence(self, words):
        """Generate meaningful sentence from words"""
        if not words:
            return ""
            
        # Classify words
        classified_words = {}
        for word in words:
            word_type = self.classify_word(word)
            if word_type not in classified_words:
                classified_words[word_type] = []
            classified_words[word_type].append(word)
        
        # Try to match a template
        for template in self.templates:
            sentence = self._try_template(template, classified_words)
            if sentence:
                return self._finalize_sentence(sentence)
        
        # Fallback: join words with basic rules
        return self._generate_fallback_sentence(words)
    
    def _try_template(self, template, classified_words):
        """Try to fit words into a template"""
        pattern = template['pattern']
        words_for_template = []
        
        for word_type in pattern:
            if word_type in classified_words and classified_words[word_type]:
                words_for_template.append(classified_words[word_type][0])
            else:
                return None
        
        return template['format'].format(*words_for_template)
    
    def _generate_fallback_sentence(self, words):
        """Generate simple sentence when templates don't match"""
        return " ".join(words)
    
    def _finalize_sentence(self, sentence):
        """Apply final formatting to sentence"""
        sentence = sentence.capitalize()
        if not sentence.endswith(('.', '?', '!')):
            sentence += '.'
        return sentence 