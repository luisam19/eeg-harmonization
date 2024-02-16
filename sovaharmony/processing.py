from sovaflow.flow import preflow,get_ics_power_derivatives,get_power_derivates,crop_raw_data,run_reject
from sovaflow.utils import cfg_logger,get_spatial_filter
import mne
import json
import os
imporrt numpy as np
from bids import BIDSLayout
from datetime import datetime
import numpy as np
import pandas as pd
from sovaharmony.info import info as info_dict

def get_derivative_path(layout,eeg_file,output_entity,suffix,output_extension,bids_root,derivatives_root):
    entities = layout.parse_file_entities(eeg_file)
    derivative_path = eeg_file.replace(bids_root,derivatives_root)
    derivative_path = derivative_path.replace(entities['extension'],'')
    derivative_path = derivative_path.split('_')
    desc = 'desc-' + output_entity
    derivative_path = derivative_path[:-1] + [desc] + [suffix]
    derivative_path = '_'.join(derivative_path) + output_extension 
    return derivative_path

def default(obj):
    if type(obj).__module__ == np.__name__:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj.item()
    raise TypeError('Unknown type:', type(obj))

def write_json(data,filepath):
    with open(filepath, 'w') as fp:
        json.dump(data, fp,indent=4,default=default)

def harmonize(THE_DATASET,fast_mode=False):
    """Process a single bids dataset.
    
    Inputs:
    
    THE_DATASET: dictionary with the following keys:
    {
    'name': str, Name of the dataset
    'input_path': str, Path of the bids input dataset,
    'layout': dict, Arguments of the filter to apply for querying eegs to be processed. See pybids BIDSLayout arguments.
    'args': dict, Arguments of the sovaflow.preflow function in dictionary form.
    'group_regex': str, regex string to obtain the group from the subject id (if applicable) else None
    'events_to_keep': list, list of events to keep for the analysis
    'run-label': str, label associated with the run of the algorithm so that the derivatives are not overwritten.
    'channels': list, channel labels to keep for analysis in the order wanted. Use standard 1005 names in UPPER CASE
    'spatial_filter': str, spatial filter to be used for component analysis. Should correspond to those in sovaflow. One of '53x53', '58x25', '62x19'
    }
    
    Example:
    THE_DATASET = {
    'name':'BIOMARCADORES',
    'input_path':'E:/Datos/BASESDEDATOS/BIOMARCADORES_BIDS',
    'layout':{'extension':'.vhdr', 'task':'OE','suffix':'eeg', 'return_type':'filename'},
    'args':{'line_freqs':[60]},
    'group_regex':'(.+).{3}',
    'events_to_keep':None,
    'run-label':'restEC'
    'channels':['FP1', 'FPZ', 'FP2', 'AF3', 'AF4', 'F7', 'F5', 'F3', 'F1', 'FZ', 'F2', 'F4', 'F6', 'F8', 'FC5', 'FC3', 'FC1', 'FCZ', 'FC2', 'FC4', 'FC6', 'T7', 'C5', 'C3', 'C1', 'CZ', 'C2', 'C4', 'C6', 'T8', 'TP7', 'CP5', 'CP3', 'CP1', 'CPZ', 'CP2', 'CP4', 'CP6', 'TP8', 'P7', 'P5', 'P3', 'P1', 'PZ', 'P2', 'P4', 'P6', 'P8', 'PO7', 'PO5', 'PO3', 'POZ', 'PO4', 'PO6', 'PO8', 'O1', 'OZ', 'O2']
    'spatial_filter':'58x25',
    }

    Output:

    list of str, filepaths of files with errors
    """

    # Dataset dependent inputs
    input_path = THE_DATASET.get('input_path',None)
    default_channels = ['FP1', 'FPZ', 'FP2', 'AF3', 'AF4', 'F7', 'F5', 'F3', 'F1', 'FZ', 'F2', 'F4', 'F6', 'F8', 'FC5', 'FC3', 'FC1', 'FCZ', 'FC2', 'FC4', 'FC6', 'T7', 'C5', 'C3', 'C1', 'CZ', 'C2', 'C4', 'C6', 'T8', 'TP7', 'CP5', 'CP3', 'CP1', 'CPZ', 'CP2', 'CP4', 'CP6', 'TP8', 'P7', 'P5', 'P3', 'P1', 'PZ', 'P2', 'P4', 'P6', 'P8', 'PO7', 'PO5', 'PO3', 'POZ', 'PO4', 'PO6', 'PO8', 'O1', 'OZ', 'O2']
    channels = THE_DATASET.get('channels',default_channels)
    layout_dict = THE_DATASET.get('layout',None)
    def_spatial_filter='58x25'
    # Inputs not dataset dependent
    spatial_filter = get_spatial_filter(THE_DATASET.get('spatial_filter',def_spatial_filter))

    # Static Params
    pipeline = 'sovaharmony'
    pipelabel = '['+THE_DATASET.get('run-label', '')+']'
    layout = BIDSLayout(input_path)
    bids_root = layout.root
    output_path = os.path.join(bids_root,'derivatives',pipeline)

    eegs = layout.get(**layout_dict)

    derivatives_root = os.path.join(layout.root,'derivatives',pipeline)
    log_path = os.path.join(derivatives_root,'code')
    os.makedirs(log_path, exist_ok=True)
    logger,currentdt = cfg_logger(log_path)


    e = 0
    archivosconerror = []

    description = layout.get_dataset_description()
    desc_pipeline = "sovaharmony, a harmonization eeg pipeline using the bids standard"
    description['GeneratedBy']=[info_dict]
    write_json(description,os.path.join(derivatives_root,'dataset_description.json'))
    num_files = len(eegs)
    for i,eeg_file in enumerate(eegs):
        try:
            logger.info(f"File {i+1} of {num_files} ({(i+1)*100/num_files}%) : {eeg_file}")

            wica_path = get_derivative_path(layout,eeg_file,'wica','eeg','.fif',bids_root,derivatives_root)
            prep_path = get_derivative_path(layout,eeg_file,'prep','eeg','.fif',bids_root,derivatives_root)
            
            stats_path = get_derivative_path(layout,eeg_file,'label','stats','.txt',bids_root,derivatives_root)
            
            power_path = get_derivative_path(layout,eeg_file,'channel'+pipelabel,'powers','.txt',bids_root,derivatives_root)
            icpowers_path = get_derivative_path(layout,eeg_file,'component'+pipelabel,'powers','.txt',bids_root,derivatives_root)
            reject_path = get_derivative_path(layout,eeg_file,'reject'+pipelabel,'eeg','.fif',bids_root,derivatives_root)

            os.makedirs(os.path.split(power_path)[0], exist_ok=True)

            json_dict = {"Description":desc_pipeline,"RawSources":[eeg_file.replace(bids_root,'')],"Configuration":THE_DATASET}
            json_dict["Sources"]=wica_path.replace(bids_root,'')

            if os.path.isfile(wica_path) and os.path.isfile(prep_path):
                logger.info(f'{prep_path} and {wica_path} already existed, skipping...')
            else:
                raw = mne.io.read_raw(eeg_file,preload=True)
                signal,prep_signal,stats=preflow(raw,correct_montage=channels,fast_mode=fast_mode,**THE_DATASET.get('args',{}))
                
                del raw
                
                prep_signal.save(prep_path ,split_naming='bids', overwrite=True)
                del prep_signal
                
                signal.save(wica_path ,split_naming='bids', overwrite=True)
                
                write_json(json_dict,wica_path.replace('.fif','.json'))
                write_json(json_dict,prep_path.replace('.fif','.json'))

                write_json(json_dict,stats_path.replace('label','prep').replace('.txt','.json'))
                write_json(json_dict,stats_path.replace('label','wica').replace('.txt','.json'))
                
                write_json(stats.get('prep',{}),stats_path.replace('label','prep'))
                write_json(stats.get('wica',{}),stats_path.replace('label','wica'))
                
            if THE_DATASET.get('events_to_keep', None) is not None:
                events_file = os.path.splitext(eeg_file)[0].replace('_eeg','_events.tsv')
                events_raw=pd.read_csv(events_file,sep='\t')
                samples = events_raw['sample'].tolist()
                values = events_raw['value'].tolist()
                events = list(zip(values,samples))
                events_to_keep = THE_DATASET.get('events_to_keep', None)
            else:
                events = None
                events_to_keep = None

            if os.path.isfile(reject_path):    
                logger.info(f'{reject_path} already existed, skipping...')
            else:
                signal = mne.io.read_raw(wica_path,preload=True)
                signal = crop_raw_data(signal,events, events_to_keep)
                signal,reject_info = run_reject(signal)
                signal.save(reject_path ,split_naming='bids', overwrite=True)
                write_json(json_dict,reject_path.replace('.fif','.json'))
                write_json(json_dict,stats_path.replace('label','reject'+pipelabel).replace('.txt','.json'))
                write_json(reject_info,stats_path.replace('label','reject'+pipelabel))
            
            if os.path.isfile(power_path):
                logger.info(f'{power_path}) already existed, skipping...')
            else:
                power_dict = get_power_derivates(signal)
                write_json(power_dict,power_path)
                write_json(json_dict,power_path.replace('.txt','.json'))

            if not os.path.isfile(icpowers_path) and spatial_filter is not None:
                ic_powers_dict = get_ics_power_derivatives(signal,spatial_filter)
                write_json(ic_powers_dict,icpowers_path)
                write_json(json_dict,icpowers_path.replace('.txt','.json'))

            else:
                logger.info(f'{icpowers_path}) already existed or no spatial filter given, skipping...')


        except Exception as error:
            e+=1
            logger.exception(f'Error for {eeg_file}')
            archivosconerror.append(eeg_file)
            print(error)
            pass
    return archivosconerror
