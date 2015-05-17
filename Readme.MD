# Scraping and sentiment detection utilities for news article analysis
## Explanation of purpose
* News articles should be processed and analysed in order to have a "point of comparison" for social media analysis.
* Online news portals rarely resemble one another in layouts and frequently change the design of their websites, the structure of their archives, the availability of articles etc. For this reason, it is significantly easier to scrape collections of articles than individual media outlets.
* LexisNexis is one such compilation portal. As it is only intended to be operated by humans, scraping techniques must be employed. As the website further relies heavily on JavaScript, the most promising approach is one based on browser automation. The search terms are still specified manually and all scraping and retrieval happens via a real browser, consistent with the intended usage. The toolset can be adjusted, without too much difficulty, to work for other portals.
* For reasons of consistency, this analysis tool also employs SentiStrength by default. This is not vital, as it is expected that LexisNexis articles (by default) are written in a standard dialect of English. If you do not have access to SentiStrengthCom.jar, make the neccessary adjustments to the function get_sentiment.
* Note that storing the fulltext of an arbitrary number of articles indefinitely violates LexisNexis' TOC. To get around this, articles are loaded, scraped and processed immediately, without the full text ever being stored on the disk. This is also the reason the tools are provided in a single "fire-and-forget" file.

## Usage
* Run websearch_scrape.py to execute a search for Tweets and to save them (with some meta-information) in a CSV file. Refer to http://www.twitter.com/search for operators you can use. As this search scrapes Twitter's web search and does not use the search API, it is able to retrieve Tweets that are older than a week. In case you want to interrupt and later resume a search, you can specify a search cursor (check the .meta file to see the search cursors that are being / have been processed).
* Run merge_csv_files.py to merge all CSV files in the current directory. This tool is a very blunt instrument that should really only be used if you had to split up a search and now want to merge the files. Note that duplicates are automatically removed and that entries are forced into UTF-8 format. You can probably use UNIX tools instead of this utility, but it's provided for completeness' sake.
* Run senti_strength.py to analyse the retrieved Tweets and to compute sentiment scores. Note that the JAR file ("SentiStrengthCom.jar") MUST be in the same folder as the script, as MUST the SentiStrength_Data directory. The output is stored in another CSV file.
* Alternatively, Tweets can be analyzed using score_textblob.py. This method is significantly more primitive, but it also does not require the presence of the SentiStrengthCom.jar file and can in fact be used completely standalone.

## Required files
* A file called "access.txt", containing, in this order,
** your username,
** your password,
** your LexisNexis access URL
* A file called "SentiStrengthCom.jar", containing the Java version of SentiStrength (available from http://sentistrength.wlv.ac.uk/)
* A folder called "SentiStrength_Data" to go with SentiStrengthCom (ditto)
* A folder called "chromedriver", which contains the Chrome driver (named "chromedriver")
All of these files need to be in the same folder as lexisnexis_analysis.py