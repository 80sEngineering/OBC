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
        """Fetch the latest code from the repo in chunks, update, and reset."""
        
        index = 0
        for firmware_url in self.firmware_urls:
            gc.collect()  # Free memory before request
            try:
                response = urequests.get(firmware_url, stream=True)  # Enable streaming
            except OSError:
                logging.error(f'> Memory allocation failed for {firmware_url}')
                continue  # Skip to the next URL

            if response.status_code == 200:
                filename = self.filenames[index]
                logging.info(f'> Fetched latest firmware for {filename}, status: {response.status_code}')
                
                try:
                    with open('latest_code.py', 'w') as f:
                        chunk_size = 1024  # Read in 1KB chunks
                        while True:
                            gc.collect()  # Free memory during download
                            chunk = response.raw.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)  # Write each chunk to file
                    response.close()
                    
                    logging.debug("> Updating device...")
                    os.rename('latest_code.py', filename)  # Replace old code

                except MemoryError:
                    logging.error(f'> Memory allocation failed while writing {filename}')
            
            else:
                logging.error(f'> Firmware not found - {firmware_url}')
            
            index += 1
            response.close()
            gc.collect()  # Free memory after each file

        logging.debug('> Restarting device...')
        machine.reset()  # Reset to apply update         
                
              
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
    

