import os
import sys

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

        # Set all lower-triangular spectra to NaN in order to find the indices of the zero elements in the upper
        # triangular portion of the uniqueness matrix
        uniqueness_matrix[np.tril_indices(uniqueness_matrix.shape[0], 0)] = np.nan
        zero_indices = np.argwhere(uniqueness_matrix == 0)

        # Each element of the array `spectra` is a tuple consisting of four spectra denoting:
        #   - A boolean indicating whether this spectra was visited
        #   - A list of references to other spectra
        #   - An index indicating the spectrum it refers to, None if N/A
        #   - A boolean indicating whether this spectrum is a reference spectrum
        spectra = [[False, [], None, False] for _ in range(len(self.provider.green_filenames))]

        for i, j in zero_indices:
            # Convert Numpy integers to good ol' Python integers.
            #todo: optimize: necessary?
            i, j = int(i), int(j)

            # Mark the involved spectra as visited
            spectra[i][0],spectra[j][0] = True, True

            # Append element i to the array present in spectra[j]
            # todo: check: Do they need to be linked if they are not processed due to too low PPMC in the next step?
            spectra[j][1]+=[i]

            # Don't further process matches where the total PPMC of the peaks above 2100 is lower than the threshold
            #todo: optimize: definitely
            samples_file_i, samples_file_j = fms_files[i][235:], fms_files[j][235:]
            if np.corrcoef(samples_file_i, samples_file_j)[0, 1] * 100 < self.threshold:
                continue

            #spectrum[x][2]: An index indicating the spectrum it refers to, None if N/A
            if spectra[i][2] and spectra[j][2]:
                #both already refer to another spectrum, just match these two
                self.match_array.append([filenames[j], filenames[i]])
            elif spectra[i][2] and not spectra[j][2]:
                # The second spectrum does is not a reference yet
                # Make sure the second spectrum is unique wrt the whole chain, so check unicity with every reference
                # that's linked.

                # Make the second spectrum refer to the reference of the first spectrum
                referred_index=spectra[i][2]
                ref_unique_peaks=uniqueness_matrix[referred_index][2]
                #repeat until we reach the end of the chain, or a unique peak is found
                while ref_unique_peaks == 0 and referred_index is not None:
                    # j= second spectrum index
                    # get the next reference in the chain
                    referred_index=spectra[referred_index][2]
                    # check uniqueness of second spectrum wrt referred spectrum
                    ref_unique_peaks=uniqueness_matrix[referred_index][j]

                if ref_unique_peaks!=0:
                    # ref is found
                    spectra[j][3]=True
                    spectra[j][2]=referred_index
                    self.match_array.append([filenames[j], filenames[i]])

                else: #ref_unique_peaks==0 and referred_index== None
                    #end of the chain is reached
                    # no new reference has been found, just add a match
                    self.match_array.append([filenames[j], filenames[i]])

            elif not spectra[i][2] and spectra[j][2]:
                #make the first spectrum a reference, and match the second with the first
                spectra[i][3]=True
                self.match_array.append([filenames[j], filenames[i]])
            else: # not spectra[j][2] and not spectra[i][2]:
                # If both involved spectra don't refer to another spectra, then make j refer to i
                self.refer_array.append([filenames[j], filenames[i]])
                #self.outfile.write('REFER {0} {1}\n'.format(filenames[j], filenames[i]))
                spectra[j][2] = i
                spectra[i][3] = True


        # Place each unvisited spectrum in its own cluster
        spectra = [[True, [i], False, True] if not visited else [visited, refers, has_reference, is_reference]
                   for i, [visited, refers, has_reference, is_reference] in enumerate(spectra)]

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
