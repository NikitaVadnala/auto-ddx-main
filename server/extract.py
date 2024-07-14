# Modules required for the data extraction

import boto3
from trp import Document
import fitz
import os
import re
import pandas as pd


# client = boto3.client('textract', region_name="ap-south-1", aws_access_key_id='AKIA6NKKI5RDQBGHA2W4',aws_secret_access_key= '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')

client = boto3.client('textract', region_name="ap-south-1", aws_access_key_id='AKIA6NKKI5RD2NZ5MY47',aws_secret_access_key= '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')

def extract_text(filePath: str) -> str:
    parseDataHTML = '<h2>CBP Report</h2><br/>'
    # filePath = '/content/drive/MyDrive/Panace/report-mos_012016104609.jpg'

    if os.path.splitext(filePath)[1] == '.pdf':
        doc = fitz.open(filePath)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        bytesDataOfImage = pix.tobytes()
    else:
        with open(filePath, 'rb') as rawImage:
            rawImageContent = rawImage.read()
            bytesDataOfImage = bytearray(rawImageContent)

    response = client.analyze_document(Document={
      'S3Object': {
          'Bucket': 'panace-fs-doc-processing',
      },
      'Bytes': bytesDataOfImage,
    }, FeatureTypes=['FORMS'])

    doc = Document(response)
    patientData = {}

    nameFound = False
    ageFound = False
    genderFound = False

    for page in doc.pages:
        for field in page.form.fields:
            key = str(field.key)
            lowerKey = re.sub("[^a-zA-Z]", " ", key.lower()).strip()
            # Finding the names
            if not nameFound:
                if "patient name" in lowerKey:
                    nameFound = True
                    patientData["name"] = str(field.value)
                elif "name" in lowerKey:
                    patientData["name"] = str(field.value)
                    nameFound = True
            # Finding the age
            if not ageFound:
                if "age" in lowerKey:
                    pattern = r"age[^a-zA-Z]*"
                    if re.fullmatch(pattern, lowerKey):
                        patientData["age"] = str(field.value)
                        ageFound = True
                    else:
                        splitKeys = re.split(r"[^a-zA-Z]", lowerKey)
                        splitVals = re.split(r"[^a-zA-Z0-9]", str(field.value))
                        passKeys = 0
                        for i in splitKeys:
                            if i:
                                if "age" in i:
                                    if passKeys&1:
                                        patientData["age"] = splitVals[-1]
                                        patientData["gender"] = splitVals[0]
                                    else:
                                        patientData["age"] = splitVals[0]
                                        patientData["gender"] = splitVals[-1]
                                    ageFound = True
                                    genderFound = True
                                passKeys += 1
            # Fetching the gender
            if not genderFound:
                if "gender" in lowerKey or "sex" in lowerKey:
                    pattern1 = r"gender[^a-zA-Z]*"
                    pattern2 = r"sex[^a-zA-Z]*"
                    if re.fullmatch(pattern1, lowerKey) or re.fullmatch(pattern2, lowerKey):
                        patientData["gender"] = str(field.value)
                        genderFound = True
                    else:
                        splitKeys = re.split(r"[^a-zA-Z]", lowerKey)
                        splitVals = re.split(r"[^a-zA-Z0-9]", str(field.value))
                        passKeys = 0
                        for i in splitKeys:
                            if i:
                                if "age" in i:
                                    if passKeys&1:
                                        patientData["age"] = splitVals[-1]
                                        patientData["gender"] = splitVals[0]
                                    else:
                                        patientData["age"] = splitVals[0]
                                        patientData["gender"] = splitVals[-1]
                                    ageFound = True
                                    genderFound = True
                                passKeys += 1
    patientData["age"] = re.search(r"(\d+)", patientData["age"]).group(1)
    if patientData["gender"].lower()=="m":
        patientData["gender"] = "Male"
    elif patientData["gender"].lower()=="f":
            patientData["gender"] = "Female"
    else:
        patientData["gender"] = patientData["gender"].capitalize()

    for i in patientData:
        parseDataHTML += f"<i>{i.title()}</i>: {patientData[i]}<br/>"
    parseDataHTML += "<br/>"
    # return patientData

    response = client.analyze_document(
        Document={'Bytes': bytesDataOfImage},
        FeatureTypes=['TABLES']
    )

    # print(response) #*****************************************

    def map_blocks(blocks, block_type):
        return {
            block['Id']: block
            for block in blocks
            if block['BlockType'] == block_type
        }

    blocks = response['Blocks']
    tables = map_blocks(blocks, 'TABLE')
    cells = map_blocks(blocks, 'CELL')
    words = map_blocks(blocks, 'WORD')
    selections = map_blocks(blocks, 'SELECTION_ELEMENT')


    def get_children_ids(block):
        for rels in block.get('Relationships', []):
            if rels['Type'] == 'CHILD':
                yield from rels['Ids']

    dataframes = []

    for table in tables.values():

        # Determine all the cells that belong to this table
        table_cells = [cells[cell_id] for cell_id in get_children_ids(table)]

        # Determine the table's number of rows and columns
        n_rows = max(cell['RowIndex'] for cell in table_cells)
        n_cols = max(cell['ColumnIndex'] for cell in table_cells)
        content = [[None for _ in range(n_cols)] for _ in range(n_rows)]

        # Fill in each cell
        for cell in table_cells:
            cell_contents = [
                words[child_id]['Text']
                if child_id in words
                else selections[child_id]['SelectionStatus']
                for child_id in get_children_ids(cell)
            ]
            i = cell['RowIndex'] - 1
            j = cell['ColumnIndex'] - 1
            content[i][j] = ' '.join(cell_contents)

        # We assume that the first row corresponds to the column names
        dataframe = pd.DataFrame(content[1:], columns=content[0])
        dataframes.append(dataframe)
    # print(dataframe) #****************************************

    content = {}
    hg_ptn = r"ha?emoglobin"
    rbc_ptn = r"(total )?(r\.*b\.*c\s*)(count)?"
    wbc_ptn = r"(total )?(w\.*b\.*c\s*)(count)?"
    # ptlt_ptn = r"platelet count"

    detailsDone = [False]*3 # change to 4 when you include platelet count
    # haemoglobin, rbc count, wbc count, platelet count
    mapIndexValue = {0: "haemoglobin", 1: "rbc count", 2: "wbc count"} # 3: "platelet count"
    mapRegexPattern = {0: hg_ptn, 1: rbc_ptn, 2: wbc_ptn} # 3: ptlt_ptn

    for df in dataframes:
        n = len(df.index)
        if n>6:
            for i in range(n):
                key = df.iloc[i,0]
                for j in range(len(detailsDone)): # 4 iterations
                    if detailsDone[j]==False:
                        match = re.search(mapRegexPattern[j], str(key), re.I)
                        if match is not None:
                            val=df.iloc[i][1]
                            content[mapIndexValue[j]] = float(re.search(r"(\d+\.?\d*)", str(val)).group(1))
                            detailsDone[j] = True

    for i in content:
        parseDataHTML += f"<i>{i.title()}</i>: {content[i]}<br/>"
    parseDataHTML += "<br/>"
    # print(content) #*************************

    # Comparision with the standard values

    standardValues = {
        "haemoglobin" : {
            "genderSpecific": True,
            "Male": [13.2, 16.6],
            "Female": [11.6, 15]
        },
        "rbc count": {
            "genderSpecific": True,
            "Male": [4.7, 6.1],
            "Female": [4.2, 5.4]
        },
        "wbc count": {
            "genderSpecific": False,
            "default": [4000, 11000],
        },
        "platelet count": {
            "genderSpecific": False,
            "default": [150000, 450000]
        }
    }

    # Use patientData, content and standardValues

    gender = patientData["gender"]
    displayText = []
    for i in content:
        if standardValues[i]["genderSpecific"]==True:
            if content[i]<standardValues[i][gender][0]:
                displayText.append(f"You are having the {100-(content[i]*100/standardValues[i][gender][0]):.2f}% less {i.title()} than the normal value.")
            elif content[i]>standardValues[i][gender][1]:
                displayText.append(f"You are having the {(content[i]*100/standardValues[i][gender][1])-100:.2f}% more {i.title()} than the normal value.")
            else:
                displayText.append(f"Your {i.title()} is good!!")
    else:
        if content[i]<standardValues[i]["default"][0]:
            displayText.append(f"You are having the {100-(content[i]*100/standardValues[i]['default'][0]):.2f}% less {i.title()} than the normal value.")
        elif content[i]>standardValues[i]["default"][1]:
            displayText.append(f"You are having the {(content[i]*100/standardValues[i]['default'][1])-100:.2f}% more {i.title()} than the normal value.")
        else:
            displayText.append(f"Your {i.title()} is good!!")
    
    # print(displayText)
    if displayText:
        parseDataHTML += "<h3>Analysis: </h3><br/>"
    for index, text in enumerate(displayText):
        parseDataHTML += f"{index+1}. {text}<br/>"

    # parseDataJSON = {"user_details": patientData, "sample_records": content, "analysis": displayText}

    return parseDataHTML
