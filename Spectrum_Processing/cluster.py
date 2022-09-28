import os
import sys
import pandas as pd

import numpy as np
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),".."))
from Spectrum_Processing.postProcess import format_CSV, format_TXT


class SpectrumClustering:
    """ The Class that takes care of matching, referencing and grouping (clustering) the data present in the uniqueness matrix."""

    def __init__(self, provider, threshold, output_directory, out_name):
        """Construct a class that can cluster uniqueness values.

        :param provider: Provides the input files and locations used in calculations.
        :type provider: FileProvider
        :param threshold: Cluster threshold.
        :type threshold: int
        :param output_directory: Path to the output folder
        :type output_directory: str
        """
        self.provider = provider
        self.threshold = threshold
        self.output_directory= output_directory
        self.refer_array=None
        self.match_array=None
        self.group_array=None
        self.out_name=out_name
        self.reference_list=None



    def prepare_clustering(self, uniqueness_matrix):
        """Write the clustering of the uniqueness matrix to their respective arrays.

        The 3 attributes refer_array, match_array, group_array are constructed.
        After executing each array contains size 3 arrays representing a REFER, MATCH, or GROUP

        :param uniqueness_matrix: A square matrix representing the uniqueness matrix.
        :type uniqueness_matrix: array
        :return: void
        """
        self.refer_array=[]
        self.match_array=[]
        self.group_array=[]



        # Sort the columns and rows of the matrix by descending row sum
        column_sum = np.sum(uniqueness_matrix, axis=0)
        sorted_indices = np.argsort(column_sum)[::-1]
        uniqueness_matrix = uniqueness_matrix[:, sorted_indices]
        uniqueness_matrix = uniqueness_matrix[sorted_indices, :]

        # Apply the new ordering to the filenames and fms_files
        filenames = [self.provider.green_filenames[i] for i in sorted_indices.tolist()]
        fms_files = [self.provider.green_fms_files[i] for i in sorted_indices.tolist()]
        pkl_files = [self.provider.green_pkl_files[i] for i in sorted_indices.tolist()]
        
        # Copy of uniqueness_matrix used for matching of spectra to obtained references
        uniqueness_matrix_full = np.copy(uniqueness_matrix)
        uniqueness_matrix_ref = np.copy(uniqueness_matrix)

        # Set all lower-triangular spectra to NaN in order to find the indices of the zero elements in the upper
        # triangular portion of the uniqueness matrix
        uniqueness_matrix[np.tril_indices(uniqueness_matrix.shape[0], -1)] = np.nan
        uniqueness_matrix_ref[np.tril_indices(uniqueness_matrix_ref.shape[0], 0)] = np.nan


        #convert the uniqueness_matrix nd_array to a panda dataframe
        uniqueness_matrix = pd.DataFrame(uniqueness_matrix)
        uniqueness_matrix_full = pd.DataFrame(uniqueness_matrix_full)


        # Each element of the array `spectra` is a tuple consisting of four spectra denoting:
        #   - A boolean indicating whether this spectra was visited
        #   - A list of references to other spectra
        #   - An index indicating the spectrum it refers to, None if N/A
        #   - A boolean indicating whether this spectrum is a reference spectrum
        spectra = [[False, [], None, True] for _ in range(len(self.provider.green_filenames))]
        
        zero_indices = np.argwhere(uniqueness_matrix_ref == 0)
        for i,j in zero_indices:
            spectra[int(i)][3] = False
            
        for column in uniqueness_matrix:
            # all row indexes in the coolumn with value 0, converted to a numpy array
            item_index = np.where(uniqueness_matrix[column] == 0)
            item_index = np.asarray(item_index)

            # the index of the current column
            index_column = uniqueness_matrix.columns.get_loc(column)

            # mark the spectrum to be visited
            spectra[index_column][0] = True

            # check if the spectrum is a reference, if so mark the spectrum to be a reference
            if index_column == item_index.item(0):
                # this sample is a reference
                spectra[index_column][3] = True

            # spectrum is not a reference
            else:

                # Filter out references in  item_index with UNX > 10, sample can only match a close reference

                check_reference = pd.DataFrame(columns=['index', 'UNX'])
                for x in np.nditer(item_index):
                    x = int(x)
                    check_reference.loc[len(check_reference.index)] = [x, uniqueness_matrix_full.at[column, x]]

                check_reference = check_reference.loc[(check_reference['UNX'] < 10)]
                item_index_resorted = check_reference['index'].values
                item_index_resorted = np.append(item_index_resorted, column)

                # Match non reference sample to obtained references
                for x in np.nditer(item_index_resorted):
                    x = int(x)
                    
                    if x < column:
                        if (spectra[x][3]) and (int(uniqueness_matrix_full.at[column,x]) < 15):
                            # add the refering to the list
                            self.refer_array.append([filenames[index_column], filenames[x]])


                            # mark the spectrum as "not a reference"
                            spectra[index_column][3] = False

                            break
                    else:
                        spectra[index_column][3] = True
                        # Should we add a field for suspicious references?

                # mark all other zero elements as matching
                for x in np.nditer(item_index):
                    x = int(x)
                    if x < index_column:
                        spectra[index_column][1] += [x]
                        self.match_array.append([filenames[index_column], filenames[x]])


        # Make a list with length len(spectra), the value at index i is a set{i} if the spectrum at that index is a reference spectrum

        corresponding_cluster = [{i} if is_reference else set()
                                 for i, [visited, refers, has_reference, is_reference] in enumerate(spectra)]


        # All reference spectra and their children are in their own cluster at the moment
        # Merge clusters if necessary
        for i, (_, references, _, _) in enumerate(spectra): #for each spectrum and its index
            old_clusters, new_cluster = [], set()

            for j in references: #for each reference to some other spectrum for my spectrum
                old_clusters += [corresponding_cluster[j]] #gather the clusters of those children (your "linked" clusters)
                new_cluster |= corresponding_cluster[j] #gather the clusters of those children in a set: unique numbers

            # for each sample: (each sample has a set of linked clusters)


            #   for each cluster in sample_linked_clusterset
            #       if child_cluster old_cluster==corresponding_cluster[j]:
            #           corresponding_cluster[j]= new_cluster
            #               break

            for j in range(len(corresponding_cluster)): #now check for every linked cluster
                #todo: optimize: via "in"?

                matches = any(old_cluster is corresponding_cluster[j] for old_cluster in old_clusters) #if any linked spectrum's cluster is the same as has a reference spectrum already in its own cluster
                if matches: #merge them-> set the corresponding cluster to the new cluster
                    corresponding_cluster[j] = new_cluster

        # Print the reference spectra for each cluster
        all_clusters = set(tuple(cluster) for cluster in corresponding_cluster)
        for i, cluster in enumerate(all_clusters):
            for j in cluster:
                #self.outfile.write('GROUP {0} {1}\n'.format(filenames[j],i))
                self.group_array.append([filenames[j],i])


    def write_clustering(self, out_format):
        """Write all clustering info in the format `out_format` to an output file.

        :param out_format: The format of the output file.
        :type out_format: str
        :return: void
        """
        if out_format=="txt":
            if self.out_name[-4:] != ".txt":
                self.out_name+=".txt"
            format_TXT(self.refer_array, self.match_array, self.group_array, os.path.join(self.output_directory, self.out_name))
        else: # out_format=="csv":
            if self.out_name[-4:] != ".csv":
                self.out_name+=".csv"
            format_CSV(self.refer_array, self.group_array, os.path.join(self.output_directory ,self.out_name), self.provider)

    def generate_reference_list(self):
        """Generate a reference list which contains all references.

        :return: void
        """
        self.reference_list=[]
        for [spectrum, group_number] in self.group_array:
            self.reference_list.append(spectrum)


        for [spectrum, ref_spectrum] in self.refer_array:
            self.reference_list.append(ref_spectrum)

    def integrate_dice_refers(self, dice_refer_array):
        """Add all dice refers to the cluster refer array.

        :param dice_refer_array: An array with refers generated from dice matching.
        :return: void
        """

        for match in dice_refer_array:
            self.refer_array.append(match)
