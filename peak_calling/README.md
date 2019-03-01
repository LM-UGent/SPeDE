R script used for peak calling on the benchmarking dataset as in Dumolin et al. 2019.

<b>Usage</b>:

$ Rscript peak_calling_cwt.R <FullMS>  
where <FullMS> is the name of a directory containing .txt files of quality filtered, raw mass spectra. 
Each text file should have two tab-spearated columns without headers. 
First column is the m/z value and second column the intensity value as in the example below:

#m/z  int  
1998.75 686  
1999.17 603  
1999.59 640  
2000.00 599  

<b>Output</b>:  
Output is stored in the PKL4DICE directory. The directory contains the peak lists for each spectrum as called by the MassSpectWavelet package
(1 file per spectrum).

<b>Requirements</b>:
- Rscript version 3.4.4 or newer (not tested on older versions)
- MassSpecWavelet package version 1.48.1, available from Bioconductor (Du et al. 2006)

References:
Du P, Kibbe WA, Lin SM (2006). “Improved peak detection in mass spectrum by incorporating continuous wavelet transform-based pattern matching.” Bioinformatics, 22, 2059-2065.
