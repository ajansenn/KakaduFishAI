
import os
import json
#import azure.storage.blob as azureblob
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient    #, BlockBlobService, PublicAccess

# azure.storage.blob V12 notes
#https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python



def download_blob_from_container(connection_string, container_path, directory_path ,blob_name):
    """
    Downloads specified blob from the specified Azure Blob storage container to local directory.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param container_name: The Azure Blob storage container from which to
        download file.
    :param blob_name: The name of blob to be downloaded
    :param directory_path: The local directory to which to download the file.
    """
    print('Downloading file [{}]...'.format(blob_name))

    destination_file_path = os.path.join(directory_path, blob_name)
    # Update method - this method for azure-staorage 1.4 - Modded for version 12.3.2
    #block_blob_client.get_blob_to_path(container_name, blob_name, destination_file_path)


    container_path=container_path.replace("\\","/")
    container_path=container_path.replace("//","/")   # Ad hoc fix - tidy later - sometimes formal\\ sometimes \\\\ - check and fix

    blob = BlobClient.from_connection_string( conn_str=connection_string, container_name=container_path, blob_name=blob_name)
    with open(destination_file_path, "wb") as my_blob:
        my_blob.write(blob.download_blob().readall())

    print('  Downloaded blob [{}] from container [{}] to {}'.format(
        blob_name, container_path, destination_file_path))

    print('  Download complete!')




def upload_file_to_container(block_blob_client, container_name, file_path):
    """
    Uploads a local file to an Azure Blob storage container.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param str container_name: The name of the Azure Blob storage container.
    :param str file_path: The local path to the file.
    :rtype: `azure.batch.models.ResourceFile`
    :return: A ResourceFile initialized with a SAS URL appropriate for Batch
    tasks.
    """
    blob_name = os.path.basename(file_path)

    print('Uploading file {} to container [{}]...'.format(file_path,
                                                          container_name))

    block_blob_client.create_blob_from_path(container_name,
                                            blob_name,
                                            file_path)

    # Obtain the SAS token for the container.
    sas_token = get_container_sas_token(block_blob_client,
                                        container_name, azureblob.BlobPermissions.READ)

    sas_url = block_blob_client.make_blob_url(container_name,
                                              blob_name,
                                              sas_token=sas_token)

    return batchmodels.ResourceFile(file_path=blob_name,
                                    http_url=sas_url)


def get__existing_resource_file(block_blob_client, container_name, file_path):
    sas_token = get_container_sas_token(block_blob_client,container_name, azureblob.BlobPermissions.READ)

    #blob_name1 = "Strips_Voxel_2cm_Merge.las"  # output from step 2 merge
    blob_name = os.path.basename(file_path)

    sas_url = blob_client.make_blob_url(container_name,
                                              blob_name,
                                              sas_token=sas_token)

    return batchmodels.ResourceFile(file_path=blob_name,
                                        http_url=sas_url)



def run_sample(local_path):
    container_name ='fishvideography'

    # Create the BlobServiceClient object which will be used to create a container client
    connect_str="<insert key here>"
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

    # Create a unique name for the container
    container_name ='fishvideography'

    # Create the container
    #container_client = blob_service_client.create_container(container_name)



    path_remove = "C:\\2020"
    #local_path = "C:\\2020\\2020 Channel Billabong\\Mudginberri Billabong\\Transect 1\\Location 2\\outputs"
    

    for r,d,f in os.walk(local_path):        
        if f:
            for file in f:
                file_path_on_azure = r.replace(path_remove,"")   # remove start
                file_path_on_azure = file_path_on_azure.replace("\\outputs","")   # remove outputs
                file_path_on_azure="fishvideography" + file_path_on_azure
                file_path_on_local = os.path.join(r,file)
                #block_blob_service.create_blob_from_path(container_name,file_path_on_azure,file_path_on_local)  

                # Create a blob client using the local file name as the name for the blob
                blob_client = blob_service_client.get_blob_client(container=file_path_on_azure, blob=file)
                # Upload the created file
                with open(file_path_on_local, "rb") as data:
                    blob_client.upload_blob(data)

         


def main():



    with open('parameters_batch.txt') as json_file:
        data = json.load(json_file)
        base_path= data['base_path']
        container_name_input= data['container_name_input']
        connection_string_input= data['connection_string_input']
        connection_string_output= data['connection_string_output']
        


    directory_path='C:' + '\\2020\\' + base_path
    container_path=container_name_input + "\\" + base_path




    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


    # Dynamically create parameters.txt used by ScoringImages_ae.py
    data = {}
    data['path'] = directory_path
    data['connect_str'] = connection_string_output


    with open('parameters.txt', 'w') as outfile:
        json.dump(data, outfile)




    blob_service_client = BlobServiceClient.from_connection_string(connection_string_input)
    

    container_client = blob_service_client.get_container_client('fishvideography') 
    print("\nListing blobs...")


    # Test - only process one file
    #FileCount=0

    # List the blobs in the container
    blob_list = container_client.list_blobs()
    # add hoc check - Check   - Each node will process 1 location (5-6 files)
    substring=base_path.replace("\\","/")
    substring=substring.replace("//","/")   
    substring=substring + "/"   
    substring=substring[1:]  
    for blob in blob_list:
        print("\t" + blob.name)

        if blob.name.find(substring) != -1:
            print ("Found!")
            
            blob_name=os.path.basename(blob.name)
        #    if FileCount==0:
                # copy from Container to local drive for storage
            download_blob_from_container(connection_string_input, container_path, directory_path ,blob_name)
            #FileCount=1
        #else:
        #    print ("Not found!")



    #  Score images using MS computer vision model
    import ScoringImages_Channel_ae
    ScoringImages_Channel_ae.main()

    
    # Copy outputs back to storage container
    print("Upload results to blog storage")
    local_path = directory_path + "\\outputs"    
    run_sample(local_path)
    print("Upload complete")


if __name__ == '__main__':
    main()

