import concurrent.futures
import math
import multiprocessing
import os

import numba as nb
import numpy as np
import pandas as pd

EXPERIMENT=False

class SpectrumMatcher:
    """
    Handles the creation of a uniqueness matrix.
    """

    def __init__(self, provider, density, local, cutoff, validate, output_directory, validation_output_name):
        """Construct a matcher that can be used to calculate the uniqueness matrix.

        :param provider: Provides the input files and locations used in calculations.
        :type provider: FileProvider
        :param density: PPMC threshold used to determine matches in the initial matching.
        :type density: int
        :param local: PPMC local threshold expressed as a percentage used to refine matches based on their PPMC.
        :type local: int
        :param cutoff: S/N cutoff value.
        :type cutoff: int
        :param validate: Determines whether or not the full uniqueness matrix is written to an outputfile validation_data.csv
        :type validate: bool
        """
        self.provider = provider
        self.density = density
        self.local = local
        self.cutoff = cutoff
        self.validate= validate
        self.output_directory=output_directory

        #output must be csv
        if validation_output_name[-4:] != ".csv":
            validation_output_name += ".csv"

        self.validation_output=validation_output_name

    def calculate_uniqueness_matrix(self):
        """Calculate the uniqueness matrix and optionally prints validation data.

        When the flag -v is set, the validation data will be printed to an external file.

        :return: The uniqueness matrix of all files contained in `provider`.
        """

        maximum_pkl_length=self.provider.green_pkl_files.shape[1]
        maximum_interval_length = np.amax(self.provider.intervals[:, 2] - self.provider.intervals[:, 1] + 1)

        matcher_jit = SpectrumMatcherJIT(self.density, self.local, self.cutoff, self.provider.green_pkl_files,
                                         self.provider.pkl_files_length, maximum_pkl_length, self.provider.green_fms_files,
                                         self.provider.intervals, maximum_interval_length)

        print("Sys: Start calculating using {0} processess...".format(multiprocessing.cpu_count()))
        #parallellize the calculation of the uniqueness values
        with concurrent.futures.ThreadPoolExecutor() as executor:
            jobs_count = multiprocessing.cpu_count()
            jobs = [executor.submit(calculate_uniqueness_matrix_step, matcher_jit, i, jobs_count) for i in range(jobs_count)]


        #todo: optimize: via axis sum
        uniqueness_matrix = jobs[0].result()[0]
        shared_matrix=jobs[0].result()[1]

        #todo: do something with shared_matrix
        for job in jobs[1:]:
            uniqueness_matrix += job.result()[0]
            shared_matrix+=job.result()[1]

        if self.validate:
            self.print_validation(uniqueness_matrix, shared_matrix)

        return uniqueness_matrix

    def print_validation(self, uniqueness_matrix, shared_matrix=None):
        """Print the uniqueness matrix to an external file data_validation.csv

        :param uniqueness_matrix: The matrix to be serialized.
        :type uniqueness_matrix: array
        :param shared_matrix: (Optional) Not currently used.
        :type shared_matrix: array

        :return: void
        """

        # Sort the columns and rows of the matrix by descending row sum
        column_sum = np.sum(uniqueness_matrix, axis=0)
        sorted_indices = np.argsort(column_sum)[::-1]
        validation_matrix = uniqueness_matrix[:, sorted_indices]
        validation_matrix = validation_matrix[sorted_indices, :]


        # Apply the new ordering to the filenames and fms_files
        filenames = [self.provider.green_filenames[i] for i in sorted_indices.tolist()]


        # Make sure the output file can be written to
        outfilename=os.path.join(self.output_directory, self.validation_output)
        try:
            output= open(outfilename,"w+")
        except IOError:
            raise IOError


        data=pd.DataFrame(validation_matrix,columns=filenames)

        # Insert a column with the filenames
        data.insert(0, '', pd.Series(filenames, index=data.index))
        pd.DataFrame.to_csv(data,output,index=False)
        output.close()



#todo: optimize: param size
@nb.jitclass([
    ('density', nb.int64),
    ('local', nb.int64),
    ('cutoff', nb.int64),
    ('pkl_files', nb.float64[:, :, :]),
    ('pkl_files_length', nb.int32[:]),
    ('maximum_pkl_length', nb.int64),
    ('fms_files', nb.int32[:, :]),
    ('intervals', nb.float64[:, :]),
    ('maximum_interval_length', nb.int64)
])
class SpectrumMatcherJIT:
    """A JIT-compiled class that holds all information necessary to compute the uniqueness matrix.

    Note that this new class is introduced since `SpectrumMatcher` needs access to functions that are not supported in
    the NoPython mode of Numba (e.g. concurrent.futures). Since that class can't be passed around, this one is created.
    """

    def __init__(self, density, local, cutoff, pkl_files, pkl_files_length, maximum_pkl_length, fms_files, intervals, maximum_interval_length):
        self.density = density
        self.local = local
        self.cutoff = cutoff
        self.pkl_files = pkl_files
        self.pkl_files_length = np.array(pkl_files_length,dtype=np.int32)
        self.maximum_pkl_length = maximum_pkl_length
        self.fms_files = fms_files
        self.intervals = intervals
        self.maximum_interval_length = maximum_interval_length



