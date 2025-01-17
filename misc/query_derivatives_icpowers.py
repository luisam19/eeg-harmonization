import json
from bids import BIDSLayout
import numpy as np
import re
import pandas as pd
from bids.layout import parse_file_entities
from datasets import SRM as THE_DATASET


input_path = THE_DATASET.get('input_path',None)
task = THE_DATASET.get('layout',None).get('task',None)
group_regex = THE_DATASET.get('group_regex',None)
name = THE_DATASET.get('name',None)
runlabel = THE_DATASET.get('run-label','')

data_path = input_path
layout = BIDSLayout(data_path,derivatives=True)
layout.get(scope='derivatives', return_type='file')



eegs_powers = layout.get(extension='.txt',task=task,suffix='powers', return_type='filename')
eegs_powers = [x for x in eegs_powers if f'desc-component[{runlabel}]' in x]
list_subjects = []
for i in range(len(eegs_powers)):
    with open(eegs_powers[i], 'r') as f:
        data = json.load(f)

    ncomps = np.array(data['ics_power']).shape[1]
    comp_labels = ['C'+str(i+1) for i in range(ncomps)]
    icpowers = np.array(data['ics_power'])
    bandas = data['bands']

    datos_1_sujeto = {}
    info_bids_sujeto = parse_file_entities(eegs_powers[i])
    datos_1_sujeto['subject'] = info_bids_sujeto['subject']
    if group_regex:
        regex = re.search('(.+).{3}',info_bids_sujeto['subject'])
        datos_1_sujeto['group'] = regex.string[regex.regs[-1][0]:regex.regs[-1][1]]
    try:
        datos_1_sujeto['visit'] = info_bids_sujeto['session']
    except:
        pass
    datos_1_sujeto['condition'] = info_bids_sujeto['task']
    for b,band in enumerate(bandas):
        for c in range(ncomps):
            datos_1_sujeto[f'{comp_labels[c]}_r{band.title()}']=icpowers[b,c]
    list_subjects.append(datos_1_sujeto)


df = pd.DataFrame(list_subjects)
df.to_excel(r'E:\Academico\Universidad\Posgrado\Tesis\Datos\longitudinal_data_icpowers_'+name+'.xlsx')
