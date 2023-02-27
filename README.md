## KakaduFishAI

Fish monitoring programs designed to detect and assess potential impacts associated with mining in the Alligators Rivers Region (ARR), Northern Australia, were developed and implemented by the Supervising Scientist Branch in the late 1980s. Fish community structure metrics from recessional flow/early dry season sampling are used to detect potential long-term ecosystem level responses by comparing data gathered from downstream of mine sites to historical data and data from control streams unaffected by mining. 

![Bubble Boat](https://github.com/ajansenn/KakaduFishAI/blob/main/Edith%20Falls%20-%20Bubble%20boat.jpg)

Since the inception of these programs advances in technology and the decline of associated costs has allowed for innovation and implementation of new practices using underwater video cameras. Such innovations are necessary to improve worker safety through reduced contact with waters (e.g. crocodiles) and increase replication through efficiencies in data collection. 

![Camera](https://github.com/ajansenn/KakaduFishAI/blob/main/Edith%20Falls%20-%20Surface%20Deployed%20Camera.jpg)

However, efficiencies in data collection do not always translate to efficiencies in data processing, with significant volumes of videography processing required by a trained technician. 

Advances in artificial intelligence algorithms now provide the platform to automate this processing using Deep Learning.

This repository demonstrates how we developed a training dataset and deep learning model for automating fish identification in underwater video and provides the framework for any fisheries scientist to adapt their monitoring program using the same techniques. 

### Access the data

This dataset can be accessed on [Zenodo](https://zenodo.org/record/7250921#.Y_w4tMJBzl0). It consists of 44,412 images in .jpg format with 82,904 bounding box annotations for 23 freshwater fish species. The annotations are in COCO format.

### Setting up your desktop

Follow the steps below to install this repository on your dekstop.

* Install [Azure Storage Explorer](https://azure.microsoft.com/en-us/features/storage-explorer/)
* Install [Anaconda](https://repo.anaconda.com/archive/Anaconda3-2019.10-Windows-x86_64.exe)
  * Choose All Users
* Install [Git Desktop](https://desktop.github.com/)
* Open Git Desktop and clone https://github.com/ajansenn/KakaduFishAI.git
* Open Anaconda Prompt, cd to folder with cloned repository and [create conda environment](https://docs.microsoft.com/en-us/azure/machine-learning/service/how-to-configure-environment#local) using the code below:
```
conda env create -f environment.yml
conda env list
conda activate KakaduFishAI
conda install notebook ipykernel
ipython kernel install --user
```

### Videos to CustomVision.ai

Images are required to annotate, label and train a deep learning model. Images are best source from real-world conditions that mirror the test conditions the model will be applied to, and are often videos from Remote Underwater Video (RUV) or Baited Remote Underwater Video (BRUV) deployments. To extract images from video and upload to a Azure Custom Vision for labelling perform the following: 

CustomVision.ai in Microsoft Azure is used for image labeling and model training. 

* Create a [CustomVision.ai project](https://docs.microsoft.com/en-us/azure/cognitive-services/custom-vision-service/get-started-build-detector)

Ensure your project type is Object Detector and Domain type is General. This project used a historical collection of videos (~500 1 hour videos, 2016-2019) that were uploaded into the CustomVision.ai project folder. Frames were extracted from video using the jupyter notebook titled Extract Frames from Video. 

To link the notebook to your CustomVision.ai project, open a text file on your desktop, copy and paste the credentials below and save as a .env file:
```
CUSTOM_VISION_PROJECT_ID=<this is found in the settings for your azure subsription>
CUSTOM_VISION_TRAINING_KEY=<this is found in the settings for your azure subsription>
STORAGE_ACCOUNT_NAME=<your azure subscription storage account name to store images>
STORAGE_ACCOUNT_KEY=<Storage account key found in azure settings>
 ```
Store this .env file in the notebooks section of the GitHub repository folder on your desktop. Then open your anaconda command prompt and enter the following:

* Change directory to KakaduFish:
```
cd KakaduFish
```
* Start the [Jupyter Notebook app](https://jupyter-notebook-beginner-guide.readthedocs.io/en/latest/execute.html):
```
jupyter notebook
```
* Navigate to the notebooks section and open the Extract Frames from Video notebook.

* Adjust the starting time to reflect the desired time from the beginning of each video file you want to begin extracting frames. If your video begins when the camera is turned on in the boat you can eliminate these frames from being uploaded into the project folder.
```
starting_time = <enter starting time in seconds>
```
* Provide the path details for a folder where the videos intended to upload are stored. This can be on the desktop, cloud storage or external hard-drive. 
```
video_path = <C:\\>
```
* Run the remainder of the notebook. Frames will be extracted from the videos and uploaded in batches of 64. You can observe the frames as they are uploaded to the CutomVision.ai project folder. 



### CustomVision.ai Image Labeling 

To train an effective deep learning model significant volumes of training material that is representative of test scenarios is required. For this computer vision project, we targeted the following taxa found in deep channel and shallow lowland billabongs from Kakadu National Park, Northern Territory Australia:

```
Ambassis agrammus
Ambassis macleayi
Amniataba percoides
Craterocephalus stercusmuscarum
Denariusa australis
Glossamia aprion
Glossogobius spp.
Hephaestus fuliginosus
Lates calcarifer
Leiopotherapon unicolor
Liza ordensis
Megalops cyprinoides
Melanotaenia nigrans
Melanotaenia splendida inornata
Mogurnda mogurnda
Nemetalosa erebi
Neoarius spp.
Neosilurus spp.
Oxyeleotris spp.
Scleropages jardinii
Strongylura kreffti
Syncomistes butleri
Toxotes chatareus
```

Bounding boxes were placed around all fish that a trained fish ecologist could confidently identify to species level from a still image. Labelling guidelines for fish are defined at [BRUVNet](https://github.com/ajansenn/BRUVNet). 

![Toxotes chatareus](https://github.com/ajansenn/KakaduFishAI/blob/main/Toxotes%20chatareus.JPG)


The quick train function in CustomVision.ai was used throughout the labeling process to infer the success of our labeling strategy and inform which species to prioritise. 

### Model training

To train deep learning models navigate to the Train button from the Custom Vision portal. Advanced training runs were used for this project with the maximum training time (96 hours). 

### Monitor training trends

To observe the performance of each fish taxa between training runs the mean Average Precision (mAP), Precision and Recall is plotted. This is useful for observing the effect additional training data has on perdictive performance.

* Navigate to the notebooks section and open the CustomVision.ai Project Trend notebook.

Enter you project keys and run notebook to plot data. 

### Using the fish identification model

* Score videos: use this notebook to create a video with bounding box mask predictions overlayed. This is useful for communicating results and interpreting model predictions over a sequence of frames. 

* Filter frames Yes Fish/No Fish: use the Scoring Frames from Video notebook to filter frames with and without fish present and save images into an Azure blob storage account. It uses the Custom Vision. This is useful for 'finding' fish in videos for image annotation. 

* Compact model scoring:
    * Parameter.txt - enter the file location of videos on your desktop and provide the connection string for your azure blob storage account
    * ScoringImages.py - run the scoring images python file to use the compact model to make predictions on your videos. Check the file_path requirements/structure required or adapt to your workflow. 

* Processing of multiple videos simultaenously in the cloud was achieved using [Microsofts Azure Batch](https://azure.microsoft.com/en-au/products/batch/) service. For information related to the setup and configuration of a batch account follow the documentation in the provided link. All code used for this project is available in the Batch Processing folder. 

### Additional notebooks 


* Convert Pawsey to Custom Vision: use this script to import the [OzFish](https://data.pawsey.org.au/public/?path=/FDFML/crops) dataset to Custom Vision. 
* Convert VIA to CustomVision.ai: Use this notebook to convert annotations made use the [VIA](https://www.robots.ox.ac.uk/~vgg/software/via/via.html) annotation tool. 

  
  ### Contact
  
  For more details contact:
  
* [Andrew Jansen](mailto:andrew.jansen@dcceew.gov.au) (Supervising Scientist, Department of Climate Change, Energy, Environment and Water)
* [Steve van Bodegraven](mailto:Steve.VanBodegraven@ForBetterAI.onmicrosoft.com) (Microsoft)
* Andrew Esparon (Supervising Scientist, Department of Climate Change, Energy, Environment and Water)
* Varma Gadhiraju (Microsoft, Australia)
* Kris Bock (Microsoft, Australia)
  
  ### License
  
  This repository is licensed with the [MIT license](https://github.com/Microsoft/dotnet/blob/master/LICENSE).
  The training dataset and model are licensed with [Creative Commons license CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
