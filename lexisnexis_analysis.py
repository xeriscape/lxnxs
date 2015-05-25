# -*- coding: utf-8 -*-

from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from time import gmtime, strftime
import codecs, cStringIO
import csv
import datetime
import glob
import hashlib
import lxml
import os
import re
import selenium
import sqlite3
import sys
import time
import shlex, subprocess




#--------------------------------------------------------------------------------------
''' Clean string by removing line breaks, semicolons, pipes; force down to ASCII. '''
def stringscrub(irnput): #
	retval = irnput.replace("\n", "").replace("\r", "").replace(";", ",").replace("|", ",")
	return retval.encode('ascii', 'ignore')
#--------------------------------------------------------------------------------------
''' Set up a basic chrome driver to be found at the specified location. '''
def set_up_browser(chromedriver): 
	os.environ["webdriver.chrome.driver"] = chromedriver
	opt = webdriver.ChromeOptions()
	driver = webdriver.Chrome(chromedriver, chrome_options=opt)
	
	return driver
#--------------------------------------------------------------------------------------
''' Execute the steps neccessary for the login procedure. '''
def handle_login(driven_browser, LN_url, LN_username, LN_password):
	#Go to log in page
	driven_browser.get(LN_url)
	
	#Fill in information
	login = driven_browser.find_element_by_name("User")
	login.send_keys(LN_username)
	password = driven_browser.find_element_by_name("Password")
	password.send_keys(LN_password)
	driven_browser.find_element_by_xpath("//*[@type='submit']").click()
	
	time.sleep(2.5) #Give the website some time to process this
	
	#Accept terms
	try:
		driven_browser.find_element_by_xpath("//a[contains(@href, 'submitterms')]").click()
	
	except:
		print "Terms already accepted, probably"

	#Login handled!
	return True
#--------------------------------------------------------------------------------------
''' Execute the steps neccessary to begin searching. '''	
def execute_search(driven_browser, query):
	#Make sure we're only looking at English-language news sources
	selenium.webdriver.support.select.Select(driven_browser.find_element_by_id("sourceSelectDDStyle")).select_by_value("F_GB00NBGenSrch.CS00900470;All English Language News")

	#Find the text area and fill in the search terms
	search_field = driven_browser.find_element_by_id("searchTextAreaStyle")
	search_field.send_keys(query)
	
	#Click the submit button
	driven_browser.find_element_by_xpath('//button[@type="submit" and @class="power_submit"]').click()
	time.sleep(20) #Give the website some time to process this
	
	#Next, we need to switch to the full article view
	driven_browser.switch_to_frame(driven_browser.find_element_by_xpath("//frame[contains(@name, 'fr_results')]"))
	selenium.webdriver.support.select.Select(driven_browser.find_element_by_xpath('//select[@id="viewDropdown"]')).select_by_value("GNBFULL")
	time.sleep(10)
	
	#Okay, the search has been prepared! Return the number of pages
	driven_browser.switch_to_frame(driven_browser.find_element_by_xpath("//frame[contains(@name, 'fr_resultsNav')]"))
	pagecount = int(driven_browser.find_element_by_xpath("//span[contains(@class, 'l3b pagination')]/strong[2]").text)
	driven_browser.switch_to_default_content()
	return pagecount
