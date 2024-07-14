#!/usr/bin/python3

import boto3
import os
import time
import json
import nltk
from pymongo import MongoClient

def extract_ehr(filePath) -> dict:

  nltk.download("punkt", quiet=True)
  nltk.download("averaged_perceptron_tagger", quiet=True)

  # For readability there are 3 statements being written which even can be completed in a single statement

  s3 = boto3.client('s3', region_name="ap-south-1", aws_access_key_id='AKIA6NKKI5RD2NZ5MY47',aws_secret_access_key= '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')
  client = boto3.client('textract', region_name="ap-south-1", aws_access_key_id='AKIA6NKKI5RD2NZ5MY47',aws_secret_access_key= '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')
  cmp_med = boto3.client('comprehendmedical', region_name="us-east-1", aws_access_key_id='AKIA6NKKI5RD2NZ5MY47',aws_secret_access_key= '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')

  # Uploading the File to the S3 bucket for the purpose of processing the data

  validFileExtensions = {'.jpeg', '.jpg', '.png', '.tiff'}

  bucket = 'panace-fs-doc-processing'
  filename = os.path.basename(filePath)

  fileExt = os.path.splitext(filePath)[1]

  if fileExt.lower() == '.pdf':
    print(type(filename), type(filePath), str(filePath))
    s3.upload_file(Filename=str(filePath), Bucket=bucket, Key=filename)
  elif fileExt.lower() in validFileExtensions:
    with open(filePath, 'rb') as rawImage:
      rawImageContent = rawImage.read()
      bytesDataOfImage = bytearray(rawImageContent)
  else:
    print("File should be of jpeg/png/tiff")
    return -1 # Invalid File Extension

  # Making Asynchronous calls for extracting data from PDF's

  def BeginJob(client, s3BucketName, objectName):
    response = None
    response = client.start_document_text_detection(
        DocumentLocation={
            'S3Object' : {
                'Bucket' : bucket,
                'Name' : filename
            }
        }
    )

    return response['JobId']

  def IsJobComplete(client, jobId):
    time.sleep(2)
    response = client.get_document_text_detection(JobId=jobId)
    status = response["JobStatus"]

    while status=="IN_PROGRESS":
      time.sleep(1)
      response = client.get_document_text_detection(JobId=jobId)
      status = response["JobStatus"]

    return status == "SUCCEEDED"

  def FetchJobResults(client, jobId):
    time.sleep(5)
    response = client.get_document_text_detection(JobId=jobId)
    return response

  if fileExt == ".pdf":
    jobId = BeginJob(client, bucket, filename)
    if IsJobComplete(client, jobId):
      response = FetchJobResults(client, jobId)
  else:
    response = client.detect_document_text(Document={
        'S3Object': {
            'Bucket': bucket,
        },
        'Bytes': bytesDataOfImage,
      })

  OCRData = ""

  for item in response["Blocks"]:
    if item["BlockType"] == "LINE":
      OCRData += item["Text"]

  res = cmp_med.infer_icd10_cm(Text=OCRData)

  entityDetection = cmp_med.detect_entities_v2(Text=OCRData)

  # holders

  diagnosis = set()
  symptoms = set()
  sym = set()

  medStatus = {}
  medConditions = set()

  medications = set()
  details = {}

  tests = set()

  # all symptoms
  for i in res["Entities"]:
    if i["Category"] == "MEDICAL_CONDITION" and i["Type"]=="DX_NAME" and i["Score"]>0.9:
      s = i["Text"].split(" ")[0]
      tokenized = nltk.word_tokenize(s)
      nouns = [word for (word, pos) in nltk.pos_tag(tokenized) if(pos[:2] == 'NN')]
      if nouns:
        sym.add(nouns[0])

  for entity in entityDetection["Entities"]:
    # symptoms and diagnosis
    if entity["Category"] == "MEDICAL_CONDITION" and entity["Type"]=="DX_NAME" and entity["Score"]>0.9:
      for j in entity["Traits"]:
        if medStatus.get(entity["Text"], 0) == 0:
          medStatus[entity["Text"]] = [j["Name"],j["Score"]]
          medConditions.add(entity["Text"])
        else:
          if (medStatus[entity["Text"]][1] >= j["Score"] and medStatus[entity["Text"]][0] == "NEGATION"):
            medConditions.discard(i["Text"])
          elif (medStatus[entity["Text"]][1] <= j["Score"] and j["Name"] == "NEGATION"):
            medConditions.discard(i["Text"])

        if j["Name"]=="DIAGNOSIS":
          diagnosis.add(entity["Text"])
        elif j["Name"]=="SYMPTOM":
          symptoms.add(entity["Text"])


    # medications
    if entity["Category"] == "MEDICATION" and entity["Score"]>0.93:
      if(len(entity)>8):
        details_cur = {}
        medications.add(entity["Text"])
        for j in entity["Attributes"]:
          details_cur[j["Type"]] = j["Text"]
        details[entity["Text"]] = details_cur
      else:
        medications.add(entity["Text"])


    # tests
    if entity["Category"] == "TEST_TREATMENT_PROCEDURE" and entity["Score"]>0.85:
      tests.add(entity["Text"])

  # Output
  res = {}
  res["Symptoms"] = list((sym&medConditions)-(diagnosis))
  res["Diagnosis"] = list(diagnosis)
  res["Medications"] = list(medications)
  res["Details"] = list(details)
  res["Tests"] = list(tests)

  # return json.dumps(res, indent=4) # Readability
  #Mongo Db
  mongo_client=MongoClient("mongodb+srv://root:root@panace-ehr-db.gvuwobv.mongodb.net/?retryWrites=true&w=majority")
  db = mongo_client.get_database("EHR-DB")
  ehr = db.EHR
  if ehr.count_documents(res)==0:
    ehr.insert_one(res)
    print("Data Inserted Successfully")
  print(res)
  sym = res["Symptoms"]
  dia = res["Diagnosis"]
  med = res["Medications"]
  detil = res["Details"]
  tet = res["Tests"]
  ret = "<h1>Report</h1><br/>"
  if sym:
    ret += f"<b>Symtoms:</b> {', '.join(sym)}<br/>"
  if dia:
    ret += f"<b>Diagnosis:</b> {', '.join(dia)}<br/>"
  if med:
    ret += f"<b>Medications:</b> {', '.join(med)}<br/>"
  if detil:
    ret += f"<b>Details:</b> {', '.join(detil)}<br/>"
  if tet:
    ret += f"<b>Tests:</b> {', '.join(tet)}<br/>"
  # return json.dumps(res, indent=4)
  return ret

# res = extract_ehr(filePath='report1.pdf')
# print(res)

