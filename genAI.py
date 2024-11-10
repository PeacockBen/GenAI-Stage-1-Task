from paddleocr import PaddleOCR
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import io
from googletrans import Translator
from fuzzywuzzy import fuzz
import string
import json

def ocr_pdf(pdf_path, ocr_model):
    # Open the PDF file
    doc = fitz.open(pdf_path)

    # Iterate through pages and perform OCR
    for page_number in range(len(doc)):
        page = doc[page_number]
        pix = page.get_pixmap(dpi=400)
        img_bytes = pix.tobytes(output='png')
        img = Image.open(io.BytesIO(img_bytes))

        # Convert image to numpy array
        img_np = np.array(img)

        # Perform OCR
        result = ocr_model.ocr(img_np)

        # # Extract text
        page_text = ''
        for line in result:
            for x in line:
                page_text += x[1][0] + ' '
        
        return page_text

def translation (page_text):  
    translator = Translator()
    translated_text = translator.translate(page_text, src='fr', dest='en').text

    return translated_text

def find_approximate_term(text, term, threshold=80, min_threshold=50, threshold_step=5):
    """
    Find approximate matches of a term in a text using fuzzy string matching.

    Starts from a specified threshold and decreases it step by step until it reaches the minimum threshold,
    searching for matches at each level.

    Parameters:
    - text (str): The text to search within.
    - term (str): The term to search for.
    - threshold (int): The starting similarity threshold (0-100). Default is 80.
    - min_threshold (int): The minimum similarity threshold to consider (0-100). Default is 50.
    - threshold_step (int): The amount to decrease the threshold in each iteration. Default is 5.

    Returns:
    - List[int]: A list of indexes where approximate matches of the term are found in the text.
    """
    indexes = []
    words = text.split()
    current_threshold = threshold

    while current_threshold >= min_threshold:
        temp_indexes = []
        for i, word in enumerate(words):
            # Check similarity of each word with the term
            if fuzz.ratio(word.lower(), term.lower()) >= current_threshold:
                temp_indexes.append(i)
        if temp_indexes:
            indexes.extend(temp_indexes)
            return list(set(indexes))  # Remove duplicates
        else:
            current_threshold -= threshold_step

    # If no matches found above min_threshold, return empty list
    return []

