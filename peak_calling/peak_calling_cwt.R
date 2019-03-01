library(MassSpecWavelet)
args <- commandArgs(TRUE)

#folder <- args[1]
folder <- "FullMS"

dir.create("PKL4DICE")
dir.create("PKL4PPMC_TRIMMED")
dir.create("PKL4PPMC")


for (infile in list.files(folder)){
    print(infile)
    path = sprintf("%s/%s",folder,infile)
    path_out <- sprintf("PKL4DICE/PKL_%s",infile)
    path_trim <- sprintf("PKL4PPMC_TRIMMED/PKLint_%s",infile)
    path_ppmc <- sprintf("PKL4PPMC/PKL_%s",infile)

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

    #adding dummy values at 2000 and 20000 to comply to PPMC peak list standard
    d <- rbind(d,"a"=c(2000,0))
    d <- rbind(d,"b"=c(20000,0))
    d <- d[order(d$V1),]
    write.table(d, file=path_ppmc,append = FALSE,sep="\t", quote=FALSE,row.names=FALSE,col.names=c("Centroid Mass","S/N"))

    #trimming m/z values below 3000 to output in the PKL4PPMC_TRIMMED directory
    trim <- subset(d,V1>3000)
    trim <- rbind(trim,"a"=c(2000,0))
    trim <- rbind(trim,"b"=c(20000,0))
    trim <- trim[order(trim$V1),]
    write.table(trim, file=path_trim,append = FALSE,sep="\t", quote=FALSE,row.names=FALSE,col.names=c("Centroid Mass","S/N"))})
    }
