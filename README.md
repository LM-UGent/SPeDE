# SPeDE: SPectral DEreplication

# Quick guide

## Requirements

- Python v3.7
- Pandas v0.23.3
- Numpy v1.15.0
- Numba v0.39.0
- PyQt5 v5.11.2
- PyYAML v3.13



## Command driven processing (Windows and Linux supported, MacOS unknown)

**This program can't be run on a Linux subsystem in Windows.**

1. Clone or download the Spectrum_Processing map onto your pc.
2. Start the processing with the following command:  
``python SPeDE.py <Path\to\ppmc_interval_index.csv> <Project_directory> <Output_directory> [-d <density>] [-c <cluster>] [-l <local>] [-m <cutoff>] [ -o <output_format>\] [-p <peak-count>] [-n <name>] [-q <validation_name>] [-v] [-e]``


## Graphical processing (Windows and Linux)

1. Clone or download the Spectrum\_Processing and GUI map to your pc into the same folder.
2. Start the graphical interface by opening _GSPeDE.py_.
3. Select the correct parameters.
4. Start processing by clicking _Start_. 
5. The results will be put in the specified output folder.


# Introduction

*SPeDe* is a program that is used to dereplicate large sets of MALDI-TOF MS spectra. The analysis consist of screening the dataset for  spectra with unique spectral features and outputs the reduced set of selected reference spectra. Spectra not assigned as a refererence  are matched according to their matching reference spectra. 

The program allows you to perform the  "on the fly" dereplicate process of MALDI-TOF MS spectra and summarizes them into unique references and matching spectra.


The output will be written to a specified folder.

The program takes a file containing peak interval boundaries, a directory containing all data and 
an output directory in which it places its output. The output always consists of a reference list and optionally also 
includes a file containing the uniqueness matrix, a krona output file and copies the extracted references to a subfolder.



# Command driven processing
First an overview of the command line program.

## Input
### Required inputs
1. ``intervals``: A path to the *ppmc_interval_index.csv* file.
2. ``project_directory``: A path to the directory containing all PKL and FMS files.  
These files all have to be in the same folder.
3. ``output_directory``: The path to a folder to which the program writes its output.

### Optional inputs
1. ``-d density``: The PPM threshold, default 700.
2. ``-c cluster``: The PPVM cluster threshold in percentage, default 75.
3. ``-l local``: The PPMC local threshold in percentage, default 50.
4. ``-m cutoff``: The S/N cutoff in M/Z, default 30.
5. ``-o output format``: Output format of the reference list output file, default csv.   
CSV is currently also the only option.
6. ``-v output validate``: Print the validation data to an output file _data_validation.csv_, default false.
7. ``-p peak count threshold``: Peaks with an S/N value >30 are counted. If the amount of such peaks in one spectrum 
is greater or equal to the peak count threshold, the spectrum is eligible to be a reference spectrum, default 5.
8. ``-n output name``: The name of the reference list output file. Extension must match output format, default <current_time_>SPeDE_output.csv.
9. ``-q validation name``: The name of the data validation matrix. This must be a .csv file, default <current_time_>data_validation.csv.
10. ``-e copy files``: Copy the resulting unique reference files to a subfolder, default false.
11. ``-k krona output``: Generate a [krona][krona_website] txt file, ready to be processed by the krona software.

## Output
The program places all of its output into the folder specified by ``output_directory``. Every run produces a reference list named <current_time_>SPeDE_output.csv 
or ``-n`` whenever this option is used. 

Optionally, when the ``-v`` flag is set, the program will also output a validation matrix named 
validation_matrix.csv or ``-q`` whenever this option is used. 
This matrix is the uniqueness matrix of the spectra in the project directory.  

When the ``-e`` flag is set, all spectra files that are marked as references will be copied to a subfolder 
References in the output folder.

When the ``-k`` flag is set, a txt file will be generated which is ready to be processed by the [krona software][krona_website].


# Graphical Processing
Now, the GUI will be covered.

## Overview

![Gui overview][GSPeDe_tutorial]

The GUI exists out of 2 major parts: 
An upper part, which is the variable part, and a lower part which default values and optional inputs.
 
In the lower part you can distinguish the following sections: configuration IO, default values, 
key buttons and additional processing options. 

See _Setup_ for first time use.

