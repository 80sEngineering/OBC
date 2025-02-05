from FOTA import access_point, dns, server
from FOTA.template import render_template
import json
import machine
import os
import utime
import _thread
import network
import logging

def machine_reset():
    utime.sleep(1)
    logging.debug("> Resetting...")
    machine.reset()

def setup_mode():
    logging.debug("> Entering setup mode...")
    
    AP_NAME = "E30_OBC"
    AP_DOMAIN = "obc-80s.engineering"
    AP_TEMPLATE_PATH = "FOTA/ap_templates"

    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    networks = wlan.scan()
    
    found_wifi_networks = {}
    
    for n in networks:
        ssid = n[0].decode().strip('\x00')
        if len(ssid) > 0:
            rssi = n[3]
            if ssid in found_wifi_networks:
                if found_wifi_networks[ssid] < rssi:
                    found_wifi_networks[ssid] = rssi
            else:
                found_wifi_networks[ssid] = rssi

    wifi_networks_by_strength = sorted(found_wifi_networks.items(), key = lambda x:x[1], reverse = True)
    
    logging.debug(f"> WiFi network by strenght: {wifi_networks_by_strength}")
    
    def ap_index(request):
        if request.headers.get("host").lower() != AP_DOMAIN.lower():
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = AP_DOMAIN.lower())

        return render_template(f"{AP_TEMPLATE_PATH}/index.html", wifis = wifi_networks_by_strength)


    def ap_configure(request):
        logging.debug(f"> Saving wifi credentials...")

        with open('wifi.json', "w") as f:
            json.dump(request.form, f)
            f.close()

        # Reboot from new thread after we have responded to the user.
        _thread.start_new_thread(machine_reset, ())
        return render_template(f"{AP_TEMPLATE_PATH}/configured.html", ssid = request.form["ssid"])
        
    def ap_catch_all(request):
        if request.headers.get("host") != AP_DOMAIN:
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = AP_DOMAIN)

        return "Not found.", 404

    server.add_route("/", handler = ap_index, methods = ["GET"])
    server.add_route("/configure", handler = ap_configure, methods = ["POST"])
    server.set_callback(ap_catch_all)

    ap = access_point(AP_NAME)
    ip = ap.ifconfig()[0]
    dns.run_catchall(ip)
    
    


