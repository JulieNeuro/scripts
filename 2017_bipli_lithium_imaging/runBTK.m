function runBTK(subjdir,reconstruct_type,btkdir)

%btkdir="/home/js247994/DocumentsN2/Test2/fbrain-build";
if ~exist('btkdir','var')
    if contains(subjdir,'/')
        btkdir=fullfile('/volatile','BTK-v1.5-Linux-x64');
    else
        btkdir='';
    end
    
end

if ~exist('reconstruct_type','var')
    reconstruct_type='Reconstruct_gridding';
end

%Processeddir='/neurospin/ciclops/projects/BIPLi7/ClinicalData/temp/';
btkfunc=fullfile(btkdir,'Applications','btkNLMDenoising');

if exist(subjdir,'dir')==7
    TPIpathinput=fullfile(subjdir,'TPI',reconstruct_type,'02-PostQuantif');
    TPIpathoutput=fullfile(subjdir,'TPI',reconstruct_type,'03-Filtered');  
    
    if exist(TPIpathinput,'dir')
        if ~exist(TPIpathoutput,'dir')
            mkdir(TPIpathoutput)
        end        
        T= dir(fullfile(TPIpathinput,'*nii'));
        T=T(~ismember({T.name},{'.','..'}));
        for file=T'
            filename=(file.name);
            dotf=(strfind(filename,'.'));
            if strcmp(filename(dotf:dotf+3),'.nii')
                %filename=string(filename);
                %newfilepath=strcat(filename(1:dotf-1),'_filtered.nii');
                filepath=fullfile(TPIpathinput,filename);
                newfilepath=fullfile(TPIpathoutput,string(filename(1:dotf-1))+'.nii');
                newfilepath_filt=fullfile(TPIpathoutput,string(filename(1:dotf-1))+'_filt.nii');
                if exist(btkfunc,'file')
                    codelaunch=strcat(btkfunc,{' '},'-i',{' '},filepath,{' '},'-o',{' '},newfilepath_filt);
                    system(codelaunch{1});
                end
                copyfile(filepath,newfilepath)
            end
        end
    end
    
    trufipathinput=fullfile(subjdir,'Trufi','02-PostQuantif');
    trufipathoutput=fullfile(subjdir,'Trufi','03-Filtered');  
    
    if exist(trufipathinput,'dir')
        if ~exist(trufipathoutput,'dir')
            mkdir(trufipathoutput)
        end        
        T= dir(fullfile(trufipathinput,'*nii*'));
        T=T(~ismember({T.name},{'.','..'}));
        for file=T'
            filename=(file.name);
            dotf=(strfind(filename,'.'));
            if strcmp(filename(dotf:dotf+3),'.nii')
                filepath=fullfile(trufipathinput,filename);
                newfilepath=fullfile(trufipathoutput,string(filename(1:dotf-1))+'.nii');
                newfilepath_filt=fullfile(trufipathoutput,string(filename(1:dotf-1))+'_filt.nii');
                if exist(btkfunc,'dir')
                    codelaunch=strcat(btkfunc,{' '},'-i',{' '},filepath,{' '},'-o',{' '},newfilepath_filt);
                    system(codelaunch{1});
                end
                copyfile(filepath,newfilepath)
            end
        end    
    end
end