## Required inputs
All inputs in the upper part of the screen are mandatory.
1. ``Project directory``: Location of your project with PKL and FMS files. 
The files should be directly contained in the project directory.
2. ``Output directory``: Folder for the output files.

Both files can be selected using their respective picker buttons.

## Default inputs
1. ``Output type``: Currently only CSV is supported.
2. ``Density``: The PPM threshold, default 700.
3. ``Cluster``: The PPVM cluster threshold in percentage, default 75.
4. ``Local``: The PPMC local threshold in percentage, default 50.
5. ``Cutoff``: The S/N cutoff in M/Z, default 30.
6. ``Intervals``: Path to the _ppmc_interval_index.csv_ file. 
This file can also be selected with the picker button to the right of the input field.

These values (except for output type) can only be edited when the _Default values_ checkbox is unchecked. 
Checking this box will also reset the default inputs.

## Configuration IO

The _Load config_ and _Store config_ button allows you to store all required and default values (except output type) to a .yaml file.
At any time, a config file can be loaded and its values will be loaded into the GUI.

At startup, the file _default_config.yaml_ is always loaded if present.


## Key buttons
Pressing the _Start_  button will initiate the processing of the spectra. All input values 
will be checked for legitimacy. A pop-up window will inform you about any progress.

You are able to abort the processing in the pop-up window, but beware that any progress will be lost.

The _Exit_ button will exit the program after a confirmation prompt.

## Setup

When installing _SPeDE_, you have to point the program towards the _ppmc_interval_index.csv_ file. 

1. Uncheck the _Default values_ checkbox.
2. Use the file picker right of the _Intervals_ input field to select the ppmc file.  
    It is located in 
``<installation_location>/pkgs/GUI/ppmc_interval_index.csv``
3. Leave _Project directory_ and _Output directory_ blanc.
4. Click on _Store Config_.
5. Continue to save when given a warning.
5. Overwrite the _default_config.yaml_ file.
6. Now, when you start _GSPeDE_, the intervals will be loaded automatically.

## Additional options

The _Default values_ checkbox resets the values in the input fields when checked.  
The _Validation matrix_ checkbox enables the output of a uniqueness matrix. This matrix 
is also written into the output directory under the name _validation_matrix.csv_.  
The _Copy unique references_ checkbox defines whether or not the resulting unique references should be copied to 
a subfolder in the output folder.  
The _Krona output_ checkbox define whethere or not you want to generate a krona output txt file.

# Documentation
Made using [Sphinx][sphinx_website]. Sphinx can be setup with [sphinx-autostart][sphinx-autostart].

All documentation files are located in the _Documentation_ folder.
Sphinx uses ``.rst`` files to feed to its autodoc software. These files can be generated with [sphinx-apidoc][sphinx-apidoc-website].
The functions to be documented can be edited inside an rst file.
Gather all rst files in the source folder and execute the [sphinx-build][sphinx-build-website] software to generate documentation.


# Installer
Made using [pynsist][pynsist_website].

The main file is _installer.cfg_, located in the main project folder. Note that this folder has to be in the most upper 
level of the project to function correctly since it must be able to access any package top-level.  
Be sure to remove all files that don't need to be included in the installer.  
Additional information about the config file can be found at [their website][pynist-config].

Beware that all dependencies of the program have to be listed in the _installer.cfg_ file, not only the ones listed by 
pipreqs.

# Troubleshooting


Any unknown error will be written to _err.txt_, which is located in the directory of the GSPeDE file. 
Consult this file for more information about errors.

[GSPeDe_tutorial]: ./Documentation/GSPeDE_tutorial.JPG
[pynsist_website]: https://pynsist.readthedocs.io/en/latest/
[pynist-config]: https://pynsist.readthedocs.io/en/latest/cfgfile.html
[sphinx_website]: http://www.sphinx-doc.org/en/master/
[sphinx-apidoc-website]: http://www.sphinx-doc.org/en/master/man/sphinx-apidoc.html
[sphinx-build-website]: http://www.sphinx-doc.org/en/master/man/sphinx-build.html
[sphinx-autostart]: http://www.sphinx-doc.org/en/master/man/sphinx-quickstart.html
[krona_website]: https://github.com/marbl/Krona/tree/master/KronaTools
