Python script used for regridding the datasets as in Dumolin et al. 2019.

<b>Usage</b>:

```ReGrid.py  FullMS_directory Output_directory```

where <i>FullMS_directory</i> is the name of a directory containing .txt files of raw mass spectra. 
Each text file should have two tab-spearated columns without headers. 
First column is the m/z value and second column the intensity value as in the example below:

#m/z  int  
1998.75 686  
1999.17 603  
1999.59 640  
2000.00 599  

<b>Output</b>:  
Output is stored in the Output_directory. The directory contains the regridded file for each spectrum (1 file per spectrum).

<b>Requirements</b>:
- Python v3.7
- Pandas v0.23.3
- Numpy v1.15.0