#-----------------------------------------------------------------------------------------
''' Get the result from the indicated search (baseurl) and page (pagectr). '''	
def retrieve_next_search_result(driven_browser, baseurl, pagectr):
	#Go to the indicated page
	driven_browser.get("{0}&start={1}".format(baseurl, (pagectr)))
	
	#Stagger the search a little (because JavaScript)
	time.sleep(7.5)
	results = []

	#Switch to the content frame
	driven_browser.switch_to_frame(driven_browser.find_element_by_xpath("//frame[contains(@name, 'fr_resultsContent')]"))
	
	#Convert the HTML into tree form so we can query it
	tree = html.fromstring(driven_browser.page_source)
	
	#Grab the meta information, headline, article body via XPATH
	meta = tree.xpath('//div[@class="sevPx"]//center//text()[string-length() > 1]')
	headline = tree.xpath('//span[@class="SS_L0"]//text()[string-length() > 1]')
	article_body = tree.xpath('//p[@class="loose"]/text() | //p[@class="loose"]/a[@class="RemoteLink"]/text()')
	
	#Also retrieve LexisNexis-specific metadata: BYLINE, LENGTH, LOAD-DATE, LANGUAGE, PUBLICATION-TYPE, JOURNAL-CODE
	ln_meta = tree.xpath('//span[@class="verdana"]//following-sibling::b/../text()[string-length() > 1]')
	ln_meta_result = ""; 
	meta_result = ""

	#We stuff all the metadata into one field each. We have to pull this apart later on. The problem is that the metadata is so inconsistent.
	for m in meta:
		to_append = ""
		if (type(m) is lxml.html.HtmlElement): to_append = stringscrub(m.text_content());
		else: to_append = stringscrub(m);
		meta_result = "{0} | {1}".format(meta_result, to_append)
	
	metadata = meta_result[3:]
	
	extracted_metadata = extract_metadata(metadata)
	
	results.append(extracted_metadata[0]) 
	results.append(extracted_metadata[1])
	results.append(metadata)
	
	#We do the same for LN metadata. Not all fields are always populated, after all.
	for m in ln_meta:
		to_append = ""
		if (type(m) is lxml.html.HtmlElement): to_append = stringscrub(m.text_content());
		else: to_append = stringscrub(m);
		ln_meta_result = "{0} | {1}".format(ln_meta_result, to_append)
	results.append(ln_meta_result[3:])
	
	#Headline and article body can be directly retrieved, which is nice.
	toHeadline = stringscrub(' '.join(headline)) #We have to do this because of formatting issues
	results.append(toHeadline)

	toBody = stringscrub(' '.join(article_body))	
	results.append(toBody)
	
	#Returns publication_name, datetime, metadata, ln_metadata, headline, body
	return results
#-----------------------------------------------------------------------------------------
def extract_metadata(blob):
	#For later
	date = ""; new_date = ""; old_date = "";

	#Define some patterns that will be used for metadata extraction
	publication_date = re.compile("[0-9 ,]{0,}[0-9]{4,}")
	month_names = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
	trim_leading = [" ", "\t", "0"]
	
	#Pull the metadata string apart
	metadata = blob.split(" | ")
	
	publication = metadata[0].upper().strip() #First column is always the publication name. UPPing takes care of inconsistent capitalization.
	
	#Date may start in the second column, but it can also be the third
	date_start_column = 1
	if (metadata[1].lower() not in month_names): date_start_column = 2 #If the second column is not the month, we need to skip one ahead
	date = metadata[date_start_column] #The first date column contains the month
	while (metadata[date_start_column+1][0] in trim_leading): metadata[date_start_column+1] = metadata[date_start_column+1][1:]; #Trim whitespace, leading zeroes and such
	
	#Okay, assemble the date
	date += " "
	date += publication_date.findall(metadata[date_start_column+1])[0] #The second date column contains the day and year
	date = date.replace(", ", " ")
	date = re.sub("[ ]+", " ", date)
	
	try: #Try to deal with nonstandard dates
		old_date = datetime.datetime.strptime(date, "%B %d %Y")
		new_date = old_date.strftime("%Y-%m-%d")
		
	except:
		new_date = date
	
	return([publication, new_date])

