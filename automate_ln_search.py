import lexisnexis_analysis
from lexisnexis_analysis import conduct_analysis
import glob, os
#------------------------------------------------------------------------------
def main():
	#Determine credentials
	with open("access.txt") as f:
		content = f.readlines()
	username = content[0].replace("\n", "")
	password = content[1].replace("\n", "")
	location = content[2].replace("\n", "")



	for search_file in glob.glob("*.srch"):
		try:
			x = open(search_file, "rb").readlines()
			query = x[0].replace("\n","").replace("\r","")
			since = x[1].replace("\n","").replace("\r","")
			until = x[2].replace("\n","").replace("\r","")
			
			query_items = query.split(" ")
			reassembled_query = []
			for item in query_items:
				if ((item[0] != "-") and (item != "lang:en")):
					reassembled_query.append(item)
					
			new_query = " ".join(reassembled_query)
		
			print "\n--------- Executing search ",search_string, location, username, password, "1"," ---------\n"
			search_string = "DATE(>={0} and <={1}) and HEADLINE({2}) not SUBJECT(patent or advert!)".format(since, until, new_query)
			#search_string, access_url, username, password, starting_page
			lexisnexis_analysis.conduct_analysis(search_string, location, username, password, 1)
			
		except (KeyboardInterrupt, SystemExit):
			print "Process aborted."
			raise
			
		except:
			print "Error at ", x

#------------------------------------------------------------------------------
if __name__ == "__main__":
	''' The usual boilerplate... '''
	main()