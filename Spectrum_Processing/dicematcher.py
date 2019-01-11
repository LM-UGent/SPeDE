import numpy as np


class DiceMatcher:
    """Class that takes care of DICE matching samples to a reference list."""

    def __init__(self, provider, reference_list):
        """

        :param provider: Instance of FileProvider class.
        :type provider: FileProvider
        :param reference_list: An array containing all unique references.
        :type reference_list: array
        """

        self.provider=provider
        self.reference_list=reference_list
        self.dice_matrix=None
        self.dice_referlist=None

        print("Sys: Generating dice matrix...")
        self.generate_dice_matrix()

        print("Sys: Generating dice referlist...")
        self.generate_dice_referlist()


    def generate_dice_matrix(self):
        """Generate a matrix with dice values.

         Each row is an orange spectrum and each column is a reference spectrum.

        :return: void
        """
        rows=len(self.provider.orange_filenames)
        columns=len(self.reference_list)
        if rows!=0:
            self.dice_matrix=np.empty((rows,columns))
        else:
            self.dice_matrix=np.array([])
            return

        #todo: optimize: parallellize
        # the headers of the columns are references
        # the headers of the rows are samples
        for i, orange_peak in enumerate(self.provider.orange_filenames): #for each orange sample
            for j, reference in enumerate(self.reference_list): # for each reference
                reference_index=np.where(self.provider.green_filenames==reference)[0][0]
                dice_value=self.calc_dice_value(self.provider.orange_pkl_files[i], self.provider.green_pkl_files[reference_index])
                self.dice_matrix[i][j]=dice_value


    def calc_dice_value(self, sample, reference):
        """Calculate the dice value for two peak files.

        :param sample: Peak file content of a sample.
        :type sample: array
        :param reference: Peak file content of a reference.
        :return: (double) the dice value of the comparison of sample and reference
        """

        #get the M/Z values
        sample_values=sample[:,0]
        reference_values=reference[:,0]

        #begin matching peaks

        shared_xy=0
        unique_x=0
        start_search_index=0

        #follow logic of matcher.construct_matching_list
        for ref_index in range(len(reference_values)):
            ref_mz_value=reference_values[ref_index]
            sample_index=start_search_index
            while sample_index!= len(sample_values) and sample_values[sample_index]< ref_mz_value:
                sample_index+=1

            if sample_index!=start_search_index:
                prev_match=np.abs(ref_mz_value-sample_values[sample_index-1])/(ref_mz_value+sample_values[sample_index-1])
            else:
                prev_match=np.inf
            if sample_index!=len(sample_values):
                succ_match=np.abs(ref_mz_value-sample_values[sample_index])/(ref_mz_value+sample_values[sample_index])
            else:
                succ_match=np.inf

            if prev_match < succ_match:
                sample_index-=1
                match_ppmd=prev_match*2*10**6
            else:
                match_ppmd=succ_match*2*10**6


            if match_ppmd <= 700:
                #the current sample peak is matched to a reference peak
                shared_xy+=1
                start_search_index=sample_index+1
                #go to the next sample peak
                break
            else:
                unique_x+=1

        #when all peaks are matched:
        if shared_xy==0:
            return 0
        else:
            return (shared_xy-unique_x)/shared_xy #move the *100 to the comparison


    def generate_dice_referlist(self):
        """Convert the values in the dicematrix to refer_list entries.

        :return: void
        """

        self.dice_referlist=[]
        refer_indices=np.argwhere(self.dice_matrix>0.7)
        for [i,j] in refer_indices:
            reference_index=np.where(self.provider.green_filenames==self.reference_list[j])[0][0]
            self.dice_referlist.append([self.provider.orange_filenames[i], self.provider.green_filenames[reference_index]])

