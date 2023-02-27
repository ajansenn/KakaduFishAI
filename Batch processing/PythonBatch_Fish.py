from __future__ import print_function
import datetime
import io
import os
import sys
import time
import config
import json

try:
    input = raw_input
except NameError:
    pass



# For local testing use 
import azure.storage.blob as azureblob
import azure.batch.batch_service_client as batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels

from azure.common.credentials import ServicePrincipalCredentials

# Es add for btch credetials for using managed image
#from azure.batch import BatchServiceClient
#from azure.common.credentials import ServicePrincipalCredentials



sys.path.append('.')
sys.path.append('..')

# Update the Batch and Storage account credential strings in config.py with values
# unique to your accounts. These are used when constructing connection strings
# for the Batch and Storage client objects.



def query_yes_no(question, default="yes"):
    """
    Prompts the user for yes/no input, displaying the specified question text.

    :param str question: The text of the prompt for input.
    :param str default: The default if the user hits <ENTER>. Acceptable values
    are 'yes', 'no', and None.
    :rtype: str
    :return: 'yes' or 'no' 
    """
    valid = {'y': 'yes', 'n': 'no'}
    if default is None:
        prompt = ' [y/n] '
    elif default == 'yes':
        prompt = ' [Y/n] '
    elif default == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError("Invalid default answer: '{}'".format(default))

    while 1:
        choice = input(question + prompt).lower()
        if default and not choice:
            return default
        try:
            return valid[choice[0]]
        except (KeyError, IndexError):
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def print_batch_exception(batch_exception):
    """
    Prints the contents of the specified Batch exception.

    :param batch_exception:
    """
    print('-------------------------------------------')
    print('Exception encountered:')
    if batch_exception.error and \
            batch_exception.error.message and \
            batch_exception.error.message.value:
        print(batch_exception.error.message.value)
        if batch_exception.error.values:
            print()
            for mesg in batch_exception.error.values:
                print('{}:\t{}'.format(mesg.key, mesg.value))
    print('-------------------------------------------')


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



def download_blob_from_container(block_blob_client, container_name, blob_name, directory_path):
    """
    Downloads specified blob from the specified Azure Blob storage container.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param container_name: The Azure Blob storage container from which to
        download file.
    :param blob_name: The name of blob to be downloaded
    :param directory_path: The local directory to which to download the file.
    """
    print('Downloading result file from container [{}]...'.format(
        container_name))

    destination_file_path = os.path.join(directory_path, blob_name)

    block_blob_client.get_blob_to_path(container_name, blob_name, destination_file_path)

    print('  Downloaded blob [{}] from container [{}] to {}'.format(
        blob_name, container_name, destination_file_path))

    print('  Download complete!')



def get_container_sas_token(block_blob_client,
                            container_name, blob_permissions):
    """
    Obtains a shared access signature granting the specified permissions to the
    container.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param str container_name: The name of the Azure Blob storage container.
    :param BlobPermissions blob_permissions:
    :rtype: str
    :return: A SAS token granting the specified permissions to the container.
    """
    # Obtain the SAS token for the container, setting the expiry time and
    # permissions. In this case, no start time is specified, so the shared
    # access signature becomes valid immediately. Expiration is in 2 hours.
    container_sas_token = \
        block_blob_client.generate_container_shared_access_signature(
            container_name,
            permission=blob_permissions,
            expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=2))

    return container_sas_token


def get_container_sas_url(block_blob_client,
                          container_name, blob_permissions):
    """
    Obtains a shared access signature URL that provides write access to the 
    ouput container to which the tasks will upload their output.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param str container_name: The name of the Azure Blob storage container.
    :param BlobPermissions blob_permissions:
    :rtype: str
    :return: A SAS URL granting the specified permissions to the container.
    """
    # Obtain the SAS token for the container.
    sas_token = get_container_sas_token(block_blob_client,
                                        container_name, azureblob.BlobPermissions.WRITE)

    # Construct SAS URL for the container
    container_sas_url = "https://{}.blob.core.windows.net/{}?{}".format(
        config._STORAGE_ACCOUNT_NAME, container_name, sas_token)

    return container_sas_url


