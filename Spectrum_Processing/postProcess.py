import os
import sys

import pandas as pd
import numpy as np
from shutil import copyfile

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),".."))
from Spectrum_Processing.provider import Quality

def format_CSV(refer_array, group_array, outfile_path, provider):
    """ Write the formatted output of SPeDE to a csv file.

    The csv file should contain the following format:
    SOURCE_FILE,REFERENCE,REFERENCE NUMBER,GROUP,QUALITY,STRAIN,BRUKER_TOPHIT,BRUKER_SCORE
    Underneath should be a list with not matched files.
    Underneath that should be a list with rejected files.

    :param refer_array: a 2D array with at each index a size 2 array depicting REFER A B.
    :type refer_array: array
    :param match_array: a 2D array with at each index a size 2 array depicting MATCH A B.
    :type match_array: array
    :param group_array: a 2D array with at each index a size 2 array depicting GROUP A groupNo.
    :type group_array: array
    :param outfile_path: The path to the output file.
    :type outfile_path: str
    :param provider: a FileProvider to provide file names
    :type provider: FileProvider
    :return: void
    """
    # Define column names
    column_names=["SOURCE_FILE", "REFERENCE", "REFERENCE_NUMBER", "REFERENCE_GROUP"]
    
    # todo: optimize: make all dataframe manipulations inplace if that would be more memory friendly
    group_dict={}
    index=0
    data=[]

    # prepare a dict to map spectra to [source_file, is_reference, references, group number]
    # first add all references
    for [spectrum, group_number] in group_array:
        group_dict[spectrum]=[group_number, index]
        data.append([spectrum[:-4], "Yes", index, group_number])
        index+=1


    # add non-references to list, all reference spectra should already be in the list above
    data_no_reference = []
    for [spectrum, ref_spectrum] in refer_array:
        data_no_reference.append([spectrum[:-4], "No", group_dict[ref_spectrum][1], group_dict[ref_spectrum][0]])

    # remove duplicates, keep only first occurrence
    data_no_reference_pd = pd.DataFrame(data_no_reference, columns=column_names)
    data_no_reference_pd.drop_duplicates(subset="SOURCE_FILE", keep='first', inplace=True)
    
    # convert data to DataFrame
    data=pd.DataFrame(data,columns=column_names)

    # merge data and data_no_reference_pd
    data = pd.concat([data, data_no_reference_pd], sort=False)

    # sort the data according to groups
    data.sort_values(by=["REFERENCE_GROUP", "SOURCE_FILE"], inplace=True)

    # don't drop column source file here, we still need it
    data = data.set_index("SOURCE_FILE",drop=False)

    # get strain names, bruker id, bruker score

    # get QualityControlledDBField files
    map_files= [x for x in os.listdir(provider.proj_path) if x[-29:-4]=="QualityControlledDBFields"]

    if len(map_files)!=0:

        # convert to DataFrame and gather all namefiles in one frame
        table=pd.DataFrame()
        for file in map_files:
            table=pd.concat([table, pd.read_csv(os.path.join(provider.proj_path,file) , sep="\t",usecols=[2,3,35,36])],sort=False)

        table=table.set_index("SOURCE_FILE")
        table=table[~table.index.duplicated(keep='first')]
    else: # there is no QualityControlledDBField file
        # make a table with all NaN values, index SOURCE_FILE and appropriate columns
        table=data.copy()
        table.insert(0, 'STRAIN', pd.Series([np.NaN]*len(table.index),index=table.index))
        table.insert(0, 'BRUKER_TOPHIT', pd.Series([np.NaN]*len(table.index),index=table.index))
        table.insert(0, 'BRUKER_SCORE', pd.Series([np.NaN]*len(table.index),index=table.index))
        table=table.drop(columns=["SOURCE_FILE",  "REFERENCE", "REFERENCE_NUMBER", "REFERENCE_GROUP"])
        print(table)


    # get qualities table
    filenames_raw=[x[:-4] for x in provider.filenames]
    filenames=pd.DataFrame(filenames_raw, columns=["SOURCE_FILE"])


    qualities=[]
    #correctly format the qualities column
    for quality in provider.qualities:
        if quality==Quality.GREEN:
            qualities.append("GREEN")
        elif quality==Quality.ORANGE:
            qualities.append("ORANGE")
        else:
            qualities.append("RED")


    qualities=pd.DataFrame(qualities,columns=["QUALITY"])
    qualities=pd.concat([filenames,qualities],axis=1)
    qualities=qualities.set_index("SOURCE_FILE")

    # join everything on the field SOURCE_FILE
    result = pd.concat([data, qualities, table], axis=1,join="inner",sort=False)

    try:
        outfile=open(outfile_path,"w+")
    except IOError:
        raise IOError
    
    # write the main table to the outfile
    column_names=["SOURCE_FILE","QUALITY","REFERENCE","REFERENCE_NUMBER","REFERENCE_GROUP","STRAIN","BRUKER_TOPHIT","BRUKER_SCORE"]
    result=result.reindex(columns=column_names)
    pd.DataFrame.to_csv(result,outfile, index=False)

    # todo: change this so 'RED' spectra are added in csv format
    # find the spectra that aren't matched
    outfile.write("\nNot matched:\n")

    # sort both lists and run through them to find which ones are missing
    not_red_filenames =[x[:-4] for x in sorted(list(provider.orange_filenames)+list(provider.green_filenames))]
    matched_filenames=sorted(data["SOURCE_FILE"].values)
    not_matched_filenames=[]

    if len(not_red_filenames)!= len(matched_filenames): # if both are the same length, they both have all references
        not_red_index=0
        matched_index=0
        last_matched_index=-1

        while not_red_index<len(not_red_filenames):
            while matched_index<len(matched_filenames):
                if not_red_filenames[not_red_index]==matched_filenames[matched_index]:
                    last_matched_index=matched_index
                    break
                else:
                    matched_index+=1
                    if matched_index==len(matched_filenames):
                        #no match found, start with next not_red_index
                        not_matched_filenames.append(not_red_filenames[not_red_index])
                        break

            matched_index=last_matched_index+1
            not_red_index+=1

        if len(not_matched_filenames)!=0:
            #not all matches were made
            not_matched_filenames=pd.DataFrame(not_matched_filenames,columns=["SOURCE_FILE"])

            not_matched_filenames=not_matched_filenames.set_index("SOURCE_FILE", drop=False)
            not_matched_data=pd.concat([not_matched_filenames,qualities],axis=1,join="inner")

            pd.DataFrame.to_csv(not_matched_data,outfile, index=False)

    outfile.write("\nRejected spectra:\n")
    for filename in provider.red_filenames:
        outfile.write(filename[:-4]+",RED"+"\n")
    outfile.close()