@nb.njit(nogil=True)
def calculate_uniqueness_matrix_step(matcher, start, step):
    """Calculate a part of the uniqueness matrix.

    A process uses this function to calculate a part of the uniqueness matrix. More specifically, all rows every `step`
    rows is calculated.

    :param matcher: A JIT compiled class containing the necessary variables, files and locations for calculating the partial matrix.
    :type matcher: SpectrumMatcherJIT
    :param start: The first row at which the current process starts.
    :type start: int
    :param step: The total amount of processes working on the complete uniqueness matrix.
    :type step: int
    :return: A part of the uniqueness matrix and shared matrix in which every step-th row is filled in.
    """

    #todo: optimize: datatypes
    count = matcher.pkl_files.shape[0]
    uniqueness_matrix = np.zeros((count, count))
    shared_matrix=np.zeros((count, count))
    #todo: print progress

    # Fill in the uniqueness matrix
    for i in range(start, count, step): #for each row, every step, until count, do
        for j in range(i + 1, count):   #for each column in the upper-right part of the matrix
            # calculate the unique values of i wrt j and vice versa, but remember that (i,j) shows the unique peaks of
            # the ith file wrt the jth file , so the indices should be swapped when filling the matrix
            #todo: clean: switch these indices for clarity
            unique_x, unique_y, shared_xy = calculate_uniqueness_value(matcher, i, j)
            uniqueness_matrix[i, j] = unique_y #swap indices: (i,j) with y
            uniqueness_matrix[j, i] = unique_x #swap indices: (j,i) with x
            shared_matrix[i,j]=shared_xy       #gather the shared features between x and y

    return uniqueness_matrix, shared_matrix


@nb.jit(nogil=True)
def calculate_uniqueness_value(matcher, i, j):
    """Calculate the unique x and unique y values for the given spectra indices.

    :param matcher: A JIT compiled class containing the necessary variables, files and locations for calculating the partial matrix.
    :type matcher: SpectrumMatcherJIT
    :param i: The spectra at matrix spot (i,j)=x and (j,i)=y are compared.
    :type i: int
    :param j: The spectra at matrix spot (i,j)=x and (j,i)=y are compared.
    :type j: int
    :return: A 3-tuple whose elements are the amount of x, y and shared xy values
    """
    # Execute the first step of the algorithm (i.e. matching peaks). The output of this method is elaborately
    # described in the corresponding docstring. In short, we now have two Numpy arrays of equal length of which we
    # want to compute the PPMC between corresponding rows and two arrays that denote the unique x and y matches.
    intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y, shared_peaks_xy = construct_matching_list(matcher, i, j)

    # Compute the PPMC between each row of `intervals_x` and `intervals_y` and store the result in `ppmcs`.
    denominators = np.sqrt(np.sum(intervals_x ** 2, axis=1) * np.sum(intervals_y ** 2, axis=1))
    ppmcs = np.sum(intervals_x * intervals_y, axis=1) / denominators * 100

    # For each match where the PPMC is below the given threshold, increment the corresponding unique counter.
    matches_below_threshold = (ppmcs < matcher.local)
    unique_x = np.sum(np.logical_and(matches_below_threshold, threshold_exceeded_x))
    unique_y = np.sum(np.logical_and(matches_below_threshold, threshold_exceeded_y))
    shared_xy = np.sum(np.logical_and(np.logical_not(matches_below_threshold), shared_peaks_xy))

    return unique_x, unique_y, shared_xy


@nb.njit(nogil=True)
def _find_nearest_interval(intervals, location):
    """Return the start and end index of the interval that corresponds to the given location.

    :param location: The M/Z value of the peak whose surrounding interval we wish to obtain.
    :type location: int
    :param intervals: The first index denotes an M/Z value. The second and third values are the indices in an FMS file for which that index gives you the interval start, respectively end value.
    :type intervals: array
    :return: The start and end index of the interval corresponding to the M/Z value that is the closest to the given M/Z value.
    """

    #todo: optimize: convert intervals to continuous array such that no searching is needed
    # Locate the index where the given location would be inserted in the list of intervals
    i = np.searchsorted(intervals[:, 0], location, side="left")

    # The closest M/Z value in the list of intervals is now either the index itself or the previous index.
    if i > 0 and (i == intervals.shape[0] or
                  math.fabs(location - intervals[i - 1, 0]) < math.fabs(location - intervals[i, 0])):
        i -= 1

    # Convert the start and end value of the interval to indices into the FMS file.
    return int(intervals[i, 1]), int(intervals[i, 2])


