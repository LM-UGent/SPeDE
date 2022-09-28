import concurrent.futures
import csv
import os
from enum import Enum

import numba as nb
import numpy as np
import pandas as pd


class FileProvider:

    def __init__(self, intervals_filename, project_directory, orange_threshold):
        """
        Construct a file provider that parses and provides input files.

        :param intervals_filename: The filename of the file containing all intervals.
        :type intervals_filename: str
        :param project_directory: The path to the directory containing the FMS and PKL files.
        :type project_directory: str
        :param orange_threshold: The maximum value of peakcountB for a spectrum to be categorized as orange and to be discarded for clustering.
        :type orange_threshold: int
        """

        self.intervals_filename=None
        self.orange_threshold=orange_threshold
        self.proj_path=None
        self.green_filenames=None
        self.orange_filenames=None
        self.red_filenames=None
        self.intervals=None
        self.green_fms_files=None
        self.orange_fms_files=None
        self.green_pkl_files=None
        self.orange_pkl_files=None
        self.qualities=None
        self.filenames=None

        self.pkl_files_length=None


        self.intervals_filename = intervals_filename
        self.proj_path=project_directory

        # The filenames are the names of the files without the PKL_ or ReGrid_ prefix.
        # Remove duplicate names by converting the namelist to a set, sort the list for consistent output
        self.filenames= [x for x in os.listdir(project_directory) if x[:4]=="PKL_"]
        self.filenames = np.array(sorted(list(set([fms_filename[-24:] for fms_filename in self.filenames]))))
        # Read all fms and pkl files in parallel and filter between Green and Orange qualities
        print("Sys: Reading and preprocessing PKL files...")
        with concurrent.futures.ProcessPoolExecutor() as executor:
            res= list((executor.map(self.parse_pkl_file, self.filenames)))
            pkl_files = np.array([x[0] for x in res], dtype=object)
            self.qualities=np.array([x[1] for x in res])
            self.green_filenames=self.filenames[self.qualities==Quality.GREEN]
            self.orange_filenames=self.filenames[self.qualities==Quality.ORANGE]
            self.red_filenames=self.filenames[self.qualities==Quality.RED]
            self.green_pkl_files=pkl_files[self.qualities==Quality.GREEN]
            self.orange_pkl_files=pkl_files[self.qualities==Quality.ORANGE]

            print("Sys: Reading FMS files...")
            self.green_fms_files= np.array(list(executor.map(self.parse_fms_file, self.green_filenames)))
            self.orange_fms_files= np.array(list(executor.map(self.parse_fms_file, self.orange_filenames)))


        #if there is no good data, abort
        if len(self.green_filenames)==0:
            raise DataMissing()


        print("Sys: Reading interval list...")
        self.intervals = self._parse_intervals()
        # Each peak list file may have a different number of peaks. But we want to store all peak files in one uniform
        # Numpy array.. Thus, we resize each array to the length of the largest and keep track of their original length.
        # Save the original lengths
        self.pkl_files_length = [nb.int32(pkl_file.shape[0]) for pkl_file in self.green_pkl_files]
        maximum_pkl_length = max(self.pkl_files_length) # Save the maximum value
        self.green_pkl_files = np.array([np.resize(pkl_file, (maximum_pkl_length, 2)) for pkl_file in self.green_pkl_files])
        # an array for which each element contains the contents of a pkl file (which is an N X 2 array, N being the amount of peaks in the file)

    def _parse_intervals(self):
        """Return a Numpy array that contains M/Z values with boundary indices.

        :return: A Numpy array in which the first index denotes an M/Z value. The second and third values are the indices in an FMS file for which that index gives you the interval start, respectively end value.
        """
        # Create a dict that maps an M/Z value to the index of that M/Z value in the FMS file
        with open(os.path.join(self.proj_path, 'ReGrid_' + self.green_filenames[0])) as fms_file:
            fms_reader = csv.reader(fms_file, delimiter='\t')
            next(fms_reader)

            mz_to_indices = dict((float(mz), i) for i, (mz, _) in enumerate(fms_reader))
            fms_file.close()


        intervals = pd.read_csv(self.intervals_filename, sep=';').values
        intervals[:, 1] = np.vectorize(mz_to_indices.__getitem__)(intervals[:, 1])
        intervals[:, 2] = np.vectorize(mz_to_indices.__getitem__)(intervals[:, 2])
        return intervals

    def parse_fms_file(self, filename):
        """Parse the specified FMS file and return its content as a Numpy array.

        Note that the M/Z values are missing. Since these are the same for every file, the M/Z-values can act as
        indices and are not needed separately.

        :param filename: The name of the FMS file located in the directory `proj_path` without the prefix 'ReGrid_'.
        :type filename: str
        :return: A one-dimensional Numpy array where each entry denotes the S/N value measured at a specific location.
        """
        return pd.read_csv(os.path.join(self.proj_path, 'ReGrid_' + filename), sep='\t', usecols=(1,)).values[:, 0].astype(np.int32)

    def parse_pkl_file(self, filename):
        """Parse the specified peak list file and return its content as a Numpy array.

        :param filename: The name of the PKL file located in the directory `proj_path` without the prefix 'PKL_'.
        :type filename: str
        :return: An N x 2 Numpy array where the first column is the location of a peak and the second is its S/N value.
        """
        peaks = pd.read_csv(os.path.join(self.proj_path, 'PKL_' + filename), sep='\t', usecols=(0, 1)).values
        # peaks= N x 2 Numpy array where the first column is the location of a peak and the second is its S/N value

        #cut the start from the spectra: >=2100

        processed_list, spectrum_quality= self.preprocess_pkl_list(peaks)

        return processed_list, spectrum_quality

    def preprocess_pkl_list(self, pkl_list):
        """Return the preprocessed pkl_list if its quality is not red and the quality itself.

        This function removes leading entries with M/Z value <2100.
        The pkl_list's quality is assessed according to MOIDePuS instructions.

        :param pkl_list: the array to be manipulated.
        :type pkl_list: array
        :return: A tuple of the preprocessed list and an enum denoting the quality of the pkl_list. If the quality is not red, the array's S/N values will be converted to quality enums.
        """

        # Remove M/Z values <2100
        # Find index of first value >=2100 and remove leading entries

        processed_list=None
        for index, value in enumerate(pkl_list[:,0]):
            if value>=2100:
                processed_list=pkl_list[index:,:]
                break
        if processed_list is None:
            return pkl_list, Quality.RED


        # Categorize all peaks as red (bad), orange (average) or green (good)
        quality_array= np.ones(len(processed_list))

        #count the good peaks
        green_indices=(processed_list[:,1]>30)
        green_indices_count=np.sum(green_indices)

        #count the bad peaks
        red_indices= (processed_list[:,1]<15)

        #count the average peaks
        orange_indices= np.logical_not(green_indices+red_indices)
        orange_indices_count=np.sum(orange_indices)

        #assess the quality of the spectrum
        if green_indices_count>=self.orange_threshold:
            spectrum_quality=Quality.GREEN
        elif orange_indices_count+green_indices_count>=1:
            spectrum_quality=Quality.ORANGE
        else:
            #todo: check: this case never happens as it's caught by previous "if processed_list is None"?
            #no need to further process if the quality is bad
            return pkl_list, Quality.RED

        quality_array[red_indices]=0
        quality_array[green_indices]=2

        processed_list[:,1]=quality_array

        return processed_list, spectrum_quality




class Quality(Enum):
    """A class depicting peak quality.

    Peaks with 30 < S/N value are classified as GREEN.
    Peaks with 15 <= S/N value <= 30 are classified as ORANGE.
    Peak with S/N value <15 are classified as RED.
    """
    RED=0
    ORANGE=1
    GREEN=2

class DataMissing(Exception):
    """
    Exception which is thrown when no valid peaklist files are found.
    """
    def __init__(self):
        message="The project directory has no valid spectra."
        super().__init__(message)
