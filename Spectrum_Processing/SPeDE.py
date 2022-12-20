import argparse
import datetime
import os
import sys
import time

#Own modules
import traceback


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),".."))

from Spectrum_Processing.postProcess import generate_krona
from Spectrum_Processing.provider import FileProvider
from Spectrum_Processing.matcher import SpectrumMatcher
from Spectrum_Processing.cluster import SpectrumClustering
from Spectrum_Processing.dicematcher import DiceMatcher
from Spectrum_Processing import postProcess



def SPeDE_wrapper(argdict):
    """Wrapper to adress the main function in a new process

    :param argdict: a dictionary containing all arguments for the main SPeDE function
    :return: output of main
    """

    #set the stderr to the provided cross process queue
    queue=argdict["queue"]
    args=argdict["args"]

    try:
        return main(*args) #* to unpack all arguments contained in args
    except Exception as e:
        message=traceback.format_exc()
        queue.put(message)


def main(intervals, project_directory, output_directory, peaks, density, local, cutoff, validate,  validation_name, cluster, name, output_format, copy, krona, affix=None):
    krona_name="krona_output.txt"

    tic=time.time()
    if affix is None:
        affix=datetime.datetime.today().strftime("%Y_%m_%d_%H_%M_%S_")

    if not os.path.isdir(output_directory):
        print("Sys: output directory",output_directory,"does not exist yet. Creating it for you.")
        os.makedirs(output_directory)

    print("Sys: Reading all spectra...")
    provider = FileProvider(intervals, project_directory, int(peaks))


    print("Sys: Creating SpectrumMatcher...")
    matcher = SpectrumMatcher(provider, density=int(density), local=int(local), cutoff=int(cutoff),
                              validate=validate, output_directory=output_directory, validation_output_name=affix+validation_name)

    print("Sys: Calculating uniqueness matrix...")
    matrix = matcher.calculate_uniqueness_matrix()

    print("Sys: Preparing clustering data...")
    cluster = SpectrumClustering(provider, threshold=int(cluster), output_directory=output_directory, out_name=affix+name)
    cluster.prepare_clustering(matrix)

    print("Sys: Generating cluster reference list...")
    cluster.generate_reference_list()

    print("Sys: Preparing dice data...")
    dice_matcher= DiceMatcher(provider,cluster.reference_list)
    cluster.integrate_dice_refers(dice_matcher.dice_referlist)

    print("Sys: Writing clustering...")
    cluster.write_clustering(output_format)

    print("Sys: Postprocessing...")

    if krona:
        print("Sys: Generating Krona output...")
        generate_krona(cluster.group_array, cluster.refer_array, os.path.join(output_directory,affix+krona_name),provider)
        pass

    if copy:
        print("Sys: Copying unique references to output folder...")
        submap="References"
        postProcess.copy_to(cluster.reference_list, project_directory, os.path.join(output_directory,affix+submap))

    toc=time.time()-tic
    print("Sys: Total processing time: "+str(toc))

    return 0


if __name__ == '__main__':

    # Assumes intervals file is named 'ppmc_interval_index.csv' and is located in folder GUI as 
    intervals_location = "GUI/ppmc_interval_index.csv"
    path_intervals_file = os.path.join(os.path.dirname(os.path.abspath(__file__)).rsplit(os.sep,1)[0],intervals_location)

    parser = argparse.ArgumentParser(description='Determines the reference spectra and clustering of the given samples.')

    parser.add_argument('-i', dest='intervals', default=path_intervals_file,
                        help='path to file specifying the intervals (default: %(default)s)')
    parser.add_argument('-d', dest='density', default=700,
                        help='the PPM threshold (default: %(default)s)')
    parser.add_argument('-c', dest='cluster', default=75,
                        help='the PPVM cluster threshold in percentage (default: %(default)s)')
    parser.add_argument('-l', dest='local', default=50,
                        help='the PPMC local threshold in percentage (default: %(default)s)')
    parser.add_argument('-m', dest='cutoff', default=30,
                        help='the S/N cutoff in M/Z (default: %(default)s)')
    parser.add_argument('-o', '--output-format',dest='output_format', default='csv',
                        help='output format of the spectra (default: %(default)s)')
    parser.add_argument('-p', '--peak-count-threshold', dest='peaks', default=5,
                        help='Peaks with an S/N value >30 are saved in peakcountB. If peakcountB >= `PEAKS`, then a spectrum is classified as green.')
    parser.add_argument('-n', dest='name', default="SPeDE_output",
                        help="the name of the reference list output file, extension must match output format. (default: %(default)s)")
    parser.add_argument('-q', '--validation-name', dest='validation_name', default="data_validation.csv",
                        help="the name of the data validation matrix, must be .csv (default: %(default)s)")
    parser.add_argument('-e', '--copy-files', dest='copy_files', default=False, action='store_true',
                        help='copy the unique references to a subfolder (default: %(default)s)')
    parser.add_argument('-k', '--krona-output', dest='krona', default=False, action='store_true',
                        help='Create a ready-to-go krona output file (default: %(default)s)')
    parser.add_argument('-v', '--output-validate', dest='validate', default=False, action='store_true',
                        help='print the validation data to an output file (default: %(default)s)')


    #parser.add_argument('intervals', help='file specifying the intervals')
    parser.add_argument('project_directory', help='directory containing all datafiles')
    parser.add_argument('output_directory', help='directory which will contain any output file')

    args = parser.parse_args()

    main(args.intervals, args.project_directory, args.output_directory, args.peaks, args.density, args.local,args.cutoff, args.validate,
         args.validation_name, args.cluster,args.name, args.output_format, args.copy_files, args.krona)