@nb.njit(nogil=True)
def add_match(mz, x_above, y_above, xy_shared, intervals, index, intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y, shared_peaks_xy, fms_file_x, fms_file_y):
    """Add an entry to the passed variables to indicate a new match has been found.

    For a new M/Z value, fill intervals_x, intervals_y, threshold_exceeded_x and threshold_exceeded_y with the appropriate intervals surrounding
    the M/Z value for x and y. Also fill threshold_exceeded_x/y with whether or not the x/y peak exceeded the cutoff threshold.

    :param mz: The MZ value of the peak that is compared to.
    :type mz: int
    :param x_above: Denotes if the x peak S/N value surpasses the threshold value.
    :type x_above: bool
    :param y_above: Denotes if the y peak S/N value surpasses the threshold value.
    :type y_above: bool
    :param xy_shared: Denotes if x and y are sharing a peak with M/Z value mz.
    :type xy_shared: bool
    :param intervals: The first index denotes an M/Z value. The second and third values are the indices in a FMS file for which that index gives you the interval start, respectively end value.
    :type intervals: array
    :param index: The index at which a new match should be inserted.
    :type index: int
    :param intervals_x: Contains at each index the appropriate interval of signal intensities values for spectrum x.
    :type intervals_x: array
    :param intervals_y: Contains at each index the appropriate interval of signal intensities values for spectrum y.
    :type intervals_y: array
    :param threshold_exceeded_x: Contains at each index whether or not the enlisted peak of spectrum x surpassed the cutoff threshold.
    :type threshold_exceeded_x: array[bool]
    :param threshold_exceeded_y: Contains at each index whether or not the enlisted peak of spectrum y surpassed the cutoff threshold.
    :type threshold_exceeded_y: array[bool]
    :param shared_peaks_xy: Contains at each index whether or not the enlisted peak
    :type shared_peaks_xy: array[bool]
    :param fms_file_x: FMS file of spectrum x.
    :type fms_file_x: array
    :param fms_file_y: FMS file of spectrum y.
    :type fms_file_y: array
    :return: void
    """

    start_idx, end_idx = _find_nearest_interval(intervals, mz)
    length = (end_idx + 1) - start_idx


    intervals_x[index, :length] = fms_file_x[start_idx:end_idx + 1] - np.mean(fms_file_x[start_idx:end_idx + 1])
    intervals_y[index, :length] = fms_file_y[start_idx:end_idx + 1] - np.mean(fms_file_y[start_idx:end_idx + 1])

    threshold_exceeded_x[index] = x_above
    threshold_exceeded_y[index] = y_above
    shared_peaks_xy[index]=xy_shared


