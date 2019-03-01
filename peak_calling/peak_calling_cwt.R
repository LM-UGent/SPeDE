library(MassSpecWavelet)
args <- commandArgs(TRUE)

folder <- args[1]
dir.create("PKL4DICE")

for (infile in list.files(folder)){
    print(infile)
    path = sprintf("%s/%s",folder,infile)
    path_out <- sprintf("PKL4DICE/PKL_%s",infile)

    #Loading example data.
    MS_data <- read.csv(path, sep="",header=FALSE)
    #converting m/z values to a vector
    MS.test <- as.vector(MS_data[,2])

    SNR.Th <- 3 #setting the signal to noise ratio threshold
    amp.Th <- 0.0001 #setting the minimum required relative amplitude threshold of peaks
    try({peakInfo <- peakDetectionCWT(MS.test,SNR.Th=SNR.Th,ampTh=ampTh)
    majorPeakInfo <- peakInfo$majorPeakInfo
    betterPeakInfo <- tuneInPeakInfo(MS.test,majorPeakInfo)
    peakIndex <- betterPeakInfo$peakIndex

    #plotPeak(MS.test, peakIndex, main=paste('Identified peaks with SNR >', SNR.Th)) 
    d <- MS_data[peakIndex,][1] #dataframe of peak positions and intensity values
    d$SNR <- betterPeakInfo$peakSNR

    #writing peak list in csv format
    write.table(d, file=path_out,append = FALSE,sep="\t", quote=FALSE,row.names=FALSE,col.names=c("Centroid Mass","S/N"))
