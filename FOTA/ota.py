import network
import urequests
import os
import json
import machine
from time import sleep
import logging
import gc
           

class OTAUpdater:
    """ This class handles OTA updates. It connects to the Wi-Fi, checks for updates, downloads and installs them."""
    def __init__(self, repo_url, filenames):
        self.filenames = filenames
        self.repo_url = repo_url
        if "www.github.com" in self.repo_url :
            logging.debug(f"> Updating {repo_url} to raw.githubusercontent")
            self.repo_url = self.repo_url.replace("www.github","raw.githubusercontent")
        elif "github.com" in self.repo_url:
            logging.debug(f"> Updating {repo_url} to raw.githubusercontent")
            self.repo_url = self.repo_url.replace("github","raw.githubusercontent")            
        self.version_url = self.repo_url + 'main/version.json'
        logging.debug(f"> Version url is: {self.version_url}")
        self.firmware_urls= []
        for filename in self.filenames:
            self.firmware_urls.append(self.repo_url + 'main/' + filename)

        # get the current version (stored in version.json)
        if 'version.json' in os.listdir():    
            with open('version.json') as f:
                self.current_version = int(json.load(f)['version'])
            logging.debug(f"> Current device firmware version is {self.current_version}")

        else:
            self.current_version = 0
            # save the current version
            with open('version.json', 'w') as f:
                json.dump({'version': self.current_version}, f)
            
    def download_update_and_reset(self):
        """ Fetch the latest code from the repo if found, updates, and reset"""
        
        # Fetch the latest code from the repo.
        index = 0
        for firmware_url in self.firmware_urls:
            try:
                gc.collect() #free some memory space
                response = urequests.get(firmware_url)
            except OSError:
                logging.error(f'> Memory allocation failed for {filename}')
                response.status_code = 404
            if response.status_code == 200:
                filename = self.filenames[index]
                logging.debug(f'> Fetched latest firmware code for {filename}, status: {response.status_code}')
                
                with open('latest_code.py', 'w') as f:
                    try:
                        gc.collect()
                        f.write(response.text)
                        writing_sucess = True
                    except MemoryError:
                        logging.error(f'> Memory allocation failed for {filename}')
                        writing_sucess = False
                 
                if writing_sucess: 
                    logging.debug("> Updating device... ")
                    # Overwrite the old code.
                    os.rename('latest_code.py', filename)  

            elif response.status_code == 404:
                logging.error(f'> Firmware not found - {firmware_url}.')
            index += 1
            
        # Restart the device to run the new code.
        logging.debug('> Restarting device...')
        machine.reset()  # Reset the device to run the new code.            
            
          
    def check_for_updates(self):
        """ Check if updates are available."""
        
        logging.debug(f'> Checking for latest version... on {self.version_url}')
        try:
            response = urequests.get(self.version_url)
        except OSError:
            self.newer_version_available = False
            return
        data = json.loads(response.text)
        
        logging.debug(f"> Data is: {data}, url is: {self.version_url}")

        
        self.latest_version = int(data['version'])
        logging.debug(f'> Latest version is: {self.latest_version}')
        
        # compare versions
        self.newer_version_available = True if self.current_version < self.latest_version else False
        
        logging.debug(f'> Newer version available: {self.newer_version_available}')    
        return self.newer_version_available
    
