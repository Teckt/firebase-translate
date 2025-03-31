import os.path
import time
from xml.dom import minidom

import xml.etree.ElementTree as ET

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import six
from google.cloud import translate_v2 as translate
from dotenv import load_dotenv

load_dotenv()

def get_text(nodelist):
    rc = []
    for node in nodelist:

        if node.nodeType == node.TEXT_NODE:

            rc.append(node.data)
    return ''.join(rc)


class FirestoreApi:

    def __init__(self):
        cred = credentials.Certificate('firebase_creds.json')
        try:
            self.app = firebase_admin.initialize_app(cred, {'storageBucket': 'df-studio-1.appspot.com'})
        except ValueError:
            self.app = firebase_admin.get_app()

        self.db = firestore.client()




class TranslateAPI:

    def __init__(self):
        self.client = translate.Client()

    def translate_text(self, target, text):
        """Translates text into the target language.

        Target must be an ISO 639-1 language code.
        See https://g.co/cloud/translate/v2/translate-reference#supported_languages
        """

        if isinstance(text, six.binary_type):
            text = text.decode("utf-8")

        # Text can also be a sequence of strings, in which case this method
        # will return a sequence of results for each text.
        result = self.client.translate(text, target_language=target,)

        # print(u"Text: {}".format(result["input"]))
        # print(u"Translation: {}".format(result["translatedText"]))
        # print(u"Detected source language: {}".format(result["detectedSourceLanguage"]))
        return result["translatedText"]

def generate_xml(translate_api, target_language_code):
    secs = time.time()

    # Define the XML structure
    resources = ET.Element("resources")

    # parse original strings.xml and translate
    dom = minidom.parse(os.path.join(os.getenv("TRANSLATE_STRINGS_FILE")))

    strings = dom.getElementsByTagName('string')
    print(f"There are {len(strings)} strings:")

    start = False
    translated = 0
    for string in strings:
        # string_name = string.attributes.items()[0][1]
        # if string_name == "v3_storage_requirement_message":
        # if string_name == "login_failed":
        #     start = True
        #
        # if not start:
        #     continue
        string_name = string.attributes['name'].value
        string_value = get_text(string.childNodes)

        if 'translatable' in string.attributes:
            continue
        else:
            translated += 1
            text_to_translate = f"{string_value}"
            translated_text = translate_api.translate_text(target=target_language_code, text=text_to_translate)
            translated_text = translated_text.replace('&quot;', '\"')
            translated_text = translated_text.replace('&amp;#39;', '\\\'')
            translated_text = translated_text.replace('&#39;', '\\\'')
            translated_text = translated_text.replace(' ', ' ')
            print(f'<string name="{string_name}">{translated_text}</string>')
            # Add <string> element
            string_element = ET.SubElement(resources, "string")
            string_element.set("name", string_name)
            string_element.text = translated_text


    # # Create the XML tree
    # tree = ET.ElementTree(resources)

    # Convert the ElementTree to a string
    xml_str = ET.tostring(resources, encoding="utf-8")

    # Use minidom to pretty-print the XML
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="    ", encoding="utf-8")

    # Create dir
    language_dir = os.path.join(os.getenv("TRANSLATE_RESULTS_DIR"), f"values-{target_language_code}") 
    if not os.path.exists(language_dir):
        os.mkdir(language_dir)

    # Write the XML to a file
    with open(f"{language_dir}/strings.xml", "wb") as xml_file:
        xml_file.write(pretty_xml)

    print(f"xml generated in {(time.time() - secs):.1f} seconds in {language_dir}")

if __name__=="__main__":
    translate_api = TranslateAPI()

    languages = [
        "de",
        "es",
        "fr",
        "hi",
        "it",
        "ja",
        "ko",
        "pt",
        "ru",
        "th",
        "vi",
        "zh",
    ]
    for language_code in languages:
        generate_xml(translate_api=translate_api, target_language_code=language_code)
