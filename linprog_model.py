#Gurobi model will live in this script
import pandas as pd
import os
import yaml
from gurobipy import *
import re 


#change directory
os.chdir('[your/path/here]')

#import home data that was gathered previously
homeData = pd.read_csv('homeData.csv')

#import config file and parameters
with open('project_config.yaml') as configFile:
	params = yaml.safe_load(configFile)


'''	Create model, assign variables, constraints, objective function	'''

#create model instance
mod = Model('idealHome')

#X{i}: binary, whether or not home i is the home to choose
xi = {}
for i in homeData['ReferenceNumber']:
	xi[i] = mod.addVar(vtype=GRB.BINARY, name=f'x{i}')

'''
#Have to leave out these for free version of Gurobi
gs_trips = {}
for i in homeData['ReferenceNumber']:
	gs_trips[i] = mod.addVar(vtype=GRB.INTEGER, name=f'gs_trips{i}')

jjMin = {}
rzMin = {}
for i in homeData['ReferenceNumber']:
	jjMin[i] = mod.addVar(vtype=GRB.CONTINUOUS, name=f'jjMin{i}')
	rzMin[i] = mod.addVar(vtype=GRB.CONTINUOUS, name=f'rzMin{i}')
'''

#Aggregating across columns instead of using computation in Gurobi model in order to reduce model variables.
jjMin = homeData[['jj1','jj2','jj3']].min(axis=1)
rzMin = homeData[['rz1','rz2']].min(axis=1)


#Constraints

#Max price
mod.addConstr(quicksum(xi[i]*homeData['Price'][i] for i in homeData['ReferenceNumber']) <= params['maxPrice'], name='maxPrice')

#Max/min bedrooms
mod.addConstr(quicksum(xi[i]*homeData['Bedrooms'][i] for i in homeData['ReferenceNumber']) <= params['maxBed'], name='maxBed')
mod.addConstr(quicksum(xi[i]*homeData['Bedrooms'][i] for i in homeData['ReferenceNumber']) >= params['minBed'], name='minBed')

#Max/min bathrooms
mod.addConstr(quicksum(xi[i]*homeData['Bathrooms'][i] for i in homeData['ReferenceNumber']) <= params['maxBath'], name='maxBath')
mod.addConstr(quicksum(xi[i]*homeData['Bathrooms'][i] for i in homeData['ReferenceNumber']) >= params['minBath'], name='minBath')

#Max/min sq footage
mod.addConstr(quicksum(xi[i]*homeData['SquareFeet'][i] for i in homeData['ReferenceNumber']) <= params['maxSqFt'], name='maxSqFt')
mod.addConstr(quicksum(xi[i]*homeData['SquareFeet'][i] for i in homeData['ReferenceNumber']) >= params['minSqFt'], name='minSqFt')

#Only choose one home
mod.addConstr(quicksum(xi[i] for i in homeData['ReferenceNumber']) == 1, name='singleHome')


'''
#Minimum of both restaurants. Have to leave this out for free Gurobi version.
for i in homeData['ReferenceNumber']:
	mod.addGenConstrMin(jjMin[i], [homeData['jj1'][i], homeData['jj2'][i], homeData['jj3'][i]], name=f'jjMin{i}')
	mod.addGenConstrMin(rzMin[i], [homeData['rz1'][i], homeData['rz2'][i]], name=f'rzMin{i}')
'''

mod.update()


#Objective function, based on my personal schedule.
mod.setObjective(quicksum(xi[i]*(6*homeData['work'][i] + 8*homeData['classes'][i] + 8*homeData['gym'][i] + 2*homeData['ph'][i] + homeData['sc'][i] + homeData['wal'][i] + homeData['sc_to_wal'][i] + 2*jjMin[i] + 2*rzMin[i]) for i in homeData['ReferenceNumber']))
mod.update()



#Optimize (minimize)
mod.ModelSense = 1
mod.optimize()

#Add output, give in both meters and miles.
conv = 1609.34
for i in range(0,len(mod.getVars())):
	if mod.getVars()[i].X == 1.0:
		print(f'\n\n\n\nOptimal home (reference number): {i}.\n')
		print(f'\tWeekly travel distance (meters/miles): {int(mod.ObjVal)}, {round(mod.ObjVal/conv,2)}')
		print(f"\t\tWork: {homeData['work'][i]}, {round(homeData['work'][i]/conv,2)}")
		print(f"\t\tUNO: {homeData['classes'][i]}, {round(homeData['classes'][i]/conv,2)}")
		print(f"\t\tGym: {homeData['gym'][i]}, {round(homeData['gym'][i]/conv,2)}")
		print(f"\t\tParent's House: {homeData['ph'][i]}, {round(homeData['ph'][i]/conv,2)}")
		print(f"\t\tSam's Club: {homeData['sc'][i]}, {round(homeData['sc'][i]/conv,2)}")
		print(f"\t\tWalmart: {homeData['wal'][i]}, {round(homeData['wal'][i]/conv,2)}")
		print(f"\t\tClosest Jimmy John's: {jjMin[i]}, {round(jjMin[i]/conv,2)}")
		print(f"\t\tClosest Runza: {rzMin[i]}, {round(rzMin[i]/conv,2)}")
		print(f"\n\tHome specs...")
		print(f"\t\tListing Price: ${homeData['Price'][i]}")
		print(f"\t\tSquare Footage: {homeData['SquareFeet'][i]}")
		print(f"\t\tTotal Bedrooms: {homeData['Bedrooms'][i]}")
		print(f"\t\tTotal Bathrooms: {homeData['Bathrooms'][i]}")

