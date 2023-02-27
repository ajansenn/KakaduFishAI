from predict_v1 import load_model, predict
import numpy as np
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import cv2, io, json, logging, os, sys, tempfile,uuid
from azure.storage.blob import (ResourceTypes, AccountSasPermissions, AccessPolicy, 
                                ContainerSasPermissions, generate_container_sas, 
                                BlobServiceClient, BlobClient, ContainerClient)


# dictionary list for thresholding values from Custom Vision
thresholding_values = {
 "Ambassis agrammus":50 ,
    "Ambassis macleayi":50 ,
    "Amniataba percoides":50 ,
    "Craterocephalus sturcusmuscarum":50,
    "Denariusa bandata":50,
    "Glossamia aprion":50,
    "Glossogobius": 50,
    "Hephaestus fuliginosus": 50,
    "Lates calcarifer":50,
    "Leiopotherapon unicolor": 50,
    "Liza ordensis": 50,
    "Megalops cyprinoides": 50,
    "Melanotaenia nigrans":50 ,
    "Melanotaenia splendida inornata":50,
    "Mogurnda mogurnda": 50,
    "Nemetalosa erebi": 50,
    "Neoarius":50,
    "Neosilurus":50,
    "Oxyeleotris": 50,
    "Other":50,
    "Scleropages jardinii":50,
    "Strongylura krefftii":50,
    "Sycomistes butleri":50,
    "Toxotes chatareus":50 
}

model_filename = 'model.pb'
labels_filename = 'labels.txt'


def get_file_info(file_path):
    file_info = {}

    parts = file_path.split(os.sep)

    file_info['video_name'] = os.path.splitext(parts[-1])[0]
    file_info['location_name'] = parts[-2]
    file_info['transect_name'] = parts[-3]
    file_info['site_name'] = parts[-4]
    file_info['billabong_type'] = parts[-5]
    file_info['year'] = parts[-6]

    return file_info


def create_azure_storage_container(connect_str, container_name, blob_service_client):
    container = ContainerClient.from_connection_string(connect_str, container_name)

    try:
        container_properties = container.get_container_properties()
        container_client = blob_service_client.get_container_client(container_name)
        # Container exists. You can now use it.
        print(f"Container {container_name} already exists.")

    except Exception as e:
        # Container does not exist. You can now create it.
        container_client = blob_service_client.create_container(container_name)
        #print(e)
        print(f"Creating container {container_name}.")

    return container_client

def generate_container_sastoken(container_client):
    sas_token = generate_container_sas(
        container_client.account_name,
        container_client.container_name,
        account_key=container_client.credential.account_key,    
        permission=ContainerSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=730),
    )
    print('SAS token for the storage container ?{0}'.format(sas_token))

    return sas_token


def compute_show_predictions(results, np_image, frame_count, fps, min_probability, debug=False):
    species_counter = {}
    for prediction in results:
        if prediction['tagName'] not in thresholding_values:
            print ("WARNING: The Species name is not in threshold dictionary, probability is set to default")
            probability = min_probability
        else:
            probability = thresholding_values[prediction['tagName']]

        if (prediction['probability']*100) > probability:

            if prediction['tagName'] not in species_counter:
                species_counter[prediction['tagName']] = [{'time':round(frame_count/fps,3), 'probability':round(prediction['probability']*100,2)}]
            else:
                species_counter[prediction['tagName']].append({'time':round(frame_count/fps,3), 'probability':round(prediction['probability']*100,2)})
    return species_counter


def custom_vision_predictor(connect_str, model, blob_service_client, file_path, thresholding_values, predictions_per_sec=1, min_probability=50, debug=False):
    # Getting parameters from the path
   # predictor = CustomVisionPredictionClient(prediction_key, endpoint=endpoint)
    file_info = get_file_info(file_path)

    # Create azure storage container
    container_name = f"{file_info['year']}-{file_info['site_name']}-{file_info['transect_name']}-{file_info['location_name']}-{file_info['video_name']}".lower().replace(' ', '')
    container_client = create_azure_storage_container(connect_str, container_name, blob_service_client)
    sas_token = generate_container_sastoken(container_client)

    container_name_NoFish = 'nofish'
    noFishcontainer_client = create_azure_storage_container(connect_str, container_name_NoFish, blob_service_client)
    nofish_container_file_path = f"{file_info['year']}-{file_info['site_name']}-{file_info['transect_name']}-{file_info['video_name']}"

    # Split video into frames
    video_dir = os.path.join(file_info['year'], file_info['billabong_type'], file_info['site_name'], file_info['transect_name'],file_info['location_name']).replace(os.sep, '-').replace(' ', '-')

    starting_time = 0 # Seconds...

    video_capture = cv2.VideoCapture(file_path)

    num_of_frames = video_capture.get(cv2.CAP_PROP_FRAME_COUNT)

    fps = int(video_capture.get(cv2.CAP_PROP_FPS))

    if debug:
        print(f"Frames per second: {fps}")
        print(f"Total frame count: {video_capture.get(cv2.CAP_PROP_FRAME_COUNT)}")

    frame_count = int(starting_time * fps)

    video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_count)

    error_frame_count = 0

    # Analyse video frames and ran custom vision 
    while video_capture.isOpened():
        success, image = video_capture.read()

        if (frame_count % (fps//predictions_per_sec)) == 0:
            if success is False:
                print(f'Could not process frame: {frame_count} of {num_of_frames}')
                error_frame_count += 1
                frame_count += 1

                if frame_count == num_of_frames:
                    break
                else:
                    continue

            frame_name = '{0}_Frame-{1}.jpg'.format(video_dir, frame_count)

            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            buffer = io.BytesIO()
            Image.fromarray(image).save(buffer, format='JPEG')
            
            image = Image.fromarray(image)
            
            results = predict(model, image)

            species_counter = compute_show_predictions(results, image, frame_count, fps, min_probability, debug)

            if species_counter:
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=frame_name)
                blob_client.upload_blob(buffer.getvalue())
                if debug:
                    print('Uploading to fish container {0}...'.format(frame_name))

            else:
                if debug:
                    print('Uploading to nofish container {0}...'.format(frame_name))
                blob_client = blob_service_client.get_blob_client(container=container_name_NoFish , blob=nofish_container_file_path+'/' + frame_name)
                blob_client.upload_blob(buffer.getvalue())

        frame_count += 1

        if frame_count == num_of_frames:
            break

    video_capture.release()
    print(f"Total video frames:{num_of_frames}")
    print(f"Total frames to process: {num_of_frames/fps}")
    print(f"Total processed frames that errored: {error_frame_count}")


def main():
    
    with open('parameters.txt') as json_file:
        data = json.load(json_file)
        path = data['path']
        connect_str = data['connect_str']

    files = os.listdir(path)

    model = load_model(model_filename, labels_filename)

    for f in files:
        if os.path.splitext(f)[1] == '.mp4':

            # Create the BlobServiceClient object which will be used to create a container client
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            file_path = os.path.join(path, f)

            #If no species found in the dictionary, min probability is set to 15 
            custom_vision_predictor(connect_str, model, blob_service_client, file_path, thresholding_values, predictions_per_sec=1, min_probability=15, debug=False)

            
if __name__ == '__main__':
    main()