def find_word_instances(text, word, remove_apostrophes=False, min_threshold=80):
    """
    Finds all instances of a word in the text, matching at least the minimum threshold.

    Parameters:
    - text (str): The text to search in.
    - word (str): The word to search for.
    - remove_apostrophes (bool): If True, removes apostrophes from words in text and the search word.
    - min_threshold (int): The minimum similarity threshold (0-100).

    Returns:
    - List[int]: List of indexes where the word is found in the text.
    """
    indexes = []
    words = text.split()

    # remove brackets or curly brackets
    words = [w.replace("(", "").replace(")", "").replace("{", "").replace("}", "") for w in words]

    # remove letter accents
    words = [w.replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a").replace("â", "a").replace("ô", "o").replace("î", "i").replace("û", "u") for w in words]

    # remove apostrophes from words in the text and the search word
    if remove_apostrophes:
        words = [w.replace("'", "") for w in words]
        word = word.replace("'", "")

    # Loop over words and compute similarity
    for i, w in enumerate(words):
        similarity = fuzz.ratio(w.lower(), word.lower())
        if similarity >= min_threshold:
            indexes.append(i)

    return indexes

def extract_indexes_fuzzy(french_text):
    """
    Extract indexes of specific terms from French text using fuzzy matching.

    Uses fuzzy string matching to find approximate occurrences of specified terms in the text,
    collects their indexes, and returns them in a dictionary.

    Parameters:
    - french_text (str): The French text to search within.

    Returns:
    - dict: A dictionary containing lists of indexes for the terms 'Nom', 'Entier', 'Abrege',
      'D'entreprise', 'L'acte', and 'Mentionner'.
    """
    min_threshold = 55
    lacte_final=[]
    multiplier = 0.6

    indexes_nom = find_word_instances(french_text, "Nom", min_threshold=min_threshold)
    indexes_entier = find_word_instances(french_text, "entier", min_threshold=min_threshold)
    indexes_abrege = find_word_instances(french_text, "abrege", min_threshold=min_threshold)
    indexes_dentreprise = find_word_instances(french_text, "d'entreprise", min_threshold=min_threshold)
    indexes_mentionner = find_word_instances(french_text, "mentionner", min_threshold=min_threshold)

    while lacte_final == [] and multiplier<2:
        found = False
        for i in range(100,0,-5):
            indexes_lacte = find_word_instances(french_text, "l'acte", min_threshold=i)
            for index in indexes_lacte:
                if index >59 and index< (len(french_text.split())/2)*multiplier:
                    # remove the index from the list
                    lacte_final.append(index)
                    multiplier = 2.5
                    found = True
                    break
            if found:
                break
        if found:
            break
        multiplier += 0.1

    # Create a dictionary of the indexes
    indexes_dict = {
        "Nom": indexes_nom,
        "Entier": indexes_entier,
        "Abrege": indexes_abrege,
        "D'entreprise": indexes_dentreprise,
        "L'acte": lacte_final,
        "Montionner": indexes_mentionner
    }
    return indexes_dict

def extract_data(french_text, indexes_dict):
    french_text_split = french_text.split()
    # Remove parentheses and replace accents from words
    french_text_split = [
        word.replace("(", "").replace(")", "").replace("{", "").replace("}", "")
        for word in french_text_split
    ]
    french_text_split = [
        word.replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ô", "o")
        .replace("î", "i")
        .replace("û", "u")
        for word in french_text_split
    ]

    company_name = ""
    company_indicator = ""
    pattern1 = False
    pattern2 = False
    finalAbregeIndex = 0

    for currentNom in indexes_dict["Nom"]:
        for currentEntier in indexes_dict["Entier"]:
            if (
                currentNom < currentEntier
                and currentNom - currentEntier < -2
                and currentNom + currentEntier < 120
                and find_approximate_term(
                    " ".join(french_text_split[currentNom:currentEntier]), "abrege"
                )
                == []
                and pattern2 == False
            ):
                company_name = " ".join(
                    french_text_split[currentNom + 1 : currentEntier - 1]
                )
                pattern1 = True

        for currentAbrege in indexes_dict["Abrege"]:
            for currentEntier in indexes_dict["Entier"]:
                if (
                    currentNom < currentEntier < currentAbrege
                    and currentAbrege - currentNom < 10
                    and pattern1 == False
                ):
                    company_name = " ".join(
                        french_text_split[
                            currentNom
                            + 2
                            - (currentNom - currentEntier) : currentAbrege - 1
                        ]
                    )
                    pattern2 = True
                    finalAbregeIndex = int(currentAbrege)

                if (
                    currentNom < currentEntier < currentAbrege
                    and currentAbrege - currentNom < 10
                    and "Nom" not in french_text_split[currentNom:currentAbrege]
                    and "abrege" not in french_text_split[currentNom:currentAbrege]
                ):
                    company_name = " ".join(
                        french_text_split[
                            currentNom
                            + 2
                            - (currentNom - currentEntier) : currentAbrege - 1
                        ]
                    )
                    pattern2 = True

        for currentDentreprise in indexes_dict["D'entreprise"]:
            if (
                currentDentreprise < currentNom
                and 4 < currentNom - currentDentreprise <= 8
                and currentNom + currentDentreprise < 120
            ):
                temp = []
                for value in french_text_split[currentDentreprise:currentNom]:
                    if value.isnumeric():
                        temp.append(value)
                company_indicator = " ".join(temp)
    Lacte = ""
    # remove apostrophes from words in the text and the search word
    french_text_split = [w.replace("'", "") for w in french_text_split]
    processed_join = " ".join(french_text_split)

    bodyText = " ".join(french_text_split[indexes_dict["L'acte"][0]:])
    
    return company_name, company_indicator, bodyText

def extract_purpose(text):
    """
    Extract a portion of text based on capitalisation criteria.

    Processes the text starting from the second word, including words that are fully uppercase,
    capitalised (first letter uppercase, rest lowercase), or punctuation marks. Stops when a word
    doesn't meet these criteria. If the result contains three words or fewer, returns the first ten
    words of the original text.

    Parameters:
    - text (str): The text to process.

    Returns:
    - str: The extracted portion of the text based on the specified criteria.
    """
    words = text.split()
    words = [word.strip(string.punctuation) for word in words]
    words = words[1:]
    valid_words = []
    for word in words:
        # If the word is only punctuation, keep it
        if all(char in string.punctuation for char in word):
            valid_words.append(word)
            continue
        # Remove punctuation from the word for checking
        stripped_word = word.strip(string.punctuation)
        if not stripped_word:
            valid_words.append(word)
            continue
        # Check if the word is fully uppercase
        if stripped_word.isupper():
            valid_words.append(word)
        # Check if the word is capitalized (first letter uppercase, rest lowercase)
        elif stripped_word.istitle():
            valid_words.append(word)
        else:
            # The word doesn't meet the conditions, so we stop processing
            break

    # if two words or less, return first 10 originalwords
    if len(valid_words) <= 3:
        return ' '.join(words[:10])
    # if more than 2 words, return first 10 words
    else:
        return ' '.join(valid_words)

def main():
    # Initialize PaddleOCR with French language support
    ocr_model = PaddleOCR(lang='fr', use_gpu=False)
    # path to folder of pdfs
    pdf_path = r'input_pdfs\24000001.pdf'
    data = []
    finaldata = []
    for i in range(1,11):
        if i < 10:
            pdf_path = pdf_path[:-6]+ "0" + str(i) + ".pdf"
        else: 
            pdf_path = pdf_path[:-6]+ str(i) + ".pdf"
        page_text = ocr_pdf(pdf_path, ocr_model)

        indexes = extract_indexes_fuzzy(page_text)
        data.append(extract_data(page_text,indexes))
        currentPurpose = extract_purpose(data[i-1][2])
        # add current purpose to the data [i-1]
        data[i-1] = list(data[i-1])
        data[i-1].append(currentPurpose)
        finaldata.append(data[i-1])
        

    json_data = []
    for i in range(1, 11):
        data = {}
        data["company_name"] = finaldata[i-1][0]
        data["company_indicator"] = finaldata[i-1][1]
        data["body_text"] = translation(finaldata[i-1][2])
        data["purpose"] = translation(finaldata[i-1][3])
        json_data.append(data)

    with open('data.json', 'w') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    print(json_data)
        
if __name__ == '__main__':
    main()