def format_TXT(refer_array, match_array, group_array, outfile_path):
    """Dump the refer, match and group array to outfile_path.

    :param refer_array: An array with all refers.
    :type refer_array: array
    :param match_array: An array with all matches.
    :type match_array: array
    :param group_array: An array with all groups.
    :type group_array: array
    :param outfile_path: Path to file.
    :type outfile_path: str
    :return:
    """
    try:
        outfile=open(outfile_path,"w+")
    except IOError:
        raise IOError
    for i,j in group_array:
        outfile.write("GROUP {0} {1}\n".format(i,j))
    for i,j in match_array:
        outfile.write("MATCH {0} {1}\n".format(i,j))
    for i,j in refer_array:
        outfile.write("REFER {0} {1}\n".format(i,j))

    outfile.close()

def copy_to(reference_list, source_folder, target_folder):
    """Copy every file of reference_list in source_folder to target_folder.

    :param source_folder: Path to source folder.
    :type source_folder: str
    :param reference_list: Array of files to be copied.
    :type reference_list: array
    :param target_folder: Path to target folder.
    :type target_folder: str
    :return: void
    """

    if not os.path.exists(target_folder):
        os.mkdir(target_folder)

    for file in reference_list:
        srcpath_PKL=os.path.join(source_folder,"PKL_"+file)
        srcpath_FMS=os.path.join(source_folder,"ReGrid_"+file)
        copyfile(srcpath_FMS, os.path.join(target_folder,"ReGrid_"+file))
        copyfile(srcpath_PKL, os.path.join(target_folder,"PKL_"+file))

def generate_krona(group_array, refer_array, outfile_path, provider):
    """Generate a txt outputfile that's ready to be processed by krona.

    :param group_array: An array with all groups.
    :type group_array: array
    :param refer_array: An array with all groups.
    :param outfile_path: Path to output file.
    :type outfile_path: str
    :param provider: a FileProvider to provide file names
    :type provider: FileProvider
    :return: void
    """
    group_dict={}
    index=0
    data=[]


    #data=[source_file, groupNo, reference spectrum]
    #prepare a dict to map spectra to [source_file, is_reference, references, group number]
    for [spectrum, group_number] in group_array:
        group_dict[spectrum]=[group_number, index]
        data.append([spectrum[:-4], group_number, spectrum[:-4]])
        index+=1


    #add references to dict, all referenced spectra should already be in the dict
    for [spectrum, ref_spectrum] in refer_array:
        data.append([spectrum[:-4], group_dict[ref_spectrum][1],ref_spectrum[:-4]])


    #convert data to DataFrame
    column_names=["SOURCE_FILE", "GROUPNO", "REFERENCE"]
    data=pd.DataFrame(data,columns=column_names)

    data=data.set_index("SOURCE_FILE")


    #get strain names

    #get QualityControlledDBField files
    map_files= [x for x in os.listdir(provider.proj_path) if x[-29:-4]=="QualityControlledDBFields"]

    if len(map_files)==0:
        raise NameMapMissing()

    #convert to DataFrame and gather all namefiles in one frame
    #name_table=[SOURCE_FILE, STRAIN, BRUKER_ID, BRUKER_SCORE]
    name_table=pd.DataFrame()
    for file in map_files:
        name_table=pd.concat([name_table, pd.read_csv(os.path.join(provider.proj_path,file) , sep="\t",usecols=[2,3,35,36])],sort=False)


    name_table=name_table.set_index("SOURCE_FILE")
    name_table=name_table[~name_table.index.duplicated(keep='first')]

    strain_names=name_table[["STRAIN"]]
    strain_names=strain_names.rename(columns={"STRAIN":"REFERENCE_STRAIN"})

    krona_data=pd.concat([data, name_table], axis=1, join='inner')


    #now add reference strain names
    krona_data=krona_data.set_index("REFERENCE")
    krona_data=pd.concat([krona_data,strain_names], axis=1, join='inner')
    krona_data=krona_data[["GROUPNO","REFERENCE_STRAIN","STRAIN","BRUKER_TOPHIT","BRUKER_SCORE"]]


    krona_data.insert(0, '', pd.Series(["CLUSTER"]*len(krona_data.index),index=krona_data.index))


    try:
        outfile=open(outfile_path,"w+")
    except IOError:
        raise IOError
    #krona_data=["CLUSTER", GROUP, REFERENCE_STRAIN, STRAIN, BRUKER_TOPHIT, BRUKER_SCORE]
    pd.DataFrame.to_csv(krona_data,outfile,sep="\t",index=False,header=None)


class NameMapMissing(Exception):
    """
    Exception which is thrown when no valid QualityControlledDBFields files are found.
    """
    def __init__(self):
        message="The project directory has no valid QualityControlledDBFields files."
        super().__init__(message)
