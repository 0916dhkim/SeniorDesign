import pandas
import beam
from math import fabs
import numpy
import re
import rebar
from multiprocessing import Pool
from constants import *


bar_name_format = re.compile(r'(?P<id>\d+)\s*/\s*(?P<minmax>MAX|MIN)')
section_format = re.compile(r'(?P<b>\d+)\s*x\s*(?P<h>\d+)')


def parse_bar_by_row(row):
    m = bar_name_format.search(row['Bar'])
    return int(m.group('id')), m.group('minmax')


def parse_bar(df):
    df['ID'], df['MINMAX'] = zip(*df.apply(parse_bar_by_row, axis=1))
    return df.drop(['Bar'], axis=1)


def unit_conversion(df):
    # TODO Implement.
    return df.rename(columns={
        'FX (kip)': 'FX',
        'FY (kip)': 'FY',
        'FZ (kip)': 'FZ',
        'MX (kip-ft)': 'MX',
        'MY (kip-ft)': 'MY',
        'MZ (kip-ft)': 'MZ',
        'Length (ft)': 'L',
        'RECT_BF (in)': 'B',
        'RECT_HT (in)': 'H'})


def distinguish_minmax_by_row(row):
    min_fx = numpy.nan
    min_fy = numpy.nan
    min_fz = numpy.nan
    min_mx = numpy.nan
    min_my = numpy.nan
    min_mz = numpy.nan
    max_fx = numpy.nan
    max_fy = numpy.nan
    max_fz = numpy.nan
    max_mx = numpy.nan
    max_my = numpy.nan
    max_mz = numpy.nan
    if row['MINMAX'] == 'MIN':
        min_fx = row['FX']
        min_fy = row['FY']
        min_fz = row['FZ']
        min_mx = row['MX']
        min_my = row['MY']
        min_mz = row['MZ']
    else:
        max_fx = row['FX']
        max_fy = row['FY']
        max_fz = row['FZ']
        max_mx = row['MX']
        max_my = row['MY']
        max_mz = row['MZ']

    return (min_fx, max_fx,
            min_fy, max_fy,
            min_fz, max_fz,
            min_mx, max_mx,
            min_my, max_my,
            min_mz, max_mz)


def distinguish_minmax(df):
    (df['MIN FX'], df['MAX FX'],
     df['MIN FY'], df['MAX FY'],
     df['MIN FZ'], df['MAX FZ'],
     df['MIN MX'], df['MAX MX'],
     df['MIN MY'], df['MAX MY'],
     df['MIN MZ'], df['MAX MZ']) = zip(*df.apply(distinguish_minmax_by_row, axis=1))
    return df.drop(['MINMAX', 'FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'], axis=1)


def beam_calculate_required_reinforcement_by_row(row):
    print('Required reinforcement [bar #%d]' % row['ID'])
    area_top = numpy.nan
    area_bottom = numpy.nan
    # Calculate for positive moment.
    if row['MAX MY'] > 0:
        area_bottom, area_top = beam.doubly_reinforced_area(row['B'],
                                                            row['H'] - C_C,
                                                            C_C,
                                                            row['MAX MY'])

    # Calculate for negative moment.
    if row['MIN MY'] < 0:
        solution = beam.doubly_reinforced_area(row['B'], row['H'] - C_C, C_C, -row['MIN MY'])
        area_top = max(area_top, solution[0])
        area_bottom = max(area_bottom, solution[1])

    return area_top, area_bottom


def beam_calculate_required_reinforcement(df):
    # Calculate required reinforcement area in parallel.
    # Number of processes generated is equal to cpu count by default.
    with Pool() as p:
        df = df.assign(**{'AREA TOP': numpy.nan, 'AREA BOTTOM': numpy.nan})
        df.loc[:,['AREA TOP','AREA BOTTOM']] = p.map(beam_calculate_required_reinforcement_by_row,
                                                   df.T.to_dict().values())
    return df