@nb.njit(nogil=True)
def construct_matching_list(matcher, i, j):
    """Return an array representing the matching of samples between the FMS files based on the PKL files.

    This method implements the first step of computing the uniqueness matrix in the given algorithm. However,
    instead of returning a list of (x_idx, y_idx) pairs, it returns a representation that is better suited for
    efficiently executing subsequent steps of the algorithm.

    :param matcher: A JIT compiled class containing the necessary variables, files and locations for current calculations.
    :type matcher: SpectrumMatcherJIT
    :param i: The spectra at matrix spot (i,j)=X and (j,i)=Y are manipulated.
    :type i: int
    :param j: The spectra at matrix spot (i,j)=X and (j,i)=Y are manipulated.
    :type j: int
    :return: A 5-tuple (intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y containing for all peaks of x and y the appropriate intervals, whether or not a peak surpassed the cutoff threshold and if they share shared peaks.
    """

    pkl_file_x, pkl_file_y, pkl_file_x_length, pkl_file_y_length, fms_file_x, fms_file_y = matcher.pkl_files[i], matcher.pkl_files[j], matcher.pkl_files_length[i], matcher.pkl_files_length[j], matcher.fms_files[i], matcher.fms_files[j]

    density, local, cutoff, intervals = matcher.density, matcher.local, matcher.cutoff, matcher.intervals

    y_pos = 0

    #an array which will contain at each index the appropriate interval of signal intensities. Will be used in PPMC calculations
    intervals_x = np.zeros((matcher.maximum_pkl_length, matcher.maximum_interval_length))
    intervals_y = intervals_x.copy()

    #an array which will contains booleans denoting if the peak at index i has exceeded the cutoff threshold
    threshold_exceeded_x = np.zeros((matcher.maximum_pkl_length, ))
    threshold_exceeded_y = threshold_exceeded_x.copy()

    #an array which will contain booleans indicating if the peaks at index i and j have shared features
    shared_peaks_xy=threshold_exceeded_x.copy()

    #the value at which a peak has to be stored in threshold_*
    index = 0

    QUALITY_GREEN=2 #A local constant that depicts the Quality.Green enum

    for x_i in range(pkl_file_x_length): #for each reference peak in x's peak file
        x_mz, x_sn = pkl_file_x[x_i, 0], pkl_file_x[x_i, 1] #get my reference peak index M/Z value and reference S/N value

        # Starting from index `y_pos`, determine the index `y_i` where the M/Z value of X would be inserted in the
        # array of M/Z values of Y if we wanted to keep the array sorted. That is, the index of the first unmatched
        # M/Z value in the Y array that is bigger than the current M/Z value of X.
        y_i = y_pos
        while y_i != pkl_file_y_length and pkl_file_y[y_i][0] < x_mz:   #while my sample peak value is lower than the reference peak value (#pkl_file_y[x]=(peak M/Z value , S/N value) at index x)
            y_i += 1                                                    #increase index

        # Compare y_position - 1 and y_position and match x with the best of these two (lowest error)

        #factor 0.5 is moved to denominator in the comparison with the density
        predecessor_match = abs(x_mz - pkl_file_y[y_i - 1][0]) / (x_mz + pkl_file_y[y_i - 1][0]) if y_i != y_pos else np.inf
        successor_match = abs(x_mz - pkl_file_y[y_i][0]) / (x_mz + pkl_file_y[y_i][0]) if y_i != len(pkl_file_y) else np.inf

        if predecessor_match * (2 * 10**6) < density or successor_match * (2 * 10**6) < density: #if a match is made

            if predecessor_match < successor_match:
                y_i-=1 #reference peak at previous index was better
            #else: reference peak at current index is best

            #y_i -= 1 if predecessor_match < successor_match else 0 #


            #todo: optimize: do not partition the for loops that much, compiler will be able optimize better if they are contained as a whole?
            for y in range(y_pos, y_i): #for every sample peak the we passed-> unmatched peaks
                if pkl_file_y[y][1] == QUALITY_GREEN: #if its S/N value is high enough
                    #add a match while denoting that the sample's y exceeds the threshold, since, as the peaklists are ordered, no peak will match with these
                    add_match(pkl_file_y[y][0], False, True, False, intervals, index, intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y, shared_peaks_xy,fms_file_x, fms_file_y)
                    index += 1 #increase the index in which we put the next peak in add_match

            y_pos = y_i + 1 #continue your search for the next match starting from the index following our current peak

            #categorize the matched peaks
            if x_sn ==QUALITY_GREEN or pkl_file_y[y_i][1] ==QUALITY_GREEN: #if one of both peaks has an adequate S/N value
                #add a match with the corresponding booleans in the x/y matched arrays
                if EXPERIMENT:
                    #take the average of M/Z values to search for the window
                    mz_value=(pkl_file_y[y_i][0] + x_mz)/2
                    add_match(mz_value, x_sn ==QUALITY_GREEN, pkl_file_y[y_i][1] ==QUALITY_GREEN,False, intervals, index, intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y,shared_peaks_xy, fms_file_x, fms_file_y)
                else:
                    add_match(pkl_file_y[y_i][0], x_sn ==QUALITY_GREEN, pkl_file_y[y_i][1] ==QUALITY_GREEN,False, intervals, index, intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y,shared_peaks_xy, fms_file_x, fms_file_y)
                index += 1
            else: #add to matched list to check for shared features
                add_match(pkl_file_y[y_i][0],False, False, True, intervals, index, intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y,shared_peaks_xy, fms_file_x, fms_file_y)
                index += 1

        elif x_sn ==QUALITY_GREEN: #if no sample peak matched with the reference peak
            add_match(x_mz, True, False, False, intervals, index, intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y, shared_peaks_xy, fms_file_x, fms_file_y)
            index += 1

    for y_i in range(y_pos, pkl_file_y_length):
        y_mz = pkl_file_y[y_i, 0]
        y_sn = pkl_file_y[y_i, 1]
        if y_sn ==QUALITY_GREEN:
            add_match(y_mz, False, True, False, intervals, index, intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y,shared_peaks_xy, fms_file_x, fms_file_y)
            index += 1

    #retain only the useful information of the respective arrays
    intervals_x = intervals_x[:index, ]
    intervals_y = intervals_y[:index, ]
    threshold_exceeded_x = threshold_exceeded_x[:index, ]
    threshold_exceeded_y = threshold_exceeded_y[:index, ]
    shared_peaks_xy=shared_peaks_xy[:index, ]

    return intervals_x, intervals_y, threshold_exceeded_x, threshold_exceeded_y, shared_peaks_xy
