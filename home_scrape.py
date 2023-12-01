

import pandas as pd		#for dataframe work
import re 			#regular expression
import requests			#pulling html code
from bs4 import BeautifulSoup	#parsing html code
import math			#various functions
import json			#to easily translate google api information into dictionaries
import time			#sleep
import os			#playing with directories
import yaml			#importing parameters from config file

#Change directory to ensure things are all saved in same location, and to read config file.
os.chdir('/Users/tjurjevich/Desktop/MATH4300_DeterministicORResearchModels/project/code')

#Import config/yaml file to load address parameters.
with open('project_config.yaml') as configFile:
	params = yaml.safe_load(configFile)

#Brining in unique google key identifier to create API connection with Google API Distance Matrix.
google_api_key = params['google_key']


#Papillion URL (to use for actual model deployment: https://www.remax.com/homes-for-sale/ne/papillion/city/3138295
#Lavista URL (to test with smaller dataset prior to submitted model): https://www.remax.com/homes-for-sale/ne/la-vista/city/3126385
root_page = 'https://www.remax.com/homes-for-sale/ne/papillion/city/3138295'

#Create empty DF to hold listing address and relevant information.
all_listings = pd.DataFrame(columns = ['Address','Price','Bedrooms','Bathrooms','SquareFeet'])


#Function that pulls data for a given page on Remax website.
def scrapeRemaxHomes(URL):

	page_html = requests.get(URL)
	page_parsed = BeautifulSoup(page_html.text, features="lxml")

	#List of homes on page
	listings = page_parsed.find_all('div',class_='listings-card')
	
	#Holds listing information for all homes on current page
	page_listings = []

	for listing in listings:
		
		#Scrape price
		price = re.search('\$[0-9,]+',listing.find('div',class_='card-details').find('div',class_='card-details-slot').text)[0].translate({ord(i): None for i in '$,'})

		#Scrape address; remove Lots that slip through
		if re.match('^LOT.*', listing.find('div',class_='card-details').find('div',class_='card-full-address cursor-pointer').text.strip()):
			address = 'N/A'
		else:
			address = listing.find('div',class_='card-details').find('div',class_='card-full-address cursor-pointer').text.strip()

		#Scrape bedrooms
		try:
			beds = re.search('[0-9]',listing.find('div',class_='card-details').find('div',class_='card-details-stats').p.text)[0]
		except:
			beds = 'N/A'

		#Scrape bathrooms
		try:
			baths = re.search('([0-9]|\.|-)', listing.find('div',class_='card-details').find('div',class_='card-details-stats').p.find_next_sibling().text)[0]
		except:
			baths = 'N/A'

		#Scrape square footage
		try:
			sqft = re.search('[0-9,]+', listing.find('div',class_='card-details').find('div',class_='card-details-stats').p.find_next_siblings()[1].text)[0].replace(',','')
		except:
			sqft = 'N/A'

		#Append the info for each listing to page_listings
		page_listings.append([address, price, beds, baths, sqft])
	
	return pd.DataFrame(page_listings, columns=['Address','Price','Bedrooms','Bathrooms','SquareFeet'])



#Initial step: pull page 1 of data
print('Creating connection with Remax')
all_listings = pd.concat([all_listings, scrapeRemaxHomes(root_page + '/page-1')], axis=0)
print('Scanning page 1...')


#Data will continue to come back as last "available" page. So...start at page 2 and continue calling until we run into "duplicate" data from prior page.
i=2
while i:
	nextPage = scrapeRemaxHomes(f'{root_page}/page-{i}')
	if nextPage.equals(scrapeRemaxHomes(f'{root_page}/page-{i-1}')):
		print('----------Scan complete----------')
		break
	all_listings = pd.concat([all_listings, nextPage], axis=0)
	print(f'Scanning page {i}...')
	i+=1


#Some data cleaning. Removing listings with unavailable specs/address. Also assign a reference number to later be used within gurobi variables.
cleaned_listings = all_listings[(all_listings['Address']!='N/A') & (all_listings['Bedrooms']!='N/A') & (all_listings['Bathrooms']!='N/A') & (all_listings['SquareFeet']!='N/A')].reset_index()
cleaned_listings['ReferenceNumber'] = cleaned_listings.index
cleaned_listings = cleaned_listings.iloc[:, [1,2,3,4,5,6]]



#Added to deal with potential duplicate listing addresses.
if cleaned_listings[cleaned_listings['Address'].duplicated()].shape[0] != 0:
	#could be potentially >1 address
	dupeAddresses = pd.DataFrame(cleaned_listings[cleaned_listings['Address'].duplicated()])
	for i in range(len(dupeAddresses)):
		badRefNum = dupeAddresses.iloc[i].ReferenceNumber
		cleaned_listings = cleaned_listings[cleaned_listings['ReferenceNumber'] != badRefNum]
	#reset indices
	cleaned_listings['ReferenceNumber'] = cleaned_listings.reset_index().index.tolist()


'''
Number of partitions to create (Google API can only handle a max of 25 origins or 25 destinations, AND a total of 100 elements per request, AND 60,000 elements per minute). 
Divisor number: maximum integer i such that i*[number of address parameters] <= 100 to stay within limit of 100 elements per request.
'''
num_calls = math.ceil(len(cleaned_listings)/9)



#Bring in addresses for 11 different destinations.
work = params['work']
classes = params['classes']
gym = params['gym']
wal = params['wal']
sc = params['sc']
jj1 = params['jj1']
jj2 = params['jj2']
jj3 = params['jj3']
rz1 = params['rz1']
rz2 = params['rz2']
ph = params['ph']


