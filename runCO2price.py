import os
import pyomo.environ
import shutil
import urbs
from datetime import datetime
from pyomo.opt.base import SolverFactory

# SCENARIOS

def scenario_generator_CO2price(scenario_name, value):
    # e.g. data[commodity].loc[('Campus', 'CO2', 'Env'), 'price']
    
    def scenario(data):
        data['commodity'].loc[('Campus', 'CO2', 'Env'), 'price'] = value
        return data
        
    scenario.__name__ = scenario_name  # used for result filenames
    return scenario

def prepare_result_directory(result_name):
    """ create a time stamped directory within the result folder """
    # timestamp for result directory
    now = datetime.now().strftime('%Y%m%dT%H%M')

    # create result directory if not existent
    result_dir = os.path.join('result', '{}-{}'.format(result_name, now))
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    return result_dir


def setup_solver(optim, logfile='solver.log'):
    """ """
    if optim.name == 'gurobi':
        # reference with list of option names
        # http://www.gurobi.com/documentation/5.6/reference-manual/parameters
        optim.set_options("logfile={}".format(logfile)) 
        # optim.set_options("timelimit=7200")  # seconds
        # optim.set_options("mipgap=5e-4")  # default = 1e-4
    elif optim.name == 'glpk':
        # reference with list of options
        # execute 'glpsol --help'
        optim.set_options("log={}".format(logfile))
        # optim.set_options("tmlim=7200")  # seconds
        # optim.set_options("mipgap=.0005")
    else:
        print("Warning from setup_solver: no options set for solver "
              "'{}'!".format(optim.name))
    return optim

def run_scenario(input_file, timesteps, scenario, result_dir, plot_periods={}):
    """ run an urbs model for given input, time steps and scenario

    Args:
        input_file: filename to an Excel spreadsheet for urbs.read_excel
        timesteps: a list of timesteps, e.g. range(0,8761)
        scenario: a scenario function that modifies the input data dict
        result_dir: directory name for result spreadsheet and plots

    Returns:
        the urbs model instance
    """

    # scenario name, read and modify data for scenario
    sce = scenario.__name__
    data = urbs.read_excel(input_file)
    data = scenario(data)

    # create model
    prob = urbs.create_model(data, timesteps)

    # refresh time stamp string and create filename for logfile
    now = prob.created
    log_filename = os.path.join(result_dir, '{}.log').format(sce)

    # solve model and read results
    optim = SolverFactory('gurobi')  # cplex, glpk, gurobi, ...
    optim = setup_solver(optim, logfile=log_filename)
    result = optim.solve(prob, tee=True)

    # copy input file to result directory
    shutil.copyfile(input_file, os.path.join(result_dir, input_file))
	
	# write report to spreadsheet
    urbs.report(
        prob,
        os.path.join(result_dir, '{}.xlsx').format(sce),
        prob.com_demand, prob.sit)

    urbs.result_figures(
        prob, 
        os.path.join(result_dir, '{}'.format(sce)),
        plot_title_prefix=sce.replace('_', ' ').title(),
        periods=plot_periods, power_unit='kW', energy_unit='kWh',
        figure_size=(24,4))
    return prob

if __name__ == '__main__':
    input_file = '1Node.xlsx'
    result_name = os.path.splitext(input_file)[0]  # cut away file extension
    result_dir = prepare_result_directory(result_name)  # name + time stamp

    # simulation timesteps
    (offset, length) = (3000, 1*24)  # time step selection
    timesteps = range(offset, offset+length+1)
    
    # plotting timesteps default
    # periods = {
        # '01-jan': range(   1,  745),
        # '02-feb': range( 745, 1417),
        # '03-mar': range(1417, 2161),
        # '04-apr': range(2161, 2881),
        # '05-may': range(2881, 3625),
        # '06-jun': range(3625, 4345),
        # '07-jul': range(4345, 5089),
        # '08-aug': range(5089, 5833),
        # '09-sep': range(5833, 6553),
        # '10-oct': range(6553, 7297),
        # '11-nov': range(7297, 8017),
        # '12-dec': range(8017, 8761)
    # }
    
    # plotting timesteps for testing
    periods = {
        'test': range(3000, 3024)
    }
    
    # add or change plot colors
    my_colors = {
        'Demand': (0, 0, 0),
        'Diesel generator': (218, 215, 203),
        'Electricity': (0, 51, 89),
        'Photovoltaics': (0, 101, 189),
        'Storage': (100, 160, 200)}
    for country, color in my_colors.items():
        urbs.COLORS[country] = color

    # select scenarios to be run
    scenarios = [
        scenario_generator_CO2price('s01', 0),
        scenario_generator_CO2price('s02', 150),
        scenario_generator_CO2price('s03', 1000)]

    for scenario in scenarios:
        prob = run_scenario(input_file, timesteps, scenario, 
                            result_dir, plot_periods=periods)
