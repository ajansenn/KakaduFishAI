
Install anaconda python
	make sure python.exe is is environemt variable path


Install requirements.txt
	azure-batch==6.0.0
	azure-storage-blob==1.4.0


https://github.com/conda/conda/issues/8273
error
 Can't connect to HTTPS URL because the SSL module is not available.

If PythonBatchTest_Lid_Py_R.py does not run at cmd prompt

try

My workaround:
I have copied the following files
libcrypto-1_1-x64.*
libssl-1_1-x64.*
from D:\Anaconda3\Library\bin to D:\Anaconda3\DLLs.