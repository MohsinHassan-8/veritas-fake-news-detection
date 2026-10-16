import re
import string
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import emoji
from internet_words_remover import words_remover
import nltk

nltk.download('stopwords',  quiet=True)
nltk.download('punkt_tab',  quiet=True)
nltk.download('wordnet',    quiet=True)
nltk.download('omw-1.4',    quiet=True)

stop_words = set(stopwords.words('english'))
wn_lem     = WordNetLemmatizer()
punc       = str.maketrans('', '', string.punctuation)

def lemmatize_word(word: str) -> str:
    """Lemmatize checking both verb and noun forms, return shorter result."""
    v = wn_lem.lemmatize(word, pos='v')
    n = wn_lem.lemmatize(word, pos='n')
    return v if len(v) <= len(n) else n

def preprocessing(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("Input text is empty.")

    # 1. Lowercase and strip
    text = text.lower().strip()

    # 2. Remove HTML tags
    text = re.sub(r'<.*?>', '', text)

    # 3. Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)

    # 4. Remove punctuation
    text = text.translate(punc)

    # 5. Convert emojis to text (before stopword removal)
    text = emoji.demojize(text)

    # 6. Replace internet/chat slang words
    text = words_remover(text)

    # 7. Remove stopwords
    text = ' '.join(w for w in text.split() if w not in stop_words)

    # 8. Lemmatization (verb + noun)
    text = ' '.join(lemmatize_word(w) for w in text.split())

    return text