def beam_calculate_stirrup_spacing_by_row(row):
    print('Stirrup spacing [bar #%d]' % row['ID'])
    case1 = beam.shear_spacing(row['B'], row['H']-C_C, row['H'], row['MAX FX'], row['MAX FZ'])
    case2 = beam.shear_spacing(row['B'], row['H']-C_C, row['H'], row['MIN FX'], row['MIN FZ'])
    return min(case1, case2)


def beam_calculate_stirrup_spacing(df):
    with Pool() as p:
        df.insert(len(df.columns), 'STIRRUP SPACING', p.map(beam_calculate_stirrup_spacing_by_row, df.T.to_dict().values()))
    return df


def beam_design_reinforcement_by_row(row):
    print('Reinforcement design [bar #%d]' % row['ID'])
    if row['AREA TOP'] is numpy.nan or row['AREA BOTTOM'] is numpy.nan:
        # If required area calculation has failed, put minimum reinforcement.
        return rebar.min_num, 2, rebar.min_num, 2

    # Try to fit rebars.
    top = rebar.fit_bars(row['AREA TOP'], row['B'] - 2 * C_C, D_AGG)
    bottom = rebar.fit_bars(row['AREA BOTTOM'], row['B'] - 2 * C_C, D_AGG)

    return top['bar'], top['count'], rebar.area[top['bar']]*top['count'],\
           bottom['bar'], bottom['count'], rebar.area[bottom['bar']]*bottom['count']


def beam_design_reinforcement(df):
    # Determine number and type of rebars.
    with Pool() as p:
        df['BAR TYPE TOP'],df['BAR COUNT TOP'],df['AREA TOP'],\
        df['BAR TYPE BOTTOM'],df['BAR COUNT BOTTOM'],df['AREA BOTTOM']\
        = zip(*p.map(beam_design_reinforcement_by_row, df.T.to_dict().values()))
    return df


def beam_check_required_strength_by_row(row):
    print('Required strength check [bar #%d]' % row['ID'])
    # Check positive moment case and negative moment case.
    efficiency_max_my = 1
    if row['MAX MY'] > 0:
        efficiency_max_my = beam.check_doubly_reinforced_design(row['B'],
                                                                row['H'] - C_C,
                                                                C_C,
                                                                row['AREA BOTTOM'],
                                                                row['AREA TOP'],
                                                                row['MAX MY'])
    efficiency_min_my = 1
    if row['MIN MY'] < 0:
        efficiency_min_my = beam.check_doubly_reinforced_design(row['B'],
                                                                row['H'] - C_C,
                                                                C_C,
                                                                row['AREA TOP'],
                                                                row['AREA BOTTOM'],
                                                                -row['MIN MY'])

    return efficiency_min_my, efficiency_max_my


def beam_check_required_strength(df):
    with Pool() as p:
        df['EFFICIENCY MIN MY'],df['EFFICIENCY MAX MY'] = zip(*p.map(beam_check_required_strength_by_row,
                                                              df.T.to_dict().values()))
    return df


def process_data(all):
    all = parse_bar(all)
    all = unit_conversion(all)
    all = distinguish_minmax(all)
    all = all.groupby(['ID']).first().reset_index()

    # Process beam forces.
    beam_dataframe = all[(all['Type'] == 'RC Beam')]
    beam_dataframe = beam_calculate_required_reinforcement(beam_dataframe)
    beam_dataframe = beam_calculate_stirrup_spacing(beam_dataframe)
    beam_dataframe = beam_design_reinforcement(beam_dataframe)
    beam_dataframe = beam_check_required_strength(beam_dataframe)
    beam_dataframe = beam_dataframe.groupby(['ID']).first()
    print(beam_dataframe)

    # Process column forces.
    column_dataframe = all[(all['Type'] == 'RC Column')]
    column_dataframe = column_dataframe.groupby(['ID']).first()
    print(column_dataframe)

    # Write result to output file.
    beam_dataframe.to_csv('beam.csv')
    column_dataframe.to_csv('column.csv')

if __name__ == "__main__":
    # Process csv file.
    process_data(pandas.read_csv('data/forces.csv')[522:600])
    print('Analysis complete')
