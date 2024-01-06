# ======================================== #
# Class that adds the policy scenarios from ENGAGE
# ======================================== #

# =========================================================== #
# PREAMBULE
# Put in packages that we need
# =========================================================== #

from pathlib import Path
import yaml
import numpy as np
import pandas as pd
import xarray as xr
import json

# =========================================================== #
# CLASS OBJECT
# =========================================================== #

class policyscenadding(object):

    # =========================================================== #
    # =========================================================== #

    def __init__(self, xrtot):
        print("# ==================================== #")
        print("# Initializing policyscenadding class        #")
        print("# ==================================== #")

        self.current_dir = Path.cwd()

        # Read in Input YAML file
        with open(self.current_dir / 'input.yml') as file:
            self.settings = yaml.load(file, Loader=yaml.FullLoader)
        self.xr_total = xrtot

    # =========================================================== #
    # =========================================================== #

    def read_engage_data(self):
        print("- Read ENGAGE scenarios and change region namings")
        df_eng = pd.read_csv(self.settings['paths']['data']['external']+'ENGAGE/PolicyScenarios/ENGAGE_internal_2610_onlyemis.csv')
        #df_eng = pd.read_excel(self.settings['paths']['data']['external']+'ENGAGE/PolicyScenarios/Zenodo_10_2023.xlsx', sheet_name='data')
        df_eng = df_eng[df_eng.Variable == 'Emissions|Kyoto Gases'] # Currently, not in the database?
        df_eng = df_eng.reset_index(drop=True)
        regions_df = np.array(df_eng.Region)
        regions_df[regions_df == "Argentine Republic"] = 'ARG'
        regions_df[regions_df == "Canada"] = 'CAN'
        regions_df[regions_df == "Commonwealth of Australia"] = 'AUS'
        regions_df[regions_df == "Federative Republic of Brazil"] = 'BRA'
        regions_df[regions_df == "People's Repulic of China"] = 'CHN'
        regions_df[regions_df == "European Union (28 member countries)"] = 'EU'
        regions_df[regions_df == "Republic of India"] = 'IND'
        regions_df[regions_df == "Republic of Indonesia"] = 'IDN'
        regions_df[regions_df == "State of Japan"] = 'JPN'
        regions_df[regions_df == "Russian Federation"] = 'RUS'
        regions_df[regions_df == "Kingdom of Saudi Arabia"] = 'SAU'
        regions_df[regions_df == "Republic of South Africa"] = 'ZAF'
        regions_df[regions_df == "Republic of Korea (South Korea)"] = 'KOR'
        regions_df[regions_df == "United Mexican States"] = 'MEX'
        regions_df[regions_df == "Republic of Turkey"] = 'TUR'
        regions_df[regions_df == "United States of America"] = 'USA'
        regions_df[regions_df == "Viet Nam "] = 'VNM'
        df_eng.Region = regions_df
        df_new = df_eng[~df_eng.index.isin(np.where((df_eng.Scenario == "GP_CurPol_T45") & (df_eng.Model == "COFFEE 1.5"))[0])]
        self.df_eng = df_new

    # =========================================================== #
    # =========================================================== #

    def filter_and_convert(self):
        print("- Filter correct scenarios and convert to xarray object")
        curpol = "GP_CurPol_T45"
        ndc = "GP_NDC2030_T45"
        nz = "GP_Glasgow"
        df_eng_ref = self.df_eng[['Model', 'Scenario', 'Region']+list(self.df_eng.keys()[5:])]
        df_eng_ref = df_eng_ref[df_eng_ref.Scenario.isin([curpol, ndc, nz])]
        scen = np.array(df_eng_ref.Scenario)
        scen[scen == ndc] = 'NDC'
        scen[scen == curpol] = 'CurPol'
        scen[scen == nz] = 'NetZero'
        reg = np.array(df_eng_ref.Region)
        reg[reg == 'World'] = 'EARTH'
        df_eng_ref['Scenario'] = scen
        df_eng_ref['Region'] = reg
        dummy = df_eng_ref.melt(id_vars=["Scenario", "Model", "Region"], var_name="Time", value_name="Value")
        dummy['Time'] = np.array(dummy['Time'].astype(int))
        dummy = dummy.set_index(["Scenario", "Model", "Region", "Time"])
        xr_eng = xr.Dataset.from_dataframe(dummy)
        xr_eng = xr_eng.reindex(Time = np.arange(1850, 2101))
        self.xr_eng = xr_eng.interpolate_na(dim="Time", method="linear")

    # =========================================================== #
    # =========================================================== #

    def add_to_xr(self):
        print("- Add to overall xrobject")
        xr_total = self.xr_total.assign(NDC = self.xr_eng['Value'].sel(Scenario='NDC'))
        xr_total = xr_total.assign(CurPol = self.xr_eng['Value'].sel(Scenario='CurPol'))
        xr_total = xr_total.assign(NetZero = self.xr_eng['Value'].sel(Scenario='NetZero'))
        xr_total = xr_total.reindex(Time = np.arange(1850, 2101))
        self.xr_total = xr_total.interpolate_na(dim="Time", method="linear")
        xr_total_onlyalloc = self.xr_total.drop_vars(['Population', 'GDP', 'GHG_hist', 'CO2_hist', 'GHG_globe', 'GHG_base', 'GHG_ndc', 'N2O_hist', 'CH4_hist', 'Budget', "CH4_globe", "N2O_globe", "GHG_hist_all"])
        xr_total_onlyalloc.to_netcdf(self.settings['paths']['data']['datadrive']+'xr_policyscen.nc')