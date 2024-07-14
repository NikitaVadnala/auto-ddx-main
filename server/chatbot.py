import typing as ty
import os
import nltk
from .sym import Sym, Row
from .extract import extract_text
from .ehr import extract_ehr
import boto3
import json

comp_med = boto3.client("comprehendmedical", region_name="us-east-1", aws_access_key_id="AKIA6NKKI5RDWYOJ3HUO", aws_secret_access_key="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")
comp = boto3.client("comprehend", region_name="ap-south-1", aws_access_key_id="AKIA6NKKI5RDWYOJ3HUO", aws_secret_access_key="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")

symptoms = []
doc = "file"

class ResponseType:
    """
    class for std communication responses
    """
    Scaler = "scaler"
    Dropdown = "dropdown"
    Attachment = "attachment"
    @staticmethod
    def scaler(data: ty.Union[int, str, bool]) -> dict:
        return {"type": ResponseType.Scaler, "payload": data}

    @staticmethod
    def dropdown(data: ty.Union[list, tuple]) -> dict:
        return {"type": ResponseType.Dropdown, "payload": list(data)}

    @staticmethod
    def attachment() -> dict:
        return {"type": ResponseType.Attachment, "payload": "Please attach document, file size less than 5MB"}

syms = Sym()

def fmt_list(l: list[Row]) -> str:
    fmt, d = "", False
    for ro in l:
        if not d:
            fmt += f"{ro.name}, "
        else:
            d = True
            fmt += ro.name
    return fmt

def responder(req: str) -> dict:
    colors = ["Yellow", "Green", "Orange", "Blue"]
    match req.get("type"):
        case ResponseType.Scaler:
            t = req.get("payload").lower().strip()
            global doc
            if t == "file":
                doc = "file"
                return ResponseType.attachment()
            elif t == "ehr":
                doc = "ehr"
                return ResponseType.attachment()
            elif t in ["hi", "hello", "hey", "hi there", "hey there", "good morning", "good afternoon", "good evening", "hola", "wassup", "sup"]:
                return ResponseType.scaler("Hello, from the Server!\n Please tell us your symptoms")
            elif t in ["no", "nothing", "that's it", "nop", "done", "just's it", "nah"]:
                sy_list = syms.match_dis()
                fmt = fmt_list(sy_list)
                if len(sy_list) > 1:
                    return ResponseType.scaler(f"You might have one of these {fmt}<br/>Please use the <b>file</b> command to upload your CBP report<br/>Please use the <b>ehr</b> command to upload report data to EHR")
                elif len(sy_list) == 1:
                    return ResponseType.scaler(f"You might have {sy_list[0].name}")
                else:
                    return ResponseType.scaler("Please visit a doctor nearby.")
            else:
                res = t
                ent = comp_med.detect_entities_v2(Text = res)
                flag = 0
                nos = ["no", "none", "nah", "nope"]
                for i in nos:
                    if i in res:
                        flag = 1
                        break
                if(flag == 1):
                    print("Have a healty life :)")
                else:
                    for entity in ent["Entities"]:
                        if entity["Category"] == "MEDICAL_CONDITION" and entity["Type"]=="DX_NAME":
                            symptoms.append(entity["Text"])
                            syms.add(entity["Text"])
                            flag = 1
                    if flag == 0:
                        print("No symptoms detected.")
                    resp = '1'
                    # while(resp != '0'):
                    #     resp = input("Are you facing more symptoms?\nIf no enter: 0\n")
                    #     ent = comp_med.detect_entities_v2(Text = resp)
                    #     flag = 0
                    #     for entity in ent["Entities"]:
                    #         if entity["Category"] == "MEDICAL_CONDITION" and entity["Type"]=="DX_NAME" :
                    #             symptoms.append(entity["Text"])
                    #             flag = 1
                    #     if flag == 0:
                    #         print("No extra symptoms are added.")

                    if("symptoms" in symptoms):
                        symptoms.remove("symptoms")    
                if len(symptoms) >= 1:
                    return ResponseType.scaler(f"You symptoms are {', '.join(symptoms)} <br>Do you have anything else?")
                else:
                    return ResponseType.scaler(f"No symptoms detected.")
        case ResponseType.Dropdown:
            index = int(req.get("payload").strip())
            return f"You have selected {colors[index]}"
        case ResponseType.Attachment:
            file_path = req.get("payload")
            if( doc == "file"):
                patientDetails = extract_text(file_path)
            elif(doc == "ehr"):
                patientDetails = extract_ehr(file_path)
            os.remove(file_path)
            return ResponseType.scaler(patientDetails)
        case other:
            raise NotImplemented
    return ResponseType.scaler(data)
