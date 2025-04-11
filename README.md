# mdw-scraper

### virtual environment setup  

If you want to setup virtual environment
steps:
1. Go to <file> -> (settings)
2. look for Project: <Project name>. eg:- mdw-scraper
3. Then python interpreter -> Click on (add interpreter) {present on right side of that window} -> (add local inerpreter)
4. Then you will see a window which has Environment: select (generate new) , Type: select (Virtulenv), Base Python: select (latest python verson), Location select (default)
5. This will create your virtual environment
   
### lib installation

first check what is installed by running pip list. 
List of required libraries
{beautifulsoup4, 
certifi, 
charset-normalizer, 
idna, 
lxml, 
pip, 
psycopg2, 
requests, 
soupsieve, 
typing_extensions,
urllib3}
If the requiremnets.txt file is present
Run this command to install required library 'pip install -r requirements.txt'

If requirement.txt is not present then install separately
Use comand 'pip install <library name>' {beautifulsoup4,certifi,charset-normalizer,idna,lxml,pip,psycopg2,requests,soupsieve,typing_extensions,urllib3}