def create_pool(batch_service_client, pool_id):
    """
    Creates a pool of compute nodes with the specified OS settings.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str pool_id: An ID for the new pool.
    :param str publisher: Marketplace image publisher
    :param str offer: Marketplace image offer
    :param str sku: Marketplace image sky
    """
    print('Creating pool [{}]...'.format(pool_id))

    # Create a new pool of Linux compute nodes using an Azure Virtual Machines
    # Marketplace image. For more information about creating pools of Linux
    # nodes, see:
    # https://azure.microsoft.com/documentation/articles/batch-linux-nodes/

    # The start task installs ffmpeg on each node from an available repository, using
    # an administrator user identity.


    # Specify Batch account credentials
    account = ""
    batch_url = ""
    ad_client_id = ""
    ad_tenant = ""
    ad_secret = ""

    # Pool settings
    pool_id =  pool_id                #"EsPool1"
    vm_size ="STANDARD_D4s_v3"          


    dedicated_node_count = 0
    low_priority_node_count = 1    #  dynamically set to location count
    
    # Initialize the Batch client
    creds = ServicePrincipalCredentials(
        client_id=ad_client_id,
        secret=ad_secret,
        tenant=ad_tenant,
        resource="https://batch.core.windows.net/"
    )
    client = batch.BatchServiceClient(creds, batch_url)

    # Create the unbound pool
    new_pool = batchmodels.PoolAddParameter(id=pool_id, vm_size=vm_size)
    #new_pool.target_dedicated = dedicated_node_count
    new_pool.target_low_priority_nodes=low_priority_node_count

    # Configure the start task for the pool
    start_task = batchmodels.StartTask(
        command_line="printenv AZ_BATCH_NODE_STARTUP_DIR"
    )
    start_task.run_elevated = True
    new_pool.start_task = start_task

    # Create an ImageReference which specifies the custom 
    # virtual machine image to install on the nodes.
    ir = batchmodels.ImageReference(
        # Environment production
        virtual_machine_image_id=""
        
    )

    # Create the VirtualMachineConfiguration, specifying
    # the VM image reference and the Batch node agent to
    # be installed on the node.
    vmc = batchmodels.VirtualMachineConfiguration(
        image_reference=ir,
        node_agent_sku_id="batch.node.windows amd64")     # 

    # Assign the virtual machine configuration to the pool
    new_pool.virtual_machine_configuration = vmc

    # Create pool in the Batch service
    client.pool.add(new_pool)


def create_job(batch_service_client, job_id, pool_id):
    """
    Creates a job with the specified ID, associated with the specified pool.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The ID for the job.
    :param str pool_id: The ID for the pool.
    """
    print('Creating job [{}]...'.format(job_id))

    job = batch.models.JobAddParameter(
        id=job_id,
        pool_info=batch.models.PoolInformation(pool_id=pool_id))

    batch_service_client.job.add(job)

 

    
def add_tasks_Fish(batch_service_client, job_id, resources, output_container_sas_url,index):
    """
    Adds a task for each input file in the collection to the specified job.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The ID of the job to which to add the tasks.
    :param list input_files: A collection of input files. One task will be
     created for each input file.
    :param output_container_sas_token: A SAS token granting write access to
    the specified Azure Blob storage container.
    """
  

    #print('Adding {} tasks to job [{}]...'.format(len(input_files), job_id))
    print('Adding {} tasks to job [{}]...'.format(len(resources), job_id))

    #las_tool_file_path = LasToolFile.file_path

    tasks = list()

    # Main Python run file
    #PythonExecute="ScoringImages_Channel_ae.py"
    PythonExecute="DownloadFilesToProcess.py"

    #  need to run cmd as admin 
    user = batchmodels.UserIdentity(
        auto_user=batchmodels.AutoUserSpecification(
            elevation_level=batchmodels.ElevationLevel.admin,
            scope=batchmodels.AutoUserScope.task))
    

    FileCreated='labels.txt'     #  Tidy later 
    tasks.append(batch.models.TaskAddParameter(
        id='Task{}'.format(index),
        user_identity=user ,
        resource_files=resources,
        output_files=[batchmodels.OutputFile(
            file_pattern=FileCreated,
            destination=batchmodels.OutputFileDestination(
                        container=batchmodels.OutputFileBlobContainerDestination(
                            container_url=output_container_sas_url)),
            upload_options=batchmodels.OutputFileUploadOptions(
                upload_condition=batchmodels.OutputFileUploadCondition.task_success))]
    )) 

    batch_service_client.task.add_collection(job_id, tasks)