#-----------------------------------------------------------------------------------------
def get_sentiment(sentiString, p):
	#Take text, compute sentiment. If you want to use a nonstandard configuration, supply a different p.
	#In general, supply p is strongly recommended so you don't keep re-starting processes.

	#Partial credit goes to Alec Larsen - University of the Witwatersrand, South Africa, 2012
	
	#open a subprocess using shlex to get the command line string into the correct args list format
	if p is None:	
		p = subprocess.Popen(shlex.split("java -jar SentiStrengthCom.jar trinary sentenceCombineTot explain stdin sentidata ./SentiStrength_Data/"),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

	#communicate via stdin the string to be rated. Note that all spaces are replaced with +
	p.stdin.write(sentiString.replace(" ","+"))
	p.stdin.write("\n")
	stdout_text = p.stdout.readline()
	
	stdout_text = stdout_text.replace('"', '^')
	stdout_text = stdout_text.replace("\n", "")

	#Different values given are tab-separated
	ret_val = stdout_text.split("\t")

	#Returns (by default) positive, negative, neutral, explanation
	return ret_val
#-----------------------------------------------------------------------------------------
def main(search_string, access_url, username, password, starting_page):
	#Set up chromedriver
	print "Now spinning up browser..."
	driver = set_up_browser("./chromedriver/chromedriver")
	
	#Prepare SentiStrength JAR file for analysis
	senti_strength_process = subprocess.Popen(shlex.split("java -jar ./SentiStrengthCom.jar trinary sentenceCombineTot explain stdin sentidata ./SentiStrength_Data/"),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	
	#Prepare CSV output facilities
	csv.register_dialect('excel-two', delimiter=";", doublequote=True, escapechar=None, lineterminator="\r\n", quotechar='"', quoting=csv.QUOTE_MINIMAL,skipinitialspace=True)
	csv_headers=["Publication", "Date","Headline", "Meta", "LN-Meta", "Polarity_Pos", "Polarity_Neg", "Polarity_Neu"]#, "Explanation"]
	
	#Prepare filenames
	file_information = "Query: {0}\nDatetime: {1}".format(search_string, strftime("%Y-%m-%d %H:%M:%S"))
	filename = "LN-{0}.csv".format(hashlib.md5(file_information).hexdigest()) #;D
	info_file_name = "LN-{0}.meta".format(hashlib.md5(file_information).hexdigest())

	with open(info_file_name, 'w') as f: #Write out meta information
		f.write("Meta information for {0}\n\n".format(filename))
		f.write(file_information)

	#If we have an error on a page, we'll re-check it once the main query is done
	errorpages = []
		
	with open(filename, 'ab') as output_file: #Then open the actual output file
		#Prepare output file and set up headers
		output_writer = csv.writer(output_file, dialect='excel-two')
		output_writer.writerow(csv_headers)

		#First of all, we need to log in.
		handle_login(driver, access_url, username, password)
	
		#Next, we need to execute the search.
		total_pages = execute_search(driver, search_string) #TODO: Return pagecount?
		print "There are {0} pages".format(total_pages)

		#Now that our session is set up, we can start gathering data.
		baseurl = driver.current_url
		for i in range(starting_page, total_pages):
			try:
				#Open page & gather data
				print "{0}: Page {1} of {2}...".format(strftime("%Y-%m-%d %H:%M:%S"), i, total_pages)
				with open(info_file_name, 'ab') as f: f.write("\n{0}: Page {1} of {2}...".format(strftime("%Y-%m-%d %H:%M:%S"), i, total_pages));
				search_results = retrieve_next_search_result(driver, baseurl, i) #Returns publication_name, datetime, metadata, ln_metadata, headline, body
				
				#Prepare SentiStrength analysis
				fulltext = "{0} {1}".format(search_results[4], search_results[5])
				sents = get_sentiment(fulltext, senti_strength_process) #Returns (by default) positive, negative, neutral, explanation
				
				#Output format is ["Publication", "Date", "Headline", "Meta", "LN-Meta", "Polarity_Pos", "Polarity_Neg", "Polarity_Neu", "Explanation"]. Note that explanations are NOT stored, as this could be seen as violating the LexisNexis Terms & Conditions, since this field contains the full text.
				to_write = [ search_results[0], search_results[1], search_results[4], search_results[2], search_results[3], sents[0], sents[1], sents[2], ]#, sents[3] ]
				
				output_writer.writerow(to_write)
			
			except (KeyboardInterrupt, SystemExit):
				with open(info_file_name, 'ab') as f:
					print "\n\nProcess aborted at {0}".format(driver.current_url)
					f.write("\n\nProcess aborted at {0}".format(driver.current_url))
				raise

			except Exception as e:
				#It's possible our session expired...
				if (access_url in driver.current_url):
					print "Session expired? Re-establishing..."
					handle_login(driver, username, password)
					execute_search(driver, search_string)
					time.sleep(1)

				with open(info_file_name, 'ab') as f:
					print "There was an error at {0}, specifically {1}\n\n".format(driver.current_url, e)
					f.write("There was an error at {0}, specifically {1}\n\n".format(driver.current_url, e))
					errorpages.append(i)
				

		print "Search complete, there were {0} errors that will now be retried...".format(len(errorpages))

		for i in errorpages:
			try:
				#Open page & gather data
				print "{0}: Retrying page #{1}...".format(strftime("%Y-%m-%d %H:%M:%S"), i)
				with open(info_file_name, 'ab') as f: f.write("{0}: Retrying page #{1}...".format(strftime("%Y-%m-%d %H:%M:%S"), i));
				search_results = retrieve_next_search_result(driver, baseurl, i) #Returns publication_name, datetime, metadata, ln_metadata, headline, body
				
				#Prepare SentiStrength analysis
				fulltext = "{0} {1}".format(search_results[4], search_results[5])
				sents = get_sentiment(fulltext, senti_strength_process) #Returns (by default) positive, negative, neutral, explanation
				
				#Output format is ["Publication", "Date", "Meta", "LN-Meta", "Polarity_Pos", "Polarity_Neg", "Polarity_Neu", "Explanation"]
				to_write = [search_results[0], search_results[1], search_results[2], search_results[3], sents[0], sents[1], sents[2], sents[3] ]
				
				output_writer.writerow(to_write)
				
				errorpages.remove(i)
			
			except (KeyboardInterrupt, SystemExit):
				with open(info_file_name, 'ab') as f:
					print "\n\nProcess aborted at {0}".format(driver.current_url)
					f.write("\n\nProcess aborted at {0}".format(driver.current_url))
				raise

			except Exception as e:
				#It's possible our session expired...
				if (access_url in driver.current_url):
					print "Session expired? Re-establishing..."
					handle_login(driver, username, password)
					execute_search(driver, search_string)
					time.sleep(1)

				with open(info_file_name, 'ab') as f:
					print "There was another error at {0}, specifically {1}\n\n".format(driver.current_url, e)
					f.write("There was another error at {0}, specifically {1}\n\n".format(driver.current_url, e))	
					
		for i in errorpages:
			try:
				#Open page & gather data
				print "{0}: Retrying page #{1}...".format(strftime("%Y-%m-%d %H:%M:%S"), i)
				with open(info_file_name, 'ab') as f: f.write("{0}: Retrying page #{1}...".format(strftime("%Y-%m-%d %H:%M:%S"), i));
				search_results = retrieve_next_search_result(driver, baseurl, i) #Returns publication_name, datetime, metadata, ln_metadata, headline, body
				
				#Prepare SentiStrength analysis
				fulltext = "{0} {1}".format(search_results[4], search_results[5])
				sents = get_sentiment(fulltext, senti_strength_process) #Returns (by default) positive, negative, neutral, explanation
				
				#Output format is ["Publication", "Date", "Meta", "LN-Meta", "Polarity_Pos", "Polarity_Neg", "Polarity_Neu", "Explanation"]
				to_write = [search_results[0], search_results[1], search_results[2], search_results[3], sents[0], sents[1], sents[2], sents[3] ]
				
				output_writer.writerow(to_write)
				
				errorpages.remove(i)
			
			except (KeyboardInterrupt, SystemExit):
				with open(info_file_name, 'ab') as f:
					print "\n\nProcess aborted at {0}".format(driver.current_url)
					f.write("\n\nProcess aborted at {0}".format(driver.current_url))
				raise

			except Exception as e:
				#It's possible our session expired...
				if (access_url in driver.current_url):
					print "Session expired? Re-establishing..."
					handle_login(driver, username, password)
					execute_search(driver, search_string)
					time.sleep(1)

				with open(info_file_name, 'ab') as f:
					print "There was another error at {0}, specifically {1}\n\n".format(driver.current_url, e)
					f.write("There was another error at {0}, specifically {1}\n\n".format(driver.current_url, e))	

	print "{0}: Search complete.".format(strftime("%Y-%m-%d %H:%M:%S"))

#---------------------------------------------------------------------------

''' If this file is run directly, it inputs query parameters from stdin and reads user credentials
    from a file called "access.txt" before doing its thing. '''
if __name__ == '__main__':
	#Do some inputting of search parameters. TODO: Validation
	query = raw_input("Query? Example: HEADLINE(sony) not SUBJECT(patent or advert!) \n >   ")
	since = raw_input("Start date (YYYY-MM-DD)? Example: 2011-04-15\n >   ")
	until = raw_input("End date (YYYY-MM-DD)? Example: 2011-05-25\n >   ")
	paeg = raw_input("Start at which page? Example: 1\n >   ")

	querystring = "DATE(>={0} and <={1}) and {2}".format(since, until, query)
	
	#Find out user's credentials
	with open("access.txt") as f:
		content = f.readlines()
	un = content[0].replace("\n", ""); pw = content[1].replace("\n", ""); rl = content[2].replace("\n", "")
	
	#Call main method
	main(querystring, rl, un, pw, int(paeg))