#Create destination list, and then create concatenated string from this list to insert into API call.
destination_list = [work, classes, gym, wal, sc, jj1, jj2, jj3, rz1, rz2, ph]
destination_string = (re.sub('( |, )','+',work) + '%7C' + re.sub('( |, )','+',classes) + '%7C' + re.sub('( |, )','+',gym) + '%7C' + re.sub('( |, )','+',wal) + '%7C' + re.sub('( |, )','+',sc) + '%7C' + re.sub('( |, )','+',jj1) + '%7C' + re.sub('( |, )','+',jj2) + '%7C' + re.sub('( |, )','+',jj3) + '%7C' + re.sub('( |, )','+',rz1) + '%7C' + re.sub('( |, )','+',rz2) + '%7C' + re.sub('( |, )','+',ph))

destination_df = pd.DataFrame([[work,'work'],[classes,'classes'],[gym,'gym'],[wal,'wal'],[sc,'sc'],[jj1,'jj1'],[jj2,'jj2'],[jj3,'jj3'],[rz1,'rz1'],[rz2,'rz2'],[ph,'ph']], columns=['Destination','Variable'])

#Will hold all origin/destination distances for entire dataset.
master_distances = []

#Added to get single distance from sams club to walmart (don't need to repeat for each home, since walmart -> sams club distance is constant across all homes).
sc_wal_matrix = requests.get(f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={re.sub('( |, )','+',wal)}&destinations={re.sub('( |, )','+',sc)}&key={google_api_key}")
sc_wal_distance = json.loads(sc_wal_matrix.text)['rows'][0]['elements'][0]['distance']['value']

#Loop through each partition, get request from google, add distances to master_distances.
print(f'\n\nBeginning Google API requests (Requires {num_calls} separate calls).\n')
for i in range(1,num_calls+1):
	
	#Make sure multiplier is same as above divisor.
	start_index = (i-1)*9
	if i == (num_calls+1):
		end_index = len(cleaned_listings)-1
	else:
		#Make sure multiplier is same as above divisor.
		end_index = (i*9)
	temp_origin_list = cleaned_listings.iloc[start_index:end_index]['Address'].values.tolist()
	temp_reference_numbers = cleaned_listings.iloc[start_index:end_index]['ReferenceNumber'].values.tolist()

	temp_origin_string = ''
	for j in range(0,len(temp_origin_list)):
		if j!=len(temp_origin_list)-1:
			temp_origin_string = temp_origin_string + re.sub('( |, )', '+', temp_origin_list[j]) + '%7C'
		else:
			temp_origin_string = temp_origin_string + re.sub('( |, )', '+', temp_origin_list[j])       
	
	temp_distance_matrix = requests.get(f'https://maps.googleapis.com/maps/api/distancematrix/json?origins={temp_origin_string}&destinations={destination_string}&key={google_api_key}')

	for m in range(0,len(temp_origin_list)):
		for n in range(0, len(destination_list)):
			if json.loads(temp_distance_matrix.text)['rows'][m]['elements'][n]['status']=='OK':
				master_distances.append([temp_reference_numbers[m], temp_origin_list[m], destination_list[n], json.loads(temp_distance_matrix.text)['rows'][m]['elements'][n]['distance']['value']])
			else:
				master_distances.append([temp_reference_numbers[m], temp_origin_list[m], destination_list[n], 'NO DISTANCE'])
			
	
	if i!=num_calls:
		print(f'\t\t Partition {i}/{num_calls} complete. Beginning next partition...')
		time.sleep(3)	#to hopefully prevent exceeding 60000 elements per minute
	else:
		print(f'\t\t Partition {i}/{num_calls} complete.')



#Convert master_distances to Data Frame.
master_distances = pd.DataFrame(master_distances, columns = ['HomeNumber','Address','Destination','Meters'])


#Merge together destination_df and master_distances, pivot, then join to cleaned_listings.
exportDF = pd.merge(pd.merge(master_distances, destination_df, on='Destination')[['Address','Meters','Variable']].pivot(index='Address', columns='Variable', values='Meters'), cleaned_listings, on='Address').sort_values(by=['ReferenceNumber'])

#Adding in walmart -> sc distance. Entire vector will obviously be the same value.
sc_wal_matrix = requests.get(f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={re.sub('( |, )','+',wal)}&destinations={re.sub('( |, )','+',sc)}&key={google_api_key}")
sc_wal_distance = json.loads(sc_wal_matrix.text)['rows'][0]['elements'][0]['distance']['value']
exportDF = pd.concat([exportDF, pd.DataFrame([[sc_wal_distance]]*len(exportDF), columns=['sc_to_wal'])], axis=1)

#Select desired column order and save out as CSV.
exportDF[['ReferenceNumber','Address','Price','Bedrooms','Bathrooms','SquareFeet','classes','gym','jj1','jj2','jj3','ph','rz1','rz2','sc','wal','work','sc_to_wal']].to_csv('homeData.csv', index=False)


#Output messages to show what information can be found where.
print('\n\nAll distances can be found in `master_distances`')
print('\n\nAll homes and their specs can be found in `cleaned_listings`')
print('\n\nFinal model-ready dataset (`homeData.csv`) can be found in `/Users/tjurjevich/Desktop/MATH4300_DeterministicORResearchModels/project/code`')