#def create_resource_list(location_to_process):
#def create_resource_list(location_to_process,MODEL_LINK):     # Model not sent for channel scoring
def create_resource_list(location_to_process):


    # 1. Upload Parameter list
    #Parameter_List=upload_file_to_container(blob_client, input_container_name, _PARAMETER_LIST_PATH ) 
    #_PARAMETER_LIST_NAME = 'ParameterList.csv'
    _PARAMETER_RESOURCE_PATH = os.path.join('resources', 'parameters_batch.txt')
    with open(_PARAMETER_RESOURCE_PATH) as json_file:
        data = json.load(json_file)
        data['base_path'] = location_to_process
        with open(_PARAMETER_RESOURCE_PATH, 'w') as outfile:
            json.dump(data, outfile)

    # Upload modified parameters_batch.txt with Location to process
    PARAMETER_BATCH_LINK=upload_file_to_container(blob_client, input_container_name, _PARAMETER_RESOURCE_PATH ) 


    _PARAMETER_FISH_PATH = os.path.join('resources', 'parameters.txt')
    PARAMETER_FISH_LINK=upload_file_to_container(blob_client, input_container_name, _PARAMETER_FISH_PATH ) 

    # 2. Upload resource files
    _PARAMETER_RESOURCE_PATH = os.path.join('resources', 'labels.txt')
    LABELS_LINK=upload_file_to_container(blob_client, input_container_name, _PARAMETER_RESOURCE_PATH ) 


    # Temp Add hoc for slow upload connection
    #_PARAMETER_RESOURCE_PATH = os.path.join('resources', 'model.pb')
    #MODEL_LINK=upload_file_to_container(blob_client, input_container_name, _PARAMETER_RESOURCE_PATH ) 

    _PARAMETER_RESOURCE_PATH = os.path.join('resources', 'ScoringImages_Channel_ae.py')
    SCORING_IMAGES_LINK=upload_file_to_container(blob_client, input_container_name, _PARAMETER_RESOURCE_PATH ) 
    _PARAMETER_RESOURCE_PATH = os.path.join('resources', 'object_detection.py')
    OBJECT_DETECTION_LINK=upload_file_to_container(blob_client, input_container_name, _PARAMETER_RESOURCE_PATH ) 
    _PARAMETER_RESOURCE_PATH = os.path.join('resources', 'predict_v1.py')
    PREIDICT_V1_LINK=upload_file_to_container(blob_client, input_container_name, _PARAMETER_RESOURCE_PATH ) 

    _PARAMETER_RESOURCE_PATH = os.path.join('resources', 'DownloadFilesToProcess.py')
    DOWNLOAD_FILES_TOP_PROCESS=upload_file_to_container(blob_client, input_container_name, _PARAMETER_RESOURCE_PATH ) 
    


    # Create resource list
    resources = list()
    resources.append(PARAMETER_BATCH_LINK)
    resources.append(PARAMETER_FISH_LINK)

    resources.append(LABELS_LINK)
    #resources.append(MODEL_LINK)    # Model not sent for channel scoring
    resources.append(SCORING_IMAGES_LINK)
    resources.append(OBJECT_DETECTION_LINK)
    resources.append(PREIDICT_V1_LINK)

    resources.append(DOWNLOAD_FILES_TOP_PROCESS)

    return resources

def wait_for_tasks_to_complete(batch_service_client, job_id, timeout):
    """
    Returns when all tasks in the specified job reach the Completed state.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The id of the job whose tasks should be monitored.
    :param timedelta timeout: The duration to wait for task completion. If all
    tasks in the specified job do not reach Completed state within this time
    period, an exception will be raised.
    """
    timeout_expiration = datetime.datetime.now() + timeout

    print("Monitoring all tasks for 'Completed' state, timeout in {}..."
          .format(timeout), end='')

    while datetime.datetime.now() < timeout_expiration:
        print('.', end='')
        sys.stdout.flush()
        tasks = batch_service_client.task.list(job_id)

        incomplete_tasks = [task for task in tasks if
                            task.state != batchmodels.TaskState.completed]
        if not incomplete_tasks:
            print()
            return True
        else:
            time.sleep(1)

    print()
    raise RuntimeError("ERROR: Tasks did not reach 'Completed' state within "
                       "timeout period of " + str(timeout))


def generate_pool_name(file_path):
    file_info = {}

    parts = file_path.split(os.sep)

    '''
    file_info['video_name'] = os.path.splitext(parts[-1])[0]
    file_info['location_name'] = parts[-2]
    file_info['transect_name'] = parts[-3]
    file_info['site_name'] = parts[-4]
    
    file_info['year'] = parts[-6]
    '''
    file_info['billabong_name'] = parts[-3]
    file_info['transect_name'] = parts[-2]
    file_info['location_name'] = parts[-1]
        
    pool_name="pool" + file_info['billabong_name'].replace(" ","") + file_info['transect_name'].replace(" ","") + file_info['location_name'].replace(" ","")
  


    return pool_name

