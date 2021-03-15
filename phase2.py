from flask import Flask, request
import boto3
import io
from io import BytesIO
import sys

import psutil
import time

import math
from PIL import Image, ImageDraw, ImageFont

import logging
from pprint import pprint
from botocore.exceptions import ClientError



def process_text_detection(bucket, document):

    
    #Get the document from S3
    s3_connection = boto3.resource('s3')
                          
    s3_object = s3_connection.Object(bucket,document)
    s3_response = s3_object.get()

    stream = io.BytesIO(s3_response['Body'].read())
    image=Image.open(stream)
    s=''

   
    # Detect text in the document
    
    client = boto3.client('textract')

    #process using S3 object
    response = client.detect_document_text(
        Document={'S3Object': {'Bucket': bucket, 'Name': document}})

    #Get the text blocks
    blocks=response['Blocks']
    width, height =image.size  
    draw = ImageDraw.Draw(image)  
    print ('Detected Document Text')
   
    # Create image showing bounding box/polygon the detected lines/text
    for block in blocks:
            #print('Type: ' + block['BlockType'])
            if block['BlockType'] == 'WORD':
                s+=block['Text']#print('Detected: ' + block['Text'])
                s+=' '
                #print('Confidence: ' + "{:.2f}".format(block['Confidence']) + "%")
            
    image.show()
                    
    #print('-'*88)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    comp_detect = ComprehendDetect(boto3.client('comprehend'))


    '''print("Sample text used:")
    print('-'*88)
    print(s)
    print('-'*88)'''

    print("Detecting languages.")
    languages = comp_detect.detect_languages(s)
    #pprint(languages)
    lang_code = languages[0]['LanguageCode']

    print("Detecting personally identifiable information (PII).")
    pii_entities = comp_detect.detect_pii(s, lang_code)
    #n=0
    
    for i in range(len(pii_entities)):
        begin=pii_entities[i]['BeginOffset']#pprint(pii_entities[i]['BeginOffset'])
        last=pii_entities[i]['EndOffset']      
        words=s[:begin].split()
        words_between=s[begin:last].split()
        #print(words, words_between)
        count=0
        for block in blocks:
            if block['BlockType']=='WORD':
                count+=1
            if count>len(words) and count<=(len(words)+len(words_between)): 
                draw=ImageDraw.Draw(image)
                draw.rectangle([(width * block['Geometry']['Polygon'][1]['X'],
                height * block['Geometry']['Polygon'][0]['Y']),
                (width * block['Geometry']['Polygon'][3]['X'],
                height * block['Geometry']['Polygon'][3]['Y'])],fill='black',
                width=2)
        #n=last
    image.show()
    #print('-'*88)
        

logger = logging.getLogger(__name__)


class ComprehendDetect:
    
    def __init__(self, comprehend_client):
        
        self.comprehend_client = comprehend_client

    def detect_languages(self, text):
        
        try:
            response = self.comprehend_client.detect_dominant_language(Text=text)
            languages = response['Languages']
            logger.info("Detected %s languages.", len(languages))
        except ClientError:
            logger.exception("Couldn't detect languages.")
            raise
        else:
            return languages

    def detect_pii(self, text, language_code):
        
        try:
            response = self.comprehend_client.detect_pii_entities(
                Text=text, LanguageCode=language_code)
            entities = response['Entities']
            logger.info("Detected %s PII entities.", len(entities))
        except ClientError:
            logger.exception("Couldn't detect PII entities.")
            raise
        else:
            return entities
 
def main():

    bucket = 'kusuma'
    document = 'pii.JPG'
    process_text_detection(bucket,document)
    
if __name__ == "__main__":
    main()