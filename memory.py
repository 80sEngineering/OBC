import ujson as json
import logging

def access_setting(setting_type, data_to_write = None):
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
            result = data[setting_type]
            file.close()
    except:
        logging.error(f"> Setting {setting_type} not found")
        return False

    if not data_to_write:
        return result
    else:
        with open('data.json', 'w') as file:
            data[setting_type] = data_to_write
            json.dump(data, file)
            file.close()
        
