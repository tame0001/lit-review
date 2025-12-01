import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

from pypdf import PdfReader
from pathlib import Path

path = Path(__file__).parent / "sample.pdf"
reader = PdfReader(path)

# read page 2-8
pages = reader.pages[1:8]
text = ""
for page in pages:
    text += page.extract_text()

# print(text)

nltk.download("stopwords")
nltk.download("punkt_tab")
stop_words = set(stopwords.words("english"))
words = word_tokenize(text)

# Calculate word frequency
freq_table = {}
for word in words:
    word = word.lower()
    if word.isalpha() and word not in stop_words:
        if word in freq_table:
            freq_table[word] += 1
        else:
            freq_table[word] = 1

# Sentence scoring
sentences = sent_tokenize(text)
sentence_scores = {}
for sentence in sentences:
    for word, freq in freq_table.items():
        if word in sentence.lower():
            if sentence in sentence_scores:
                sentence_scores[sentence] += freq_table[word]
            else:
                sentence_scores[sentence] = freq_table[word]

sum_value = 0
for score in sentence_scores.values():
    sum_value += score
average_score = sum_value / len(sentence_scores)

summary = ""
for sentence in sentences:
    if sentence in sentence_scores and sentence_scores[sentence] > 1.2 * average_score:
        summary += sentence + " "

print(summary)