if __name__ == '__main__':





    start_time = datetime.datetime.now().replace(microsecond=0)
    print('Sample start: {}'.format(start_time))
    print()




    base_string='\\2020 Channel Billabong\\Sandy Billabong\\Transect 1\\Location 1'
    #base_string=sys.argv[1]
    print(base_string)

    # Create unique Pool name
    pool_name = generate_pool_name(base_string)
    print(pool_name)


    #create_pool_bool =sys.argv[3]
    create_pool_bool="TRUE"
    print(create_pool_bool)


    # Create the blob client, for use in obtaining references to
    # blob storage containers and uploading files to containers.

    blob_client = azureblob.BlockBlobService(
        account_name=config._STORAGE_ACCOUNT_NAME,
        account_key=config._STORAGE_ACCOUNT_KEY)

        

    # Use the blob client to create the containers in Azure Storage if they
    # don't yet exist.



    input_container_name = 'input' + pool_name.lower()        # Must be lower case
    output_container_name = 'output' + pool_name.lower()


    #  NOTE - This container is for input files - 
    print("create container")
    blob_client.create_container(input_container_name, fail_on_exist=False)
    blob_client.create_container(output_container_name, fail_on_exist=False)
    print('Container [{}] created.'.format(input_container_name))
    print('Container [{}] created.'.format(output_container_name))

    print("create container  - end ")


    # Link to output container - URL
    output_container_sas_url = get_container_sas_url(
        blob_client,
        output_container_name,
        azureblob.BlobPermissions.WRITE)


    # Create a Batch service client. We'll now be interacting with the Batch
    # service in addition to Storage
    ##credentials = batchauth.SharedKeyCredentials(config._BATCH_ACCOUNT_NAME,
    ##                                             config._BATCH_ACCOUNT_KEY)



    # refer            - https://docs.microsoft.com/en-au/azure/batch/batch-aad-auth  
    # Service principle required to create VM from custom image                                
    credentials = ServicePrincipalCredentials(
        client_id="",
        secret="",
        tenant="",
        resource=""
    )



    # Create batch client and get URL link 
    batch_client = batch.BatchServiceClient(
        credentials,
        batch_url=config._BATCH_ACCOUNT_URL)




    EsJob_Fish=""

    try:
        # Create the pool that will contain the compute nodes that will execute the
        # tasks.
        if create_pool_bool == "TRUE":    
            create_pool(batch_client, pool_name)
 

        # Create the job that will run the tasks.
        EsJob_Fish= "EsJob_Fish" + pool_name.lower()        # Must be lower case
        create_job(batch_client, EsJob_Fish, pool_name)

        resources=create_resource_list(base_string)



        # Add the tasks to the job. Pass the input files and a SAS URL
        # to the storage container for output files.
        add_tasks_Fish(batch_client, EsJob_Fish,
                  resources, output_container_sas_url,1)     # Note output not used
 

        # Pause execution until tasks reach Completed state.
        timeout=5000 # about 3 days
        wait_for_tasks_to_complete(batch_client,
                                   EsJob_Fish,
                                   datetime.timedelta(minutes=timeout))

        print("  Success! All tasks reached the 'Completed' state within the "
              "specified timeout period.")




    except batchmodels.BatchErrorException as err:
        print_batch_exception(err)

        # Delete any creates resources.
        # check if error if it does not exist


        
        #Delete jobs created
        batch_client.job.delete(EsJob_Fish)

        #  Delete pool created
        batch_client.pool.delete(pool_name)

        #  Delete storage created
        blob_client.delete_container(input_container_name)
        blob_client.delete_container(output_container_name)
        
        raise



    # Print out some timing info
    end_time = datetime.datetime.now().replace(microsecond=0)
    print()
    print('Sample end: {}'.format(end_time))
    print('Elapsed time: {}'.format(end_time - start_time))
    print()


    print("Deleting Pool/Job/Temp storage")
    batch_client.job.delete(EsJob_Fish)
    batch_client.pool.delete(pool_name)
    blob_client.delete_container(input_container_name)
    blob_client.delete_container(output_container_name)



    print()
    input('Press ENTER to exit...')
